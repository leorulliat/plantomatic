"""
Abstraction SQLite avec WAL mode pour Plantomatic.
Gère initialisation DB, schéma, et toutes les opérations CRUD.

Utilisation:
    from core.database import db
    db.insert_reading(temp_celsius=22.5, humidity_percent=65, ...)
    readings = db.get_latest_readings(limit=10)
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
import logging

from config.settings import (
    DB_PATH, DB_BUSY_TIMEOUT_MS, DB_CLEANUP_DAYS
)


class Database:
    """Singleton gérant toutes les opérations SQLite."""
    
    def __init__(self, db_path: str = None):
        """
        Initialise la connexion SQLite en mode WAL.
        
        Args:
            db_path: Chemin vers la DB (par défaut: config.DB_PATH)
        """
        self.db_path = db_path or str(DB_PATH)
        self.logger = logging.getLogger(__name__)
        
        # Initialiser WAL mode + timeout
        self._init_wal_mode()
        
        # Créer schéma
        self._create_tables()
        
        self.logger.info(f"Database initialized at {self.db_path} (WAL mode)")
    
    # ========== PRIVATE METHODS ==========
    
    def _init_wal_mode(self) -> None:
        """Active WAL mode et configure busy_timeout."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(f"PRAGMA busy_timeout={DB_BUSY_TIMEOUT_MS}")
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Failed to initialize WAL mode: {e}")
            raise
    
    @contextmanager
    def _get_connection(self):
        """Context manager pour gérer les connexions SQLite."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Accès par colonne (dict-like)
        try:
            yield conn
        finally:
            conn.close()
    
    def _create_tables(self) -> None:
        """Crée le schéma complet si tables n'existent pas."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Table: Relevés globales (toutes les 4h)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    temp_celsius REAL,
                    humidity_percent REAL,
                    pressure_hpa REAL,
                    water_level_ok INTEGER
                )
            """)
            
            # Table: Définition des capteurs d'humidité
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS soil_sensors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sensor_name TEXT UNIQUE NOT NULL,
                    sensor_pin INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table: Lectures d'humidité par capteur
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS soil_humidity_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    sensor_id INTEGER NOT NULL,
                    humidity_percent REAL,
                    FOREIGN KEY (sensor_id) REFERENCES soil_sensors(id)
                )
            """)
            
            # Table: Événements d'arrosage
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watering_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    type TEXT NOT NULL,
                    duration_seconds INTEGER,
                    status TEXT,
                    reason TEXT
                )
            """)
            
            # Table: Événements caméra
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS camera_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    photo_path TEXT NOT NULL,
                    file_size_kb INTEGER
                )
            """)
            
            # Indexes pour performances
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_readings_timestamp 
                ON readings(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_soil_humidity_timestamp 
                ON soil_humidity_readings(timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_watering_timestamp 
                ON watering_events(timestamp DESC)
            """)
            
            conn.commit()
    
    # ========== INSERT METHODS ==========
    
    def insert_reading(self, 
                      temp_celsius: Optional[float] = None,
                      humidity_percent: Optional[float] = None,
                      pressure_hpa: Optional[float] = None,
                      water_level_ok: Optional[bool] = None) -> int:
        """
        Enregistre une lecture (toutes les 4h par job check).
        
        Args:
            temp_celsius: Température en °C
            humidity_percent: Humidité relative en %
            pressure_hpa: Pression en hPa
            water_level_ok: Booléen niveau eau (1=OK, 0=VIDE)
        
        Returns:
            int: ID de la ligne insérée
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO readings 
                (temp_celsius, humidity_percent, pressure_hpa, water_level_ok)
                VALUES (?, ?, ?, ?)
            """, (temp_celsius, humidity_percent, pressure_hpa, 
                  1 if water_level_ok else 0 if water_level_ok is not None else None))
            conn.commit()
            return cursor.lastrowid
    
    def insert_soil_humidity(self, sensor_id: int, humidity_percent: float) -> int:
        """
        Enregistre une lecture d'humidité pour un capteur.
        
        Args:
            sensor_id: ID du capteur (from soil_sensors table)
            humidity_percent: Humidité en %
        
        Returns:
            int: ID de la ligne insérée
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO soil_humidity_readings 
                (sensor_id, humidity_percent)
                VALUES (?, ?)
            """, (sensor_id, humidity_percent))
            conn.commit()
            return cursor.lastrowid
    
    def insert_watering_event(self, 
                             event_type: str,
                             duration_seconds: int,
                             status: str,
                             reason: Optional[str] = None) -> int:
        """
        Enregistre un événement d'arrosage.
        
        Args:
            event_type: "AUTO" ou "MANUAL"
            duration_seconds: Durée pompe activée
            status: "SUCCESS", "FAILED", "CANCELLED"
            reason: Raison optionnelle (ex: "Water empty")
        
        Returns:
            int: ID de la ligne insérée
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO watering_events 
                (type, duration_seconds, status, reason)
                VALUES (?, ?, ?, ?)
            """, (event_type, duration_seconds, status, reason))
            conn.commit()
            return cursor.lastrowid
    
    def insert_camera_event(self, photo_path: str, file_size_kb: int = 0) -> int:
        """
        Enregistre une photo prise.
        
        Args:
            photo_path: Chemin absolu de la photo
            file_size_kb: Taille fichier en KB
        
        Returns:
            int: ID de la ligne insérée
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO camera_events 
                (photo_path, file_size_kb)
                VALUES (?, ?)
            """, (photo_path, file_size_kb))
            conn.commit()
            return cursor.lastrowid
    
    def insert_soil_sensor(self, sensor_name: str, sensor_pin: Optional[int] = None) -> int:
        """
        Crée un nouveau capteur d'humidité.
        
        Args:
            sensor_name: Nom du capteur (ex: "Salon", "Chambre")
            sensor_pin: GPIO pin optionnel
        
        Returns:
            int: ID du capteur créé
        
        Raises:
            sqlite3.IntegrityError: Si capteur avec même nom existe déjà
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO soil_sensors 
                (sensor_name, sensor_pin)
                VALUES (?, ?)
            """, (sensor_name, sensor_pin))
            conn.commit()
            return cursor.lastrowid
    
    # ========== SELECT METHODS ==========
    
    def get_latest_readings(self, limit: int = 20) -> List[Dict]:
        """
        Retourne les N dernières lectures globales.
        
        Args:
            limit: Nombre de lectures à retourner
        
        Returns:
            List de dicts: [{"id": 1, "timestamp": "...", "temp_celsius": 22.5, ...}, ...]
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM readings 
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_soil_humidity_avg(self) -> Optional[float]:
        """
        Retourne la moyenne d'humidité sol de tous les capteurs (dernière lecture pour chaque).
        
        Returns:
            float: Humidité moyenne en %, ou None si pas de données
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # SQLite n'a pas DISTINCT ON, donc utiliser MAX(rowid) pour obtenir la dernière
            cursor.execute("""
                SELECT AVG(humidity_percent) as avg_humidity
                FROM (
                    SELECT humidity_percent
                    FROM soil_humidity_readings
                    WHERE rowid IN (
                        SELECT MAX(rowid)
                        FROM soil_humidity_readings
                        GROUP BY sensor_id
                    )
                )
            """)
            
            result = cursor.fetchone()
            avg = result[0] if result else None
            
            return avg
    
    def get_soil_humidity_latest(self) -> Dict[int, float]:
        """
        Retourne la dernière lecture pour chaque capteur.
        
        Returns:
            Dict: {sensor_id: humidity%, ...}
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sensor_id, humidity_percent
                FROM soil_humidity_readings
                WHERE rowid IN (
                    SELECT MAX(rowid)
                    FROM soil_humidity_readings
                    GROUP BY sensor_id
                )
            """)
            rows = cursor.fetchall()
            return {row[0]: row[1] for row in rows}
    
    def get_all_soil_sensors(self) -> List[Dict]:
        """
        Retourne tous les capteurs d'humidité enregistrés.
        
        Returns:
            List de dicts: [{"id": 1, "sensor_name": "Salon", "sensor_pin": None, ...}, ...]
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM soil_sensors ORDER BY id")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_watering_events(self, limit: int = 10) -> List[Dict]:
        """
        Retourne les N derniers événements d'arrosage.
        
        Args:
            limit: Nombre d'événements à retourner
        
        Returns:
            List de dicts
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM watering_events 
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_camera_events(self, limit: int = 10) -> List[Dict]:
        """
        Retourne les N dernières photos.
        
        Args:
            limit: Nombre de photos à retourner
        
        Returns:
            List de dicts
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM camera_events 
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    # ========== DELETE METHODS ==========
    
    def delete_old_readings(self, days_old: int = DB_CLEANUP_DAYS) -> int:
        """
        Supprime les lectures plus vieilles que N jours.
        Utilisé par tools/export_and_clean.py.
        
        Args:
            days_old: Supprimer données > N jours
        
        Returns:
            int: Nombre de lignes supprimées
        """
        cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Supprime readings
            cursor.execute(
                "DELETE FROM readings WHERE timestamp < ?",
                (cutoff_date,)
            )
            deleted_count = cursor.rowcount
            
            # Supprime soil_humidity_readings
            cursor.execute(
                "DELETE FROM soil_humidity_readings WHERE timestamp < ?",
                (cutoff_date,)
            )
            deleted_count += cursor.rowcount
            
            # Supprime watering_events
            cursor.execute(
                "DELETE FROM watering_events WHERE timestamp < ?",
                (cutoff_date,)
            )
            deleted_count += cursor.rowcount
            
            # Supprime camera_events
            cursor.execute(
                "DELETE FROM camera_events WHERE timestamp < ?",
                (cutoff_date,)
            )
            deleted_count += cursor.rowcount
            
            conn.commit()
            
            self.logger.info(f"Deleted {deleted_count} rows older than {days_old} days")
            return deleted_count
    
    # ========== UTILITY METHODS ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retourne des statistiques sur la DB (taille, nombre de lignes, etc.).
        
        Returns:
            Dict avec stats
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            tables = [
                'readings', 'soil_sensors', 'soil_humidity_readings',
                'watering_events', 'camera_events'
            ]
            
            stats = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                stats[table] = count
            
            # Taille fichier DB
            db_size_bytes = Path(self.db_path).stat().st_size
            stats['db_size_kb'] = db_size_bytes / 1024
            
            return stats
    
    def vacuum(self) -> None:
        """Compacte la base de données (après delete_old_readings)."""
        with self._get_connection() as conn:
            conn.execute("VACUUM")
            conn.commit()
        self.logger.info("Database vacuumed")
    
    def close(self) -> None:
        """Ferme la DB proprement (optionnel, rarement utilisé)."""
        pass


# ========== SINGLETON GLOBAL ==========

# Instance unique de la DB, importable partout
db = Database()
