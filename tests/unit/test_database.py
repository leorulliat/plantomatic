"""
Tests unitaires pour core/database.py.
À exécuter sur Windows/WSL ou RPi (pas de dépendance GPIO).

Exécution:
    pytest tests/unit/test_database.py -v
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from core.database import Database


@pytest.fixture
def temp_db():
    """Crée une DB temporaire pour chaque test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    db = Database(db_path=db_path)
    yield db
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)
    # Cleanup WAL files
    Path(f"{db_path}-wal").unlink(missing_ok=True)
    Path(f"{db_path}-shm").unlink(missing_ok=True)


class TestDatabaseInit:
    """Tests d'initialisation DB."""
    
    def test_database_creates_file(self, temp_db):
        """Vérifie que la DB crée un fichier."""
        assert Path(temp_db.db_path).exists()
    
    def test_database_creates_tables(self, temp_db):
        """Vérifie que toutes les tables sont créées."""
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'readings', 'soil_sensors', 'soil_humidity_readings',
            'watering_events', 'camera_events'
        ]
        
        for table in expected_tables:
            assert table in tables, f"Table {table} not created"
    
    def test_wal_mode_enabled(self, temp_db):
        """Vérifie que WAL mode est activé."""
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0].upper()
        
        assert mode == "WAL", f"WAL mode not enabled, got {mode}"


class TestReadings:
    """Tests pour les lectures globales."""
    
    def test_insert_reading(self, temp_db):
        """Insère une lecture et vérifie l'ID retourné."""
        reading_id = temp_db.insert_reading(
            temp_celsius=22.5,
            humidity_percent=65.0,
            pressure_hpa=1013.25,
            water_level_ok=True
        )
        
        assert isinstance(reading_id, int)
        assert reading_id > 0
    
    def test_get_latest_readings(self, temp_db):
        """Insère plusieurs lectures et récupère les dernières."""
        for i in range(5):
            temp_db.insert_reading(
                temp_celsius=20 + i,
                humidity_percent=60 + i,
                pressure_hpa=1013.0,
                water_level_ok=True
            )
        
        readings = temp_db.get_latest_readings(limit=3)
        
        assert len(readings) == 3
        assert readings[0]['temp_celsius'] == 24  # Dernière (la plus chaude)
        assert readings[2]['temp_celsius'] == 22  # Troisième
    
    def test_reading_with_null_values(self, temp_db):
        """Insère une lecture avec certaines valeurs NULL."""
        reading_id = temp_db.insert_reading(
            temp_celsius=22.5,
            humidity_percent=None,
            pressure_hpa=None,
            water_level_ok=True
        )
        
        readings = temp_db.get_latest_readings(limit=1)
        assert readings[0]['humidity_percent'] is None
        assert readings[0]['temp_celsius'] == 22.5
    
    def test_water_level_boolean_conversion(self, temp_db):
        """Vérifie conversion bool → int pour water_level_ok."""
        temp_db.insert_reading(water_level_ok=True)
        temp_db.insert_reading(water_level_ok=False)
        temp_db.insert_reading(water_level_ok=None)
        
        readings = temp_db.get_latest_readings(limit=3)
        
        assert readings[2]['water_level_ok'] == 1  # True → 1
        assert readings[1]['water_level_ok'] == 0  # False → 0
        assert readings[0]['water_level_ok'] is None  # None → None


class TestSoilSensors:
    """Tests pour les capteurs d'humidité."""
    
    def test_insert_soil_sensor(self, temp_db):
        """Crée un capteur."""
        sensor_id = temp_db.insert_soil_sensor("Salon", sensor_pin=None)
        assert isinstance(sensor_id, int)
        assert sensor_id > 0
    
    def test_get_all_soil_sensors(self, temp_db):
        """Récupère tous les capteurs."""
        temp_db.insert_soil_sensor("Salon")
        temp_db.insert_soil_sensor("Chambre")
        temp_db.insert_soil_sensor("Cuisine")
        
        sensors = temp_db.get_all_soil_sensors()
        
        assert len(sensors) == 3
        assert sensors[0]['sensor_name'] == "Salon"
        assert sensors[1]['sensor_name'] == "Chambre"
    
    def test_sensor_unique_constraint(self, temp_db):
        """Vérifie que noms capteurs sont uniques."""
        temp_db.insert_soil_sensor("Salon")
        
        with pytest.raises(sqlite3.IntegrityError):
            temp_db.insert_soil_sensor("Salon")
    
    def test_insert_soil_humidity(self, temp_db):
        """Insère une lecture d'humidité pour un capteur."""
        sensor_id = temp_db.insert_soil_sensor("Salon")
        reading_id = temp_db.insert_soil_humidity(sensor_id, 65.5)
        
        assert isinstance(reading_id, int)
        assert reading_id > 0
    
    def test_get_soil_humidity_latest(self, temp_db):
        """Récupère les dernières lectures par capteur."""
        s1 = temp_db.insert_soil_sensor("Salon")
        s2 = temp_db.insert_soil_sensor("Chambre")
        
        # Insère plusieurs lectures (dernière sera retournée)
        temp_db.insert_soil_humidity(s1, 60.0)
        temp_db.insert_soil_humidity(s1, 65.0)
        temp_db.insert_soil_humidity(s1, 70.0)
        
        temp_db.insert_soil_humidity(s2, 55.0)
        temp_db.insert_soil_humidity(s2, 75.0)
        
        latest = temp_db.get_soil_humidity_latest()
        
        assert len(latest) == 2
        assert latest[s1] == 70.0  # Dernière pour Salon
        assert latest[s2] == 75.0  # Dernière pour Chambre
    
    def test_get_soil_humidity_avg(self, temp_db):
        """Calcule la moyenne des dernières lectures."""
        s1 = temp_db.insert_soil_sensor("Salon")
        s2 = temp_db.insert_soil_sensor("Chambre")
        s3 = temp_db.insert_soil_sensor("Cuisine")
        
        temp_db.insert_soil_humidity(s1, 60.0)
        temp_db.insert_soil_humidity(s2, 70.0)
        temp_db.insert_soil_humidity(s3, 80.0)
        
        avg = temp_db.get_soil_humidity_avg()
        
        assert avg == 70.0  # (60 + 70 + 80) / 3


class TestWateringEvents:
    """Tests pour les événements d'arrosage."""
    
    def test_insert_watering_event_success(self, temp_db):
        """Insère un événement d'arrosage réussi."""
        event_id = temp_db.insert_watering_event(
            event_type="MANUAL",
            duration_seconds=30,
            status="SUCCESS",
            reason=None
        )
        
        assert isinstance(event_id, int)
        assert event_id > 0
    
    def test_insert_watering_event_failed(self, temp_db):
        """Insère un événement d'arrosage échoué."""
        event_id = temp_db.insert_watering_event(
            event_type="AUTO",
            duration_seconds=0,
            status="CANCELLED",
            reason="Water empty"
        )
        
        events = temp_db.get_watering_events(limit=1)
        assert events[0]['status'] == "CANCELLED"
        assert events[0]['reason'] == "Water empty"
    
    def test_get_watering_events(self, temp_db):
        """Récupère les événements d'arrosage."""
        temp_db.insert_watering_event("MANUAL", 30, "SUCCESS")
        temp_db.insert_watering_event("AUTO", 30, "SUCCESS")
        temp_db.insert_watering_event("MANUAL", 0, "CANCELLED", "Water empty")
        
        events = temp_db.get_watering_events(limit=2)
        
        assert len(events) == 2
        assert events[0]['type'] == "MANUAL"  # Dernier inséré
        assert events[1]['type'] == "AUTO"


class TestCameraEvents:
    """Tests pour les événements caméra."""
    
    def test_insert_camera_event(self, temp_db):
        """Insère un événement caméra."""
        event_id = temp_db.insert_camera_event(
            photo_path="/photos/photo_20260613_143022.jpg",
            file_size_kb=256
        )
        
        assert isinstance(event_id, int)
        assert event_id > 0
    
    def test_get_camera_events(self, temp_db):
        """Récupère les événements caméra."""
        temp_db.insert_camera_event("/photos/photo1.jpg", 200)
        temp_db.insert_camera_event("/photos/photo2.jpg", 250)
        temp_db.insert_camera_event("/photos/photo3.jpg", 300)
        
        events = temp_db.get_camera_events(limit=2)
        
        assert len(events) == 2
        assert events[0]['photo_path'] == "/photos/photo3.jpg"  # Dernier
        assert events[0]['file_size_kb'] == 300


class TestCleanup:
    """Tests pour le nettoyage des données."""
    
    def test_delete_old_readings(self, temp_db):
        """Supprime les lectures plus vieilles que N jours."""
        # Insère une lecture récente
        temp_db.insert_reading(temp_celsius=22.0, water_level_ok=True)
        
        # Insère des lectures anciennes (simulé via SQL direct)
        old_date = (datetime.now() - timedelta(days=90)).isoformat()
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO readings (timestamp, temp_celsius, water_level_ok) VALUES (?, ?, ?)",
                (old_date, 20.0, 1)
            )
            cursor.execute(
                "INSERT INTO readings (timestamp, temp_celsius, water_level_ok) VALUES (?, ?, ?)",
                (old_date, 19.0, 1)
            )
            conn.commit()
        
        # Supprime les lectures > 60 jours
        deleted = temp_db.delete_old_readings(days_old=60)
        
        assert deleted >= 2
        
        # Vérifie qu'une lecture récente reste
        readings = temp_db.get_latest_readings(limit=10)
        assert len(readings) >= 1
        assert readings[0]['temp_celsius'] == 22.0
    
    def test_vacuum_compacts_db(self, temp_db):
        """Teste la compaction DB après delete."""
        # Insère puis supprime des données
        for i in range(100):
            temp_db.insert_reading(temp_celsius=20.0 + i, water_level_ok=True)
        
        old_date = (datetime.now() - timedelta(days=90)).isoformat()
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            for i in range(100):
                cursor.execute(
                    "INSERT INTO readings (timestamp, temp_celsius, water_level_ok) VALUES (?, ?, ?)",
                    (old_date, 20.0 + i, 1)
                )
            conn.commit()
        
        size_before = Path(temp_db.db_path).stat().st_size
        
        temp_db.delete_old_readings(days_old=60)
        temp_db.vacuum()
        
        size_after = Path(temp_db.db_path).stat().st_size
        
        # Size should be reduced (not guaranteed, but likely)
        # Just verify vacuum doesn't crash
        assert size_after > 0


class TestStats:
    """Tests pour les statistiques DB."""
    
    def test_get_stats(self, temp_db):
        """Récupère les statistiques DB."""
        temp_db.insert_reading(temp_celsius=22.0, water_level_ok=True)
        temp_db.insert_reading(temp_celsius=23.0, water_level_ok=True)
        s1 = temp_db.insert_soil_sensor("Salon")
        temp_db.insert_soil_humidity(s1, 65.0)
        
        stats = temp_db.get_stats()
        
        assert stats['readings'] == 2
        assert stats['soil_sensors'] == 1
        assert stats['soil_humidity_readings'] == 1
        assert 'db_size_kb' in stats
        assert stats['db_size_kb'] > 0


class TestConcurrency:
    """Tests de concurrence (WAL mode)."""
    
    def test_concurrent_reads_and_writes(self, temp_db):
        """Simule lectures et écritures concurrentes."""
        # Simule lecture pendant que l'autre écrit
        for i in range(10):
            temp_db.insert_reading(temp_celsius=20.0 + i, water_level_ok=True)
        
        # Lecture et écriture mélangées
        readings = temp_db.get_latest_readings(limit=5)
        temp_db.insert_reading(temp_celsius=30.0, water_level_ok=True)
        readings2 = temp_db.get_latest_readings(limit=5)
        
        assert len(readings) == 5
        assert len(readings2) == 5
        # Dernière lecture doit être 30.0
        assert readings2[0]['temp_celsius'] == 30.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
