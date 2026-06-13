"""
Tests unitaires pour core/logger.py.
À exécuter sur Windows/WSL ou RPi (pas de dépendance GPIO).

Exécution:
    pytest tests/unit/test_logger.py -v
"""

import pytest
import tempfile
import logging
from pathlib import Path
from core.logger import CentralLogger


@pytest.fixture
def temp_logger():
    """Crée un logger temporaire pour chaque test."""
    with tempfile.NamedTemporaryFile(mode='w', suffix=".log", delete=False) as f:
        log_path = f.name
    
    logger = CentralLogger(log_file=log_path, log_level="DEBUG")
    yield logger
    
    # Cleanup
    Path(log_path).unlink(missing_ok=True)


class TestLoggerInit:
    """Tests d'initialisation du logger."""
    
    def test_logger_creates_file(self, temp_logger):
        """Vérifie que le logger crée un fichier log."""
        temp_logger.logger.info("Test message")
        assert Path(temp_logger.log_file).exists()
    
    def test_logger_has_handlers(self, temp_logger):
        """Vérifie que le logger a handlers fichier et console."""
        assert len(temp_logger.logger.handlers) >= 2
    
    def test_werkzeug_logger_filtered(self, temp_logger):
        """Vérifie que werkzeug logger est filtré."""
        werkzeug = logging.getLogger('werkzeug')
        assert werkzeug.level == logging.ERROR


class TestLogCheck:
    """Tests pour log_check()."""
    
    def test_log_check_full(self, temp_logger):
        """Enregistre un check complet."""
        temp_logger.log_check(
            temp=22.5,
            humidity=65,
            water_ok=True,
            pressure=1013.25
        )
        
        logs = temp_logger.get_logs(limit=1)
        assert len(logs) > 0
        assert "[CHECK]" in logs[0]
        assert "22.5°C" in logs[0]
        assert "65%" in logs[0]
        assert "Réservoir: OK" in logs[0]
        assert "1013.25hPa" in logs[0]
    
    def test_log_check_water_empty(self, temp_logger):
        """Check avec réservoir vide."""
        temp_logger.log_check(temp=20.0, water_ok=False)
        
        logs = temp_logger.get_logs(limit=1)
        assert "Réservoir: VIDE !" in logs[0]
    
    def test_log_check_partial(self, temp_logger):
        """Check avec données partielles."""
        temp_logger.log_check(temp=22.5, humidity=None)
        
        logs = temp_logger.get_logs(limit=1)
        assert "22.5°C" in logs[0]
        assert "%" not in logs[0]


class TestLogWatering:
    """Tests pour log_watering()."""
    
    def test_log_watering_manual_success(self, temp_logger):
        """Enregistre un arrosage manuel réussi."""
        temp_logger.log_watering(
            event_type="MANUAL",
            duration=30,
            status="SUCCESS",
            reason=None
        )
        
        logs = temp_logger.get_logs(limit=1)
        assert "[MANUAL]" in logs[0]
        assert "30s" in logs[0]
        assert "SUCCESS" in logs[0]
    
    def test_log_watering_auto_failed(self, temp_logger):
        """Enregistre un arrosage auto échoué."""
        temp_logger.log_watering(
            event_type="AUTO",
            duration=0,
            status="FAILED",
            reason="Water empty"
        )
        
        logs = temp_logger.get_logs(limit=1)
        assert "[AUTO]" in logs[0]
        assert "annulé" in logs[0]
        assert "Water empty" in logs[0]
    
    def test_log_watering_cancelled(self, temp_logger):
        """Enregistre un arrosage annulé."""
        temp_logger.log_watering(
            event_type="MANUAL",
            duration=0,
            status="CANCELLED",
            reason="User abort"
        )
        
        logs = temp_logger.get_logs(limit=1)
        assert "annulé" in logs[0]
        assert "User abort" in logs[0]


class TestLogCamera:
    """Tests pour log_camera()."""
    
    def test_log_camera_capture_success(self, temp_logger):
        """Enregistre une capture photo réussie."""
        # Créer un fichier temporaire pour simuler une photo
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            photo_path = f.name
            f.write(b"fake image data" * 1000)  # ~15KB
        
        try:
            temp_logger.log_camera(action="capture", photo_path=photo_path)
            
            logs = temp_logger.get_logs(limit=1)
            assert "[CAMERA]" in logs[0]
            assert "Photo capturée" in logs[0]
            assert photo_path in logs[0]
            assert "KB" in logs[0]
        
        finally:
            Path(photo_path).unlink(missing_ok=True)
    
    def test_log_camera_capture_failed(self, temp_logger):
        """Enregistre une erreur de capture."""
        temp_logger.log_camera(
            action="capture_failed",
            error="Camera not found"
        )
        
        logs = temp_logger.get_logs(limit=1)
        assert "[CAMERA]" in logs[0]
        assert "Erreur capture" in logs[0]
        assert "Camera not found" in logs[0]


class TestLogError:
    """Tests pour log_error()."""
    
    def test_log_error_error_level(self, temp_logger):
        """Enregistre une erreur avec level ERROR."""
        temp_logger.log_error(
            context="GPIO_17",
            error="Device already in use",
            severity="ERROR"
        )
        
        logs = temp_logger.get_logs(limit=1)
        assert "[ERROR]" in logs[0]
        assert "GPIO_17" in logs[0]
        assert "Device already in use" in logs[0]
    
    def test_log_error_warning_level(self, temp_logger):
        """Enregistre une erreur avec level WARNING."""
        temp_logger.log_error(
            context="API_METEO",
            error="Timeout, retrying",
            severity="WARNING"
        )
        
        logs = temp_logger.get_logs(limit=1)
        assert "[WARNING]" in logs[0]
        assert "API_METEO" in logs[0]


class TestLogGPIO:
    """Tests pour log_gpio_event()."""
    
    def test_log_gpio_read(self, temp_logger):
        """Enregistre une lecture GPIO."""
        temp_logger.log_gpio_event(pin=27, action="read", value=True)
        
        logs = temp_logger.get_logs(limit=1)
        assert "[GPIO]" in logs[0]
        assert "27" in logs[0]
        assert "read" in logs[0]
        assert "True" in logs[0]
    
    def test_log_gpio_write(self, temp_logger):
        """Enregistre une écriture GPIO."""
        temp_logger.log_gpio_event(pin=17, action="write", value=False)
        
        logs = temp_logger.get_logs(limit=1)
        assert "[GPIO]" in logs[0]
        assert "17" in logs[0]
        assert "write" in logs[0]
        assert "False" in logs[0]


class TestGetLogs:
    """Tests pour get_logs()."""
    
    def test_get_logs_empty(self, temp_logger):
        """Retourne message par défaut si log vide."""
        logs = temp_logger.get_logs(limit=20)
        assert len(logs) > 0
        assert "Aucun historique" in logs[0] or len(logs) == 0
    
    def test_get_logs_returns_limit(self, temp_logger):
        """Retourne au maximum N lignes."""
        # Insère 10 logs
        for i in range(10):
            temp_logger.log_check(temp=20 + i, humidity=60 + i)
        
        logs = temp_logger.get_logs(limit=5)
        assert len(logs) == 5
    
    def test_get_logs_reverse_order(self, temp_logger):
        """Retourne les logs en ordre inverse (dernier d'abord)."""
        temp_logger.log_check(temp=20.0)
        temp_logger.log_check(temp=21.0)
        temp_logger.log_check(temp=22.0)
        
        logs = temp_logger.get_logs(limit=3)
        
        # Le dernier doit être 22.0
        assert "22.0°C" in logs[0]
        # Le premier (de ceux-ci) doit être 20.0
        assert "20.0°C" in logs[2]
    
    def test_get_logs_filters_flask(self, temp_logger):
        """Filtre les logs Flask."""
        temp_logger.log_check(temp=20.0)
        
        # Ajouter manuellement un log Flask au fichier
        with open(temp_logger.log_file, 'a', encoding='utf-8') as f:
            f.write("GET /api/status HTTP/1.1\n")
            f.write("POST /api/arroser HTTP/1.1\n")
        
        logs = temp_logger.get_logs(limit=10)
        
        # Les logs Flask ne doivent pas apparaître
        assert not any("GET /" in log for log in logs)
        assert not any("POST /" in log for log in logs)
    
    def test_get_logs_no_file(self):
        """Gère le cas où le fichier log n'existe pas."""
        logger = CentralLogger(log_file="/tmp/nonexistent_log_file_xyz.log")
        logs = logger.get_logs(limit=20)
        
        # Doit retourner un message par défaut
        assert len(logs) > 0
        assert "Aucun historique" in logs[0]


class TestLoggerGeneric:
    """Tests pour les méthodes génériques."""
    
    def test_log_info(self, temp_logger):
        """Enregistre un message info générique."""
        temp_logger.log_info("Ceci est un test")
        
        logs = temp_logger.get_logs(limit=1)
        assert "[INFO]" in logs[0]
        assert "Ceci est un test" in logs[0]
    
    def test_log_debug(self, temp_logger):
        """Enregistre un message debug."""
        temp_logger.log_debug("Debug info")
        
        logs = temp_logger.get_logs(limit=1)
        assert "[DEBUG]" in logs[0]
        assert "Debug info" in logs[0]
    
    def test_clear_logs(self, temp_logger):
        """Vide le fichier log."""
        temp_logger.log_check(temp=20.0)
        
        # Vérifie que log existe
        logs = temp_logger.get_logs(limit=1)
        assert len(logs) > 0
        
        # Vide les logs
        temp_logger.clear_logs()
        
        # Vérifie que file est vide
        content = Path(temp_logger.log_file).read_text()
        assert content == "" or "Log file cleared" in content


class TestLoggerFormatting:
    """Tests du format des messages."""
    
    def test_timestamp_format(self, temp_logger):
        """Vérifie que les timestamps sont formatés correctement."""
        temp_logger.log_check(temp=22.5)
        
        logs = temp_logger.get_logs(limit=1)
        log_line = logs[0]
        
        # Format attendu: "DD/MM/YYYY HH:MM:SS | message"
        # Doit contenir une date au format DD/MM/YYYY
        assert "/" in log_line
        assert "|" in log_line
    
    def test_multiple_logs_format(self, temp_logger):
        """Vérifie que plusieurs logs sont bien formatés."""
        temp_logger.log_check(temp=20.0, water_ok=True)
        temp_logger.log_watering(event_type="MANUAL", duration=30, status="SUCCESS")
        temp_logger.log_error(context="TEST", error="Test error")
        
        logs = temp_logger.get_logs(limit=3)
        
        assert len(logs) == 3
        assert "[CHECK]" in logs[2]
        assert "[MANUAL]" in logs[1]
        assert "[ERROR]" in logs[0]


class TestLoggerIntegration:
    """Tests intégration simulant workflow réel."""
    
    def test_full_watering_workflow(self, temp_logger):
        """Simule un workflow complet d'arrosage."""
        # Check initial
        temp_logger.log_check(temp=22.0, humidity=60, water_ok=True)
        
        # Arrosage manuel
        temp_logger.log_watering(
            event_type="MANUAL",
            duration=30,
            status="SUCCESS"
        )
        
        # Récupère logs
        logs = temp_logger.get_logs(limit=5)
        
        assert len(logs) >= 2
        assert "[CHECK]" in str(logs)
        assert "[MANUAL]" in str(logs)
    
    def test_error_and_recovery(self, temp_logger):
        """Simule une erreur puis récupération."""
        temp_logger.log_error(
            context="GPIO_RELAY",
            error="Pin not ready",
            severity="WARNING"
        )
        
        temp_logger.log_info("Retrying GPIO access...")
        
        temp_logger.log_watering(
            event_type="AUTO",
            duration=30,
            status="SUCCESS"
        )
        
        logs = temp_logger.get_logs(limit=5)
        
        assert "[WARNING]" in str(logs)
        assert "Retrying" in str(logs)
        assert "[AUTO]" in str(logs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
