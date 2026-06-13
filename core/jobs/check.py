"""
Check Job — Relevé toutes les 4 heures

Responsabilité : Job APScheduler exécuté toutes les 4h (0h, 4h, 8h, 12h, 16h, 20h).
Relève température/humidité météo, lit capteurs humidité sol, vérifie réservoir eau.
Enregistre tout en DB et logger.

Usage:
    from core.jobs.check import run_check
    
    result = run_check()
    print(result)  # {"status": "SUCCESS", "data": {...}} ou {"status": "FAILED", ...}
"""

from typing import Dict, Any
from api.meteo import MeteoAPI
from api.sensors import SensorReader
from core.database import db
from core.logger import logger
from core.gpio_manager import gpio_manager


def run_check() -> Dict[str, Any]:
    """
    Job APScheduler : Relevé complet du système.
    
    Exécuté toutes les 4h via cron: hour='0,4,8,12,16,20'
    
    Workflow:
        1. Appel API open-meteo → température, humidité, pression
        2. Lecture capteurs humidité sol (moyenne + par capteur)
        3. Lecture niveau eau (GPIO 27)
        4. Enregistrement en DB (readings + soil_humidity)
        5. Log du check
    
    Returns:
        dict: {
            "status": "SUCCESS",
            "data": {
                "temperature": 22.5,
                "humidity": 65,
                "pressure": 1013.25,
                "water_ok": True,
                "soil_humidity_avg": 69.2,
                "soil_humidity_per_sensor": {1: 65.5, 2: 70.2, ...}
            }
        }
        ou en cas d'erreur:
        {
            "status": "FAILED",
            "error": "..."
        }
    
    Gestion d'erreurs:
        - Aucune exception ne doit sortir (gestion en interne)
        - Loggue l'erreur avec log_error()
        - Continue même si une partie échoue (ex: API down)
    
    Examples:
        result = run_check()
        if result['status'] == "SUCCESS":
            print(f"Température: {result['data']['temperature']}°C")
        else:
            print(f"Erreur: {result['error']}")
    """
    try:
        # 1. Récupère données météo
        meteo_api = MeteoAPI()
        meteo = meteo_api.get_temperature_humidity_pressure()
        
        # Si erreur API, on continue quand même avec les valeurs disponibles
        if meteo['error']:
            temp = None
            humidity = None
            pressure = None
        else:
            temp = meteo.get('temperature')
            humidity = meteo.get('humidity')
            pressure = meteo.get('pressure')
        
        # 2. Lit capteurs humidité sol
        sensor_reader = SensorReader()
        try:
            soil_humidity_per_sensor = sensor_reader.get_all_humidity()
            soil_humidity_avg = sensor_reader.get_average_humidity()
        except Exception as e:
            logger.log_error(context="SENSOR_READ", error=str(e), severity="WARNING")
            soil_humidity_per_sensor = {}
            soil_humidity_avg = None
        
        # 3. Vérifie réservoir eau
        try:
            water_ok = gpio_manager.read_button(27)
        except Exception as e:
            logger.log_error(context="GPIO_27_READ", error=str(e), severity="WARNING")
            water_ok = None
        
        # 4. Enregistre en DB
        db.insert_reading(
            temp_celsius=temp,
            humidity_percent=humidity,
            pressure_hpa=pressure,
            water_level_ok=water_ok
        )
        
        # Enregistre aussi l'humidité sol par capteur
        for sensor_id, humidity_val in soil_humidity_per_sensor.items():
            try:
                db.insert_soil_humidity(sensor_id, humidity_val)
            except Exception as e:
                logger.log_error(
                    context=f"SOIL_INSERT_SENSOR_{sensor_id}",
                    error=str(e),
                    severity="WARNING"
                )
        
        # 5. Log du check
        logger.log_check(
            temp=temp,
            humidity=humidity,
            water_ok=water_ok,
            pressure=pressure
        )
        
        return {
            "status": "SUCCESS",
            "data": {
                "temperature": temp,
                "humidity": humidity,
                "pressure": pressure,
                "water_ok": water_ok,
                "soil_humidity_avg": soil_humidity_avg,
                "soil_humidity_per_sensor": soil_humidity_per_sensor
            }
        }
    
    except Exception as e:
        logger.log_error(context="CHECK_JOB", error=str(e))
        return {
            "status": "FAILED",
            "error": str(e)
        }
