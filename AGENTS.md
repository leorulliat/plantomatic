# AGENTS.md — Définition des Modules & Responsabilités

Ce fichier décrit précisément le **rôle de chaque agent/module** du système Plantomatic, ses responsabilités, dépendances, et interactions.

---

## 📋 Vue d'Ensemble des Agents

```
FLASK APP (app.py)
    ├─→ APScheduler (jobs planifiés)
    ├─→ GPIO Manager (broker GPIO centralisé)
    ├─→ Database (SQLite WAL)
    ├─→ Logger (logs centralisés)
    │
    ├─→ API AGENTS (meteo, sensors, relay, camera)
    │
    └─→ JOB AGENTS (check.py, watering.py)
         ├→ Database (insert readings, watering_events)
         ├→ GPIO Manager (read/write GPIO)
         └→ Logger (enregistrer événements)
```

---

## 🔌 CORE AGENTS

### 1. `core/gpio_manager.py` — Broker GPIO Centralisé

**Responsabilité :** Singleton qui gère TOUS les accès GPIO (lecture/écriture). Évite les conflits "GPIO busy" quand Flask + APScheduler lisent/écrivent simultanément.

**Mode d'opération :**
- 🟢 **Sur RPi réel** : Utilise gpiozero + lgpio
- 🟡 **Mode mock** (MOCK_GPIO=1) : Retourne des valeurs simulées

**Dépendances :**
```python
from gpiozero import Button, OutputDevice, Device
import os
```

**API Publique :**
```python
class GPIOManager:
    def __init__(self):
        """Initialise le broker en singleton (une seule instance)"""
        if os.getenv("MOCK_GPIO") == "1":
            self.mode = "MOCK"
        else:
            self.mode = "REAL"
            Device.pin_factory = None  # Auto-detect lgpio
    
    def read_button(self, pin: int, pull_up=True) -> bool:
        """
        Lit l'état d'un bouton/capteur (GPIO comme input)
        
        Param:
            pin: Numéro GPIO (ex: 27 pour capteur eau)
            pull_up: Résistance de tirage (True = pull-up)
        
        Return:
            bool: True si contact fermé (GND), False si ouvert
        
        Exemple:
            eau_presente = gpio_mgr.read_button(27)
        """
    
    def write_output(self, pin: int, state: bool, active_high=True) -> None:
        """
        Écrit un signal sur un GPIO (output).
        
        Param:
            pin: Numéro GPIO (ex: 17 pour relais)
            state: True=ON (3.3V ou 0V selon active_high), False=OFF
            active_high: True si relais s'active sur 3.3V, False si sur 0V
        
        Exemple:
            gpio_mgr.write_output(17, True)  # Active relais
            time.sleep(30)
            gpio_mgr.write_output(17, False) # Coupe relais
        """
    
    def cleanup(self) -> None:
        """Ferme tous les GPIO proprement. Appelé au shutdown Flask."""

# Singleton global
gpio_manager = GPIOManager()
```

**Exemple d'utilisation :**
```python
from core.gpio_manager import gpio_manager

# Lire le capteur de niveau eau
eau_ok = gpio_manager.read_button(27)

# Activer la pompe pendant 30 secondes
gpio_manager.write_output(17, True)
time.sleep(30)
gpio_manager.write_output(17, False)
```

**Responsabilités critiques :**
- ✅ Une seule instance (singleton)
- ✅ Gestion des ressources (init/cleanup automatiques)
- ✅ Support du mode mock pour tests
- ✅ Pas de conflit d'accès simultané (thread-safety si besoin)

---

### 2. `core/database.py` — Abstraction SQLite + WAL

**Responsabilité :** Couche d'accès à la base de données. Gère initialisation (schéma), requêtes (CRUD), et concurrence (WAL mode).

**Dépendances :**
```python
import sqlite3
from datetime import datetime
from contextlib import contextmanager
```

**API Publique :**
```python
class Database:
    def __init__(self, db_path: str = "plantomatic.db"):
        """Initialise la connection SQLite + WAL mode"""
        self.db_path = db_path
        self._init_wal_mode()
        self._create_tables()
    
    def insert_reading(self, temp_celsius: float = None, 
                       humidity_percent: float = None,
                       pressure_hpa: float = None,
                       water_level_ok: bool = None) -> int:
        """
        Enregistre une lecture (toutes les 4h par le job check).
        
        Return: id de la ligne insérée
        
        Exemple:
            db.insert_reading(
                temp_celsius=22.5,
                humidity_percent=65,
                pressure_hpa=1013.25,
                water_level_ok=True
            )
        """
    
    def insert_soil_humidity(self, sensor_id: int, 
                            humidity_percent: float) -> None:
        """Enregistre une lecture d'humidité pour un capteur"""
    
    def insert_watering_event(self, event_type: str, 
                             duration_seconds: int,
                             status: str, reason: str = None) -> None:
        """
        Enregistre un événement d'arrosage (AUTO/MANUAL).
        
        Param:
            event_type: "AUTO" ou "MANUAL"
            duration_seconds: Durée pompe activée
            status: "SUCCESS", "FAILED", "CANCELLED"
            reason: Ex: "Water empty", "User triggered"
        """
    
    def insert_camera_event(self, photo_path: str, 
                           file_size_kb: int = 0) -> None:
        """Enregistre une photo prise"""
    
    def insert_soil_sensor(self, sensor_name: str, 
                          sensor_pin: int = None) -> int:
        """Crée/enregistre un nouveau capteur d'humidité. Return: sensor_id"""
    
    def get_latest_readings(self, limit: int = 20):
        """Retourne les 20 dernières lectures (pour dashboard)"""
    
    def get_soil_humidity_avg(self) -> float:
        """Retourne la moyenne d'humidité soil de tous les capteurs (dernière lecture)"""
    
    def get_watering_events(self, limit: int = 10):
        """Retourne les 10 derniers événements d'arrosage"""
    
    def delete_old_readings(self, days_old: int = 60) -> int:
        """Supprime les lectures > N jours. Return: nombre de lignes supprimées"""

# Singleton global
db = Database()
```

**Exemple d'utilisation :**
```python
from core.database import db

# Lors d'un check (toutes les 4h)
db.insert_reading(
    temp_celsius=22.5,
    humidity_percent=65,
    pressure_hpa=1013.25,
    water_level_ok=True
)

# Lors d'un arrosage manuel
db.insert_watering_event(
    event_type="MANUAL",
    duration_seconds=30,
    status="SUCCESS",
    reason="User triggered"
)

# Pour le dashboard
readings = db.get_latest_readings(limit=10)
avg_humidity = db.get_soil_humidity_avg()
```

**Schéma créé automatiquement :**
```sql
readings (id, timestamp, temp_celsius, humidity_percent, pressure_hpa, water_level_ok)
soil_sensors (id, sensor_name, sensor_pin, created_at)
soil_humidity_readings (id, timestamp, sensor_id, humidity_percent)
watering_events (id, timestamp, type, duration_seconds, status, reason)
camera_events (id, timestamp, photo_path, file_size_kb)
```

**Responsabilités critiques :**
- ✅ WAL mode activé (concurrence Flask + APScheduler OK)
- ✅ Timeout de 5s si DB verrouillée
- ✅ Insertion atomique (commit automatique)
- ✅ Support multi-senseurs d'humidité

---

### 3. `core/logger.py` — Logs Centralisés (fichier + journal)

**Responsabilité :** Enregistre TOUS les événements du système (checks, arrosages, erreurs, photos) dans un format structuré. Compatible avec `journalctl` pour debug via systemd.

**Dépendances :**
```python
import logging
import os
from datetime import datetime
```

**API Publique :**
```python
class CentralLogger:
    def __init__(self, log_file: str = "plantomatic.log", log_level: str = "INFO"):
        """Configure logging vers fichier + console"""
        self.log_file = log_file
        # Crée un logger pour fichier + un pour stdout (journalctl)
    
    def log_check(self, temp: float, humidity: float, water_ok: bool, 
                  pressure: float = None) -> None:
        """
        Enregistre un check (job toutes les 4h).
        
        Format: [CHECK] Météo: 22.5°C (65%) | Pression: 1013hPa | Réservoir: OK
        """
    
    def log_watering(self, event_type: str, duration: int, 
                    status: str, reason: str = None) -> None:
        """
        Enregistre un événement d'arrosage.
        
        Exemple:
            [AUTO] Arrosage déclenché (30s) | Eau: OK | Status: SUCCESS
            [MANUAL] Arrosage déclenché (30s) | Eau: OK | Status: FAILED - Water empty
        """
    
    def log_camera(self, action: str, photo_path: str = None, 
                  error: str = None) -> None:
        """Enregistre une capture photo ou erreur caméra"""
    
    def log_error(self, context: str, error: str, severity: str = "ERROR") -> None:
        """Enregistre une erreur système avec contexte"""
    
    def log_gpio_event(self, pin: int, action: str, value: bool) -> None:
        """Enregistre un accès GPIO (debug)"""
    
    def get_logs(self, nb_lines: int = 20) -> list:
        """Retourne les N dernières lignes du fichier log (pour dashboard)"""

# Singleton global
logger = CentralLogger()
```

**Exemple d'utilisation :**
```python
from core.logger import logger

# Dans job check
logger.log_check(temp=22.5, humidity=65, water_ok=True, pressure=1013.25)

# Dans job arrosage
logger.log_watering(event_type="MANUAL", duration=30, status="SUCCESS")

# Dans route photo
logger.log_camera(action="capture", photo_path="/photos/img_20260613_143022.jpg")

# Pour le dashboard
logs = logger.get_logs(20)
```

**Format de sortie :**
```
2026-06-13 14:30:22 | [CHECK] Météo: 22.5°C (65%) | Pression: 1013hPa | Réservoir: OK
2026-06-13 14:35:10 | [MANUAL] Arrosage déclenché (30s) | Eau: OK | Status: SUCCESS
2026-06-13 14:36:50 | [CAMERA] Photo capturée: /photos/img_20260613_143650.jpg (256 KB)
2026-06-13 15:02:33 | [ERROR] GPIO 17 write failed: Device already in use
```

**Responsabilités critiques :**
- ✅ Format lisible et parsable
- ✅ Compatible `journalctl -u dashboard.service -f`
- ✅ Filtrage logs Flask (werkzeug)
- ✅ Accessible via `/api/logs` du dashboard

---

## 💼 JOB AGENTS (APScheduler)

### 4. `core/jobs/check.py` — Job Check (toutes les 4h)

**Responsabilité :** Exécuté par APScheduler toutes les 4 heures. Relève température/humidité météo, lit capteurs, vérifie réservoir eau, enregistre tout en DB.

**Dépendances :**
```python
from api.meteo import MeteoAPI
from core.sensors import SensorReader
from core.database import db
from core.logger import logger
from core.gpio_manager import gpio_manager
```

**Fonction Principale :**
```python
def run_check() -> dict:
    """
    Job APScheduler : Exécuté toutes les 4h.
    
    Workflow:
    1. Appel API open-meteo → température, humidité, pression
    2. Lecture capteurs humidité sol (moyenne)
    3. Lecture niveau eau (GPIO 27)
    4. Enregistrement en DB
    5. Enregistrement dans logs
    
    Return:
        dict: {"status": "SUCCESS", "data": {...}} ou {"status": "FAILED", "error": "..."}
    
    Raises:
        Aucune (gère les erreurs en interne, log l'erreur, continue)
    """
    try:
        # 1. Récupère météo
        meteo_api = MeteoAPI()
        meteo = meteo_api.get_temperature_humidity_pressure()
        
        # 2. Lit capteurs humidité sol
        sensor_reader = SensorReader()
        soil_humidity_avg = sensor_reader.get_average_humidity()
        
        # 3. Vérifie réservoir eau
        water_ok = gpio_manager.read_button(27)
        
        # 4. Enregistre en DB
        db.insert_reading(
            temp_celsius=meteo.get("temperature"),
            humidity_percent=meteo.get("humidity"),
            pressure_hpa=meteo.get("pressure"),
            water_level_ok=water_ok
        )
        
        # Enregistre aussi l'humidité sol par capteur
        for sensor_id, humidity in sensor_reader.get_all_humidity().items():
            db.insert_soil_humidity(sensor_id, humidity)
        
        # 5. Log
        logger.log_check(
            temp=meteo.get("temperature"),
            humidity=meteo.get("humidity"),
            water_ok=water_ok,
            pressure=meteo.get("pressure")
        )
        
        return {
            "status": "SUCCESS",
            "data": {
                "temperature": meteo.get("temperature"),
                "humidity": meteo.get("humidity"),
                "pressure": meteo.get("pressure"),
                "water_ok": water_ok,
                "soil_humidity_avg": soil_humidity_avg
            }
        }
    
    except Exception as e:
        logger.log_error(context="CHECK_JOB", error=str(e))
        return {"status": "FAILED", "error": str(e)}
```

**Configuration APScheduler :**
```python
# Dans app.py
from apscheduler.schedulers.background import BackgroundScheduler
from core.jobs.check import run_check

scheduler = BackgroundScheduler()
scheduler.add_job(
    run_check,
    'cron',
    hour='0,4,8,12,16,20',  # 0h, 4h, 8h, 12h, 16h, 20h
    id='check_job'
)
scheduler.start()
```

**Responsabilités critiques :**
- ✅ Isolé : pas de Flask request context
- ✅ Testable : importez `run_check()` et appelez directement
- ✅ Résilient : gère erreurs, log et continue
- ✅ Idempotent : safe à relancer manuellement

---

### 5. `core/jobs/watering.py` — Job Arrosage (AUTO + MANUAL)

**Responsabilité :** Logique d'arrosage, partagée entre :
- Job APScheduler (arrosage auto à une heure fixe)
- Route Flask POST /api/arroser (arrosage manuel depuis dashboard)

**Dépendances :**
```python
from core.gpio_manager import gpio_manager
from core.database import db
from core.logger import logger
import time
```

**Fonction Principale :**
```python
def execute_watering(event_type: str = "AUTO", duration_seconds: int = 30) -> dict:
    """
    Exécute un cycle d'arrosage complet (sécurisé).
    
    Param:
        event_type: "AUTO" (job APScheduler) ou "MANUAL" (route Flask)
        duration_seconds: Durée pompe activée (30s par défaut)
    
    Return:
        dict: {"success": True, "message": "..."} ou {"success": False, "error": "..."}
    
    Workflow:
    1. Vérifie réservoir eau (GPIO 27)
    2. Si vide → log erreur, return failed, exit
    3. Active relais (GPIO 17)
    4. Attend duration_seconds
    5. Coupe relais (sécurité absolue)
    6. Enregistre événement en DB + logger
    """
    status = "PENDING"
    reason = None
    
    try:
        # 1. Vérifie réservoir
        water_ok = gpio_manager.read_button(27)
        
        if not water_ok:
            logger.log_watering(
                event_type=event_type,
                duration=0,
                status="CANCELLED",
                reason="Réservoir vide"
            )
            db.insert_watering_event(
                event_type=event_type,
                duration_seconds=0,
                status="CANCELLED",
                reason="Réservoir vide"
            )
            return {
                "success": False,
                "error": "Réservoir vide - Arrosage annulé"
            }
        
        # 2. Active relais
        logger.log_gpio_event(pin=17, action="write", value=True)
        gpio_manager.write_output(17, True)
        
        # 3. Attend
        time.sleep(duration_seconds)
        
        # 4. Coupe relais (sécurité absolue)
        gpio_manager.write_output(17, False)
        logger.log_gpio_event(pin=17, action="write", value=False)
        
        status = "SUCCESS"
        reason = None
        
        logger.log_watering(
            event_type=event_type,
            duration=duration_seconds,
            status=status,
            reason=reason
        )
        db.insert_watering_event(
            event_type=event_type,
            duration_seconds=duration_seconds,
            status=status,
            reason=reason
        )
        
        return {
            "success": True,
            "message": f"Arrosage {event_type.lower()} réussi ({duration_seconds}s)"
        }
    
    except Exception as e:
        # Sécurité : coupe relais même en erreur
        gpio_manager.write_output(17, False)
        logger.log_error(context="WATERING_JOB", error=str(e))
        
        db.insert_watering_event(
            event_type=event_type,
            duration_seconds=duration_seconds,
            status="FAILED",
            reason=str(e)
        )
        
        return {
            "success": False,
            "error": f"Erreur arrosage : {str(e)}"
        }
```

**Job APScheduler (Auto) :**
```python
def run_auto_watering() -> dict:
    """
    Job APScheduler : Exécuté à une heure fixe (ex: 18h).
    Vérifie d'abord si mode AUTO est actif en DB.
    """
    # Vérifie flag AUTO en DB (futur: ajouter table "settings")
    auto_enabled = db.get_setting("watering_auto_enabled", default=True)
    
    if not auto_enabled:
        logger.log_watering(
            event_type="AUTO",
            duration=0,
            status="CANCELLED",
            reason="Mode AUTO désactivé"
        )
        return {"status": "SKIPPED", "reason": "Mode AUTO off"}
    
    return execute_watering(event_type="AUTO", duration_seconds=30)
```

**Configuration APScheduler :**
```python
# Dans app.py
from core.jobs.watering import run_auto_watering

scheduler.add_job(
    run_auto_watering,
    'cron',
    hour=18,  # 18:00 = 18h
    id='auto_watering_job'
)
```

**Responsabilités critiques :**
- ✅ Sécurité absolue : coupe relais même en erreur
- ✅ Testable en isolation (pas Flask request)
- ✅ Shared entre auto (job) + manual (route)
- ✅ Idempotent : peut relancer manuellement sans risque

---

## 🌐 API AGENTS

### 6. `api/meteo.py` — Requêtes API Météo

**Responsabilité :** Appelle l'API open-meteo pour récupérer température, humidité relative, pression atmosphérique pour Chambéry.

**Dépendances :**
```python
import requests
```

**API Publique :**
```python
class MeteoAPI:
    LATITUDE = 45.5646      # Chambéry
    LONGITUDE = 5.9178
    TIMEOUT = 4             # 4 secondes
    
    def get_temperature_humidity_pressure(self) -> dict:
        """
        Requête API open-meteo.
        
        Return:
            dict: {
                "temperature": 22.5,        # °C
                "humidity": 65,             # %
                "pressure": 1013.25,        # hPa
                "error": False
            }
            ou
            {
                "temperature": "--",
                "humidity": "--",
                "pressure": "--",
                "error": True
            }
        
        Exemple:
            meteo_api = MeteoAPI()
            meteo = meteo_api.get_temperature_humidity_pressure()
            print(f"Température: {meteo['temperature']}°C")
        """
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={self.LATITUDE}&longitude={self.LONGITUDE}"
                f"&current=temperature_2m,relative_humidity_2m,pressure"
            )
            response = requests.get(url, timeout=self.TIMEOUT)
            data = response.json()
            
            return {
                "temperature": data['current']['temperature_2m'],
                "humidity": data['current']['relative_humidity_2m'],
                "pressure": data['current']['pressure'],
                "error": False
            }
        except Exception as e:
            logger.log_error(context="METEO_API", error=str(e))
            return {
                "temperature": "--",
                "humidity": "--",
                "pressure": "--",
                "error": True
            }
```

**Responsabilités critiques :**
- ✅ Timeout court (4s)
- ✅ Gestion d'erreur gracieuse (return "--", error=True)
- ✅ Compatible mode mock (retourne dict, pas d'objet complexe)

---

### 7. `api/sensors.py` — Lecture Capteurs (Humidité Sol)

**Responsabilité :** Lit les 5-6 capteurs d'humidité sol. Pour l'instant, retourne des données mockées. Plus tard, lira un ADC (MCP3008).

**Dépendances :**
```python
import os
from core.database import db
```

**API Publique :**
```python
class SensorReader:
    def __init__(self):
        """Initialise lecteur capteurs"""
        self.mock_mode = os.getenv("MOCK_GPIO") == "1"
    
    def get_all_humidity(self) -> dict:
        """
        Retourne humidité (%) pour CHAQUE capteur enregistré en DB.
        
        Return:
            dict: {
                1: 65.5,    # sensor_id: humidity%
                2: 70.2,
                3: 68.1,
                ...
            }
        
        Mode MOCK:
            Retourne valeurs constantes (ex: 65-75%)
        Mode RÉEL:
            Lit ADC (MCP3008) pour chaque capteur enregistré
        """
        if self.mock_mode:
            return {
                1: 65.5,
                2: 70.2,
                3: 68.1,
                4: 72.8,
                5: 69.4
            }
        else:
            # À implémenter : lecture ADC réelle (MCP3008)
            # Pour l'instant, raise error si pas d'ADC
            raise NotImplementedError("ADC MCP3008 non connecté")
    
    def get_average_humidity(self) -> float:
        """
        Retourne la moyenne d'humidité sol (simple mean).
        
        Return:
            float: Humidité moyenne %
        
        Exemple:
            reader = SensorReader()
            avg = reader.get_average_humidity()  # Ex: 69.2
        """
        all_humidity = self.get_all_humidity()
        if not all_humidity:
            return 0.0
        return sum(all_humidity.values()) / len(all_humidity)
    
    def get_humidity_by_sensor(self, sensor_id: int) -> float:
        """Retourne humidité pour un capteur spécifique"""
        all_humidity = self.get_all_humidity()
        return all_humidity.get(sensor_id, 0.0)
```

**Responsabilités critiques :**
- ✅ Mode mock supporté (données constantes)
- ✅ Flexible : dynamique par rapport à DB (non hard-codé)
- ✅ Simple (moyenne = moyenne arithmétique)

---

### 8. `api/relay.py` — Commande Relais

**Responsabilité :** Encapsule la commande du relais pompe. Généralement appelée par `core/jobs/watering.py`.

**Dépendances :**
```python
from core.gpio_manager import gpio_manager
```

**API Publique :**
```python
class RelayController:
    def __init__(self, gpio_pin: int = 17):
        self.pin = gpio_pin
    
    def activate(self, duration_seconds: int = 30) -> bool:
        """Activerelais pendant N secondes (blocage)"""
        # Généralement appelé par execute_watering() dans jobs/watering.py
        # Pas d'utilisation directe recommandée (passer par jobs/watering.py)
    
    def deactivate(self) -> None:
        """Coupe relais immédiatement"""
    
    def is_active(self) -> bool:
        """Vérifie si relais est actuellement actif (optionnel)"""
```

**Note :** En pratique, le relais est commandé directement par `execute_watering()`. Ce module peut être ignoré ou utilisé pour des tests isolés.

---

### 9. `api/camera.py` — Capture Photos

**Responsabilité :** Capture une photo via libcamera (caméra RPi native). Stockage configurable.

**Dépendances :**
```python
import subprocess
from pathlib import Path
from datetime import datetime
```

**API Publique :**
```python
class CameraController:
    def __init__(self, photo_dir: str = "/home/leo/plantomatic/photos"):
        self.photo_dir = Path(photo_dir)
        self.photo_dir.mkdir(exist_ok=True, parents=True)
    
    def capture_photo(self) -> dict:
        """
        Capture une photo et l'enregistre sur disque.
        
        Return:
            dict: {
                "success": True,
                "photo_path": "/home/.../photo_20260613_143022.jpg",
                "file_size_kb": 256
            }
            ou
            {
                "success": False,
                "error": "Camera not found or timeout"
            }
        
        Workflow:
        1. Génère filename unique (timestamp)
        2. Exécute libcamera-still
        3. Enregistre événement en DB + logger
        4. Retourne chemin photo
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            photo_filename = f"photo_{timestamp}.jpg"
            photo_path = self.photo_dir / photo_filename
            
            # Capture via libcamera
            cmd = [
                "libcamera-still",
                "-o", str(photo_path),
                "--timeout", "2000"  # 2 secondes
            ]
            subprocess.run(cmd, check=True, timeout=5)
            
            # Fichier size
            file_size_kb = photo_path.stat().st_size / 1024
            
            # Enregistre en DB + logger
            from core.database import db
            from core.logger import logger
            
            db.insert_camera_event(str(photo_path), int(file_size_kb))
            logger.log_camera(action="capture", photo_path=str(photo_path))
            
            return {
                "success": True,
                "photo_path": str(photo_path),
                "file_size_kb": int(file_size_kb)
            }
        
        except Exception as e:
            logger.log_camera(action="capture_failed", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
```

**Responsabilités critiques :**
- ✅ Stockage configurable (via config/settings.py)
- ✅ Filename unique (timestamp)
- ✅ Enregistrement en DB automatique
- ✅ Gestion erreur gracieuse

---

## 🚀 FLASK APP AGENT

### 10. `app.py` — Flask + APScheduler

**Responsabilité :** Point d'entrée de l'application. Initialise :
- Flask web server
- APScheduler (jobs planifiés)
- Database + Logger
- Routes HTTP

**Dépendances :**
```python
from flask import Flask, jsonify, request, render_template
from apscheduler.schedulers.background import BackgroundScheduler
import os
```

**Structure Principale :**
```python
app = Flask(__name__)

# ========== INITIALISATION ==========
def init_app():
    """Appelé au démarrage (setup global)"""
    
    # 1. Initialise base de données
    from core.database import db
    
    # 2. Initialise logger
    from core.logger import logger
    
    # 3. Initialise APScheduler
    from apscheduler.schedulers.background import BackgroundScheduler
    from core.jobs.check import run_check
    from core.jobs.watering import run_auto_watering
    
    scheduler = BackgroundScheduler()
    
    # Job check : toutes les 4h (0h, 4h, 8h, 12h, 16h, 20h)
    scheduler.add_job(
        run_check,
        'cron',
        hour='0,4,8,12,16,20',
        id='check_job'
    )
    
    # Job arrosage auto : tous les jours à 18h
    scheduler.add_job(
        run_auto_watering,
        'cron',
        hour=18,
        id='auto_watering_job'
    )
    
    scheduler.start()
    logger.log_error(context="APP_INIT", error="App initialized successfully", severity="INFO")

# ========== ROUTES HTTP ==========

@app.route('/')
def home():
    """Affiche le dashboard HTML"""
    return render_template('dashboard.html')

@app.route('/api/status', methods=['GET'])
def api_status():
    """
    Retourne l'état instantané : eau, météo, humidité sol.
    Appelé par le dashboard chaque X secondes.
    
    Response:
        {
            "timestamp": "2026-06-13T14:30:22",
            "water_level": {"present": true},
            "meteo": {
                "temperature": 22.5,
                "humidity": 65,
                "pressure": 1013.25
            },
            "soil_humidity_avg": 69.2,
            "error": false
        }
    """
    try:
        from api.meteo import MeteoAPI
        from api.sensors import SensorReader
        from core.gpio_manager import gpio_manager
        
        water_ok = gpio_manager.read_button(27)
        
        meteo_api = MeteoAPI()
        meteo = meteo_api.get_temperature_humidity_pressure()
        
        sensor_reader = SensorReader()
        soil_humidity_avg = sensor_reader.get_average_humidity()
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "water_level": {"present": water_ok},
            "meteo": meteo,
            "soil_humidity_avg": soil_humidity_avg,
            "error": False
        })
    
    except Exception as e:
        logger.log_error(context="API_STATUS", error=str(e))
        return jsonify({"error": True, "message": str(e)}), 500

@app.route('/api/arroser', methods=['POST'])
def api_arroser():
    """
    Déclenche un arrosage manuel.
    
    Body (optionnel):
        {
            "duration_seconds": 30  # 30 par défaut
        }
    
    Response:
        {
            "success": true,
            "message": "Arrosage manuel réussi (30s)"
        }
        ou
        {
            "success": false,
            "error": "Réservoir vide - Arrosage annulé"
        }
    """
    try:
        from core.jobs.watering import execute_watering
        
        duration = request.json.get("duration_seconds", 30) if request.json else 30
        result = execute_watering(event_type="MANUAL", duration_seconds=duration)
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.log_error(context="API_ARROSER", error=str(e))
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/logs', methods=['GET'])
def api_logs():
    """
    Retourne les derniers logs.
    
    Query params:
        ?limit=20  (par défaut)
    
    Response:
        {
            "logs": [
                "[CHECK] Météo: 22.5°C (65%) ...",
                "[MANUAL] Arrosage déclenché (30s) ...",
                ...
            ]
        }
    """
    from core.logger import logger
    
    limit = request.args.get("limit", 20, type=int)
    logs = logger.get_logs(limit)
    
    return jsonify({"logs": logs})

@app.route('/api/camera', methods=['POST'])
def api_camera():
    """
    Capture une photo.
    
    Response:
        {
            "success": true,
            "photo_path": "/home/.../photo_20260613_143022.jpg"
        }
        ou
        {
            "success": false,
            "error": "Camera not found"
        }
    """
    try:
        from api.camera import CameraController
        
        camera = CameraController()
        result = camera.capture_photo()
        
        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        logger.log_error(context="API_CAMERA", error=str(e))
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """Retourne les settings (mode AUTO, durée, etc.) - futur"""
    # À implémenter : retourne settings stockées en DB
    pass

@app.route('/api/settings', methods=['POST'])
def api_set_settings():
    """Modifie settings (mode AUTO, durée, etc.) - futur"""
    # À implémenter : update settings en DB
    pass

# ========== TEARDOWN ==========

@app.teardown_appcontext
def cleanup_gpio(exception=None):
    """Ferme GPIO proprement au shutdown Flask"""
    from core.gpio_manager import gpio_manager
    gpio_manager.cleanup()

# ========== LAUNCH ==========

if __name__ == '__main__':
    init_app()
    app.run(host='0.0.0.0', port=5000, debug=False)
    # Debug=False car app tourne via systemd (logging via journalctl)
```

**Responsabilités critiques :**
- ✅ Initialise tout (DB, logger, scheduler)
- ✅ Routes isolées (appels à core/ + api/)
- ✅ Error handling gracieux
- ✅ Cleanup GPIO au shutdown

---

## 🛠️ TOOL AGENTS

### 11. `tools/setup_db.py` — Initialisation Base de Données

**Responsabilité :** Script manuel pour créer/réinitialiser la base de données (rarement appelé).

```python
#!/usr/bin/env python3
"""
Usage:
    python tools/setup_db.py          # Crée DB vierge
    python tools/setup_db.py --reset  # Supprime + recrée (attention!)
    python tools/setup_db.py --add-sensors  # Ajoute 5 capteurs de test
"""

import sys
from pathlib import Path
from core.database import db

def setup_db(reset=False, add_test_sensors=False):
    if reset:
        Path("plantomatic.db").unlink(missing_ok=True)
        print("✅ Base de données réinitialisée")
    
    db = Database()
    print("✅ DB créée avec schéma")
    
    if add_test_sensors:
        for i in range(1, 6):
            db.insert_soil_sensor(f"Capteur {i}", pin=None)
        print("✅ 5 capteurs de test ajoutés")

if __name__ == "__main__":
    reset = "--reset" in sys.argv
    add_test = "--add-sensors" in sys.argv
    setup_db(reset=reset, add_test_sensors=add_test)
```

---

### 12. `tools/export_and_clean.py` — Export & Cleanup

**Responsabilité :** Script manuel pour exporter données anciennes en CSV et nettoyer la DB (exécuté entre absences).

```python
#!/usr/bin/env python3
"""
Export readings > N jours en CSV, puis supprime de la DB.

Usage:
    python tools/export_and_clean.py              # Export > 60 jours
    python tools/export_and_clean.py --days 30    # Export > 30 jours
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path
from core.database import db

def export_and_cleanup(days_old=60):
    export_dir = Path("./exports")
    export_dir.mkdir(exist_ok=True)
    
    cutoff_date = datetime.now() - timedelta(days=days_old)
    
    # Récupère readings avant cutoff
    # À implémenter : query custom sur DB
    
    # Export en CSV
    csv_file = export_dir / f"readings_{cutoff_date.date()}.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "temperature", "humidity", "pressure", "water_level"])
        writer.writeheader()
        # Écrit rows...
    
    print(f"✅ Exported {csv_file}")
    
    # Supprime de DB
    deleted_count = db.delete_old_readings(days_old=days_old)
    print(f"✅ Cleaned up {deleted_count} readings")

if __name__ == "__main__":
    import sys
    days = 60
    if "--days" in sys.argv:
        days = int(sys.argv[sys.argv.index("--days") + 1])
    export_and_cleanup(days_old=days)
```

---

## 🧪 TEST AGENTS

### 13. Structure Tests

**Responsabilité :** Permettre tests isolés sur Windows/WSL (mock) et RPi (hardware).

```
tests/
├── __init__.py
│
├── unit/
│   ├── test_jobs.py
│   │   ├── test_run_check()         # Job check : lecture meteo + DB insert
│   │   ├── test_execute_watering()  # Logique arrosage (succes/fail)
│   │   └── ...
│   │
│   ├── test_database.py
│   │   ├── test_insert_reading()
│   │   ├── test_insert_watering_event()
│   │   ├── test_get_latest_readings()
│   │   └── ...
│   │
│   ├── test_sensors.py
│   │   ├── test_get_all_humidity()      # Mode mock
│   │   ├── test_get_average_humidity()
│   │   └── ...
│   │
│   └── test_meteo.py
│       ├── test_get_temperature_humidity_pressure()  # API mock
│       └── ...
│
└── hardware/              ← Exécuté UNIQUEMENT sur RPi
    ├── test_water_level.py       # GPIO 27
    ├── test_relay.py            # GPIO 17
    ├── test_camera.py           # libcamera
    └── test_soil_humidity.py     # ADC MCP3008
```

**Exécution :**
```bash
# Sur PC/WSL (mock)
export MOCK_GPIO=1
pytest tests/unit/

# Sur RPi (hardware réel)
pytest tests/unit/          # Tests métier
python tests/hardware/test_water_level.py  # Validations GPIO isolées
```

---

## 📊 Diagramme d'Interactions

```
APScheduler (Background)
    ├─→ run_check() [toutes les 4h]
    │   ├→ MeteoAPI.get_temperature_humidity_pressure()
    │   ├→ SensorReader.get_all_humidity()
    │   ├→ GPIOManager.read_button(27)
    │   ├→ Database.insert_reading()
    │   ├→ Database.insert_soil_humidity()
    │   └→ Logger.log_check()
    │
    └─→ run_auto_watering() [tous les jours 18h]
        ├→ Database.get_setting("watering_auto_enabled")
        └→ execute_watering(event_type="AUTO")
            ├→ GPIOManager.read_button(27)  [vérifie eau]
            ├→ GPIOManager.write_output(17, True)  [activate]
            ├→ time.sleep(30)
            ├→ GPIOManager.write_output(17, False) [stop]
            ├→ Database.insert_watering_event()
            └→ Logger.log_watering()

Flask Routes (HTTP)
    ├─→ GET /api/status
    │   ├→ MeteoAPI.get_temperature_humidity_pressure()
    │   ├→ SensorReader.get_average_humidity()
    │   ├→ GPIOManager.read_button(27)
    │   └→ return JSON
    │
    ├─→ POST /api/arroser
    │   └→ execute_watering(event_type="MANUAL")
    │       [même workflow que run_auto_watering()]
    │
    ├─→ GET /api/logs
    │   └→ Logger.get_logs(limit)
    │
    ├─→ POST /api/camera
    │   ├→ CameraController.capture_photo()
    │   ├→ Database.insert_camera_event()
    │   └→ Logger.log_camera()
    │
    └─→ GET / (Dashboard HTML)
```

---

## ✅ Checklist d'Implémentation

Par ordre de priorité :

- [ ] **1. core/database.py** — SQLite + WAL + schéma (aucune dépendance)
- [ ] **2. core/logger.py** — Logs centralisés (dépend: DB)
- [ ] **3. core/jobs/check.py** — Job check (dépend: DB, Logger, API)
- [ ] **4. core/jobs/watering.py** — Logique arrosage (dépend: DB, Logger, GPIO Manager)
- [ ] **5. api/meteo.py** — Requête météo (aucune dépendance GPIO)
- [ ] **6. api/sensors.py** — Lecture capteurs (mode mock d'abord)
- [ ] **7. app.py** — Flask + routes API (dépend: tout le reste)
- [ ] **8. core/gpio_manager.py** — Broker GPIO (quand capteurs physiques testés)
- [ ] **9. api/camera.py** — Capture caméra (quand caméra physique prête)
- [ ] **10. tools/setup_db.py & export_and_clean.py** — Maintenance
- [ ] **11. tests/** — Tests unitaires + hardware

---

## 📚 Exemple Complet : Workflow Arrosage Manuel

```
Utilisateur clique "Arroser" sur dashboard
    ↓
POST /api/arroser (Flask)
    ↓
execute_watering(event_type="MANUAL", duration_seconds=30)
    ├─1. gpio_manager.read_button(27)  → eau_ok=True
    ├─2. gpio_manager.write_output(17, True)  → relais ON
    ├─3. time.sleep(30)
    ├─4. gpio_manager.write_output(17, False) → relais OFF
    ├─5. db.insert_watering_event(type="MANUAL", duration=30, status="SUCCESS")
    ├─6. logger.log_watering(type="MANUAL", duration=30, status="SUCCESS")
    └─Return: {"success": True, "message": "Arrosage réussi (30s)"}
    ↓
Dashboard affiche notification "✅ Arrosage réussi"
Dashboard rafraîchit logs et historique (via GET /api/logs)
```

---

**Status :** ✅ Architecture validée, prête pour implémentation  
**Dernière mise à jour :** 2026-06-13
