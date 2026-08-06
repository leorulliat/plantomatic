"""
Configuration centralisée pour Plantomatic.
Toutes les constantes et paramètres système sont définis ici.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ========== PATHS & DIRECTORIES ==========
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = Path(os.getenv("DB_PATH", str(PROJECT_ROOT / "plantomatic.db")))
LOG_FILE = Path(os.getenv("LOG_PATH", str(PROJECT_ROOT / "plantomatic.log")))
PHOTO_DIR = Path(os.getenv("PHOTO_DIR", str(PROJECT_ROOT / "photos")))
BACKUP_PHOTO_DIR = Path(os.getenv("BACKUP_PHOTO_DIR", str(PROJECT_ROOT / "photos")))
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", str(PROJECT_ROOT / "exports")))

# Créer les répertoires s'ils n'existent pas
PHOTO_DIR.mkdir(exist_ok=True, parents=True)
BACKUP_PHOTO_DIR.mkdir(exist_ok=True, parents=True)
EXPORT_DIR.mkdir(exist_ok=True, parents=True)


def _is_usb_storage_available(path: Path) -> bool:
    """Retourne True si le dossier existe, est accessible et se trouve sur un support distinct."""
    try:
        if not path.exists() or not path.is_dir() or not os.access(path, os.W_OK):
            return False

        if os.path.ismount(str(path)):
            return True

        return path.resolve().stat().st_dev != PROJECT_ROOT.resolve().stat().st_dev
    except OSError:
        return False


def get_photo_storage_dir() -> Path:
    """Retourne le dossier de stockage des photos utilisé dans l'application."""
    if PHOTO_DIR != BACKUP_PHOTO_DIR and _is_usb_storage_available(PHOTO_DIR):
        return PHOTO_DIR
    return BACKUP_PHOTO_DIR

# ========== GPIO PINS ==========
GPIO_WATER_LEVEL = 27      # Capteur niveau eau (input, pull-up)
GPIO_RELAY = 17            # Relais pompe (output)

# ========== SCHEDULER CONFIGURATION ==========
CHECK_INTERVAL_HOURS = [0, 4, 8, 12, 16, 20]  # Heures de check (toutes les 4h)
WATERING_TIME_HOUR = 18                         # Arrosage automatique à 18h (18:00)
WATERING_DURATION_SECONDS = 30                  # Durée pompe par défaut (30s)

# ========== CAMERA CONFIGURATION ==========
PHOTO_MAX_SIZE_MB = 5
LIBCAMERA_TIMEOUT_MS = 2000  # libcamera-still timeout (2 secondes)

# ========== DATABASE CONFIGURATION ==========
DB_BACKUP_DIR = str(EXPORT_DIR)
DB_CLEANUP_DAYS = 60         # Garder 60 jours de données, puis archiver
DB_BUSY_TIMEOUT_MS = 5000    # 5 secondes si DB verrouillée (WAL mode)

# ========== LOGGING CONFIGURATION ==========
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s | %(message)s"
LOG_DATE_FORMAT = "%d/%m/%Y %H:%M:%S"

# ========== DEVELOPMENT MODE ==========
MOCK_GPIO = os.getenv("MOCK_GPIO", "0") == "1"
DEBUG = os.getenv("DEBUG", "0") == "1"

# ========== FLASK CONFIGURATION ==========
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = DEBUG
