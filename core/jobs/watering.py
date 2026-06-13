"""
Watering Job — Logique d'arrosage (AUTO + MANUAL)

Responsabilité : Exécute un cycle d'arrosage sécurisé. Partagée entre:
- Job APScheduler (auto-watering à 18h)
- Route Flask POST /api/arroser (manual via dashboard)

Sécurité absolue:
- Vérifie réservoir avant de démarrer
- Coupe relais même en cas d'erreur
- Enregistre tout (DB + logger)

Usage:
    from core.jobs.watering import execute_watering, run_auto_watering
    
    # Manual trigger (depuis dashboard)
    result = execute_watering(event_type="MANUAL", duration_seconds=30)
    
    # Auto trigger (job APScheduler)
    result = run_auto_watering()
"""

import time
from typing import Dict, Any
from core.gpio_manager import gpio_manager
from core.database import db
from core.logger import logger


def execute_watering(event_type: str = "AUTO", duration_seconds: int = 30) -> Dict[str, Any]:
    """
    Exécute un cycle d'arrosage complet (sécurisé).
    
    Args:
        event_type: "AUTO" (job) ou "MANUAL" (route API)
        duration_seconds: Durée pompe activée (30s par défaut)
    
    Returns:
        dict: {
            "success": True,
            "message": "Arrosage manual réussi (30s)"
        }
        ou en cas d'erreur:
        {
            "success": False,
            "error": "Réservoir vide - Arrosage annulé"
        }
    
    Workflow:
        1. Vérifie réservoir eau (GPIO 27)
        2. Si vide → log + DB insert (CANCELLED), return failed
        3. Active relais (GPIO 17)
        4. Attend duration_seconds
        5. Coupe relais (sécurité absolue)
        6. Enregistre succès en DB + logger
    
    Gestion d'erreurs:
        - Coupe relais même en erreur (try/finally implicite par finally)
        - Loggue tout
        - Continue sans lever exception
    
    Examples:
        # Manual trigger
        result = execute_watering(event_type="MANUAL", duration_seconds=30)
        if result['success']:
            print(f"OK: {result['message']}")
        else:
            print(f"Erreur: {result['error']}")
        
        # Auto trigger
        result = execute_watering(event_type="AUTO", duration_seconds=30)
    """
    status = "PENDING"
    reason = None
    
    try:
        # 1. Vérifie réservoir
        water_ok = gpio_manager.read_button(27)
        
        if not water_ok:
            # Réservoir vide - annule l'arrosage
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
        
        # 2. Active relais (GPIO 17)
        gpio_manager.write_output(17, True)
        logger.log_gpio_event(pin=17, action="write", value=True)
        
        # 3. Attend
        time.sleep(duration_seconds)
        
        # 4. Coupe relais (sécurité absolue)
        gpio_manager.write_output(17, False)
        logger.log_gpio_event(pin=17, action="write", value=False)
        
        # 5. Enregistre succès
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
        try:
            gpio_manager.write_output(17, False)
        except:
            pass  # Ignore erreur de sécurité
        
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


def run_auto_watering() -> Dict[str, Any]:
    """
    Job APScheduler : Arrosage automatique à heure fixe (ex: 18h).
    
    Exécuté une fois par jour via cron: hour=18
    
    Vérifie d'abord si mode AUTO est actif en DB (feature future: table "settings").
    Pour l'instant, mode AUTO est toujours actif.
    
    Returns:
        dict: Même format que execute_watering()
    
    Examples:
        result = run_auto_watering()
        print(result)  # {"success": True, "message": "..."}
    """
    try:
        # Futur: vérifie flag AUTO en DB
        # auto_enabled = db.get_setting("watering_auto_enabled", default=True)
        # if not auto_enabled:
        #     logger.log_watering(...)
        #     return {"status": "SKIPPED", ...}
        
        # Pour l'instant, mode AUTO toujours actif
        return execute_watering(event_type="AUTO", duration_seconds=30)
    
    except Exception as e:
        logger.log_error(context="AUTO_WATERING_JOB", error=str(e))
        return {
            "success": False,
            "error": str(e)
        }
