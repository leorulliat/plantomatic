"""
Logger centralisé pour Plantomatic.
Enregistre tous les événements (checks, arrosages, erreurs, photos) dans un fichier
et vers stdout (compatible journalctl pour systemd).

Utilisation:
    from core.logger import logger
    logger.log_check(temp=22.5, humidity=65, water_ok=True)
    logger.log_watering(event_type="MANUAL", duration=30, status="SUCCESS")
    logs = logger.get_logs(limit=20)
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from config.settings import LOG_FILE, LOG_LEVEL, LOG_FORMAT, LOG_DATE_FORMAT


class CentralLogger:
    """Logger centralisé pour tous les événements du système."""
    
    def __init__(self, 
                 log_file: str = None,
                 log_level: str = LOG_LEVEL,
                 log_format: str = LOG_FORMAT,
                 log_date_format: str = LOG_DATE_FORMAT):
        """
        Initialise le logger centralisé.
        
        Args:
            log_file: Chemin fichier log (par défaut: config.LOG_FILE)
            log_level: Niveau log (INFO, DEBUG, ERROR, WARNING)
            log_format: Format des logs
            log_date_format: Format de la date/heure
        """
        self.log_file = log_file or str(LOG_FILE)
        self.log_level = log_level
        
        # Créer le logger principal
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level))
        
        # Handler fichier
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, log_level))
        file_formatter = logging.Formatter(log_format, datefmt=log_date_format)
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Handler console (pour journalctl)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level))
        console_formatter = logging.Formatter(log_format, datefmt=log_date_format)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Filtrer les logs Flask (werkzeug) pour éviter pollution
        werkzeug_logger = logging.getLogger('werkzeug')
        werkzeug_logger.setLevel(logging.ERROR)
    
    # ========== PUBLIC METHODS ==========
    
    def log_check(self, 
                 temp: Optional[float] = None,
                 humidity: Optional[float] = None,
                 water_ok: Optional[bool] = None,
                 pressure: Optional[float] = None) -> None:
        """
        Enregistre un check (toutes les 4h).
        
        Format:
            [CHECK] Météo: 22.5°C (65%) | Pression: 1013hPa | Réservoir: OK
        
        Args:
            temp: Température en °C
            humidity: Humidité relative en %
            water_ok: Booléen niveau eau
            pressure: Pression en hPa
        """
        parts = ["[CHECK]"]
        
        if temp is not None or humidity is not None:
            meteo_str = "Météo:"
            if temp is not None:
                meteo_str += f" {temp}°C"
            if humidity is not None:
                meteo_str += f" ({humidity}%)"
            parts.append(meteo_str)
        
        if pressure is not None:
            parts.append(f"Pression: {pressure}hPa")
        
        if water_ok is not None:
            water_status = "OK" if water_ok else "VIDE !"
            parts.append(f"Réservoir: {water_status}")
        
        message = " | ".join(parts)
        self.logger.info(message)
    
    def log_watering(self, 
                    event_type: str,
                    duration: int,
                    status: str,
                    reason: Optional[str] = None) -> None:
        """
        Enregistre un événement d'arrosage.
        
        Format:
            [AUTO] Arrosage déclenché (30s) | Eau: OK | Status: SUCCESS
            [MANUAL] Arrosage déclenché (30s) | Eau: OK | Status: FAILED - Water empty
        
        Args:
            event_type: "AUTO" ou "MANUAL"
            duration: Durée pompe activée (secondes)
            status: "SUCCESS", "FAILED", "CANCELLED"
            reason: Raison optionnelle (ex: "Water empty", "User triggered")
        """
        parts = [f"[{event_type}]"]
        
        if duration > 0:
            parts.append(f"Arrosage déclenché ({duration}s)")
        else:
            parts.append("Arrosage annulé")
        
        if status:
            parts.append(f"Status: {status}")
        
        if reason:
            parts.append(f"Raison: {reason}")
        
        message = " | ".join(parts)
        
        # Log level dépend du status
        if status == "SUCCESS":
            self.logger.info(message)
        elif status == "FAILED":
            self.logger.warning(message)
        elif status == "CANCELLED":
            self.logger.info(message)
        else:
            self.logger.info(message)
    
    def log_camera(self, 
                  action: str,
                  photo_path: Optional[str] = None,
                  error: Optional[str] = None) -> None:
        """
        Enregistre un événement caméra.
        
        Format:
            [CAMERA] Photo capturée: /photos/photo_20260613_143650.jpg | 256 KB
            [CAMERA] Erreur capture: Camera not found
        
        Args:
            action: "capture", "capture_failed", etc.
            photo_path: Chemin de la photo
            error: Message d'erreur optionnel
        """
        if action == "capture":
            if photo_path:
                file_size = self._get_file_size_kb(photo_path)
                message = f"[CAMERA] Photo capturée: {photo_path} | {file_size} KB"
            else:
                message = "[CAMERA] Photo capturée"
            self.logger.info(message)
        
        elif action == "capture_failed":
            if error:
                message = f"[CAMERA] Erreur capture: {error}"
            else:
                message = "[CAMERA] Erreur capture inconnue"
            self.logger.error(message)
        
        else:
            message = f"[CAMERA] Action: {action}"
            self.logger.info(message)
    
    def log_error(self, 
                 context: str,
                 error: str,
                 severity: str = "ERROR") -> None:
        """
        Enregistre une erreur système.
        
        Format:
            [ERROR] GPIO 17 write failed: Device already in use
            [WARNING] API open-meteo timeout (retrying...)
        
        Args:
            context: Contexte de l'erreur (ex: "GPIO_17", "API_METEO")
            error: Message d'erreur
            severity: "ERROR", "WARNING", "INFO"
        """
        message = f"[{severity}] {context}: {error}"
        
        level = getattr(logging, severity, logging.ERROR)
        self.logger.log(level, message)
    
    def log_gpio_event(self, 
                      pin: int,
                      action: str,
                      value: Optional[bool] = None) -> None:
        """
        Enregistre un accès GPIO (debug).
        
        Format:
            [GPIO] GPIO 27 read: True
            [GPIO] GPIO 17 write: True
        
        Args:
            pin: Numéro GPIO
            action: "read", "write"
            value: Valeur booléenne
        """
        if value is not None:
            message = f"[GPIO] GPIO {pin} {action}: {value}"
        else:
            message = f"[GPIO] GPIO {pin} {action}"
        
        self.logger.debug(message)
    
    def log_info(self, message: str) -> None:
        """
        Enregistre un message info générique.
        
        Args:
            message: Message à enregistrer
        """
        self.logger.info(f"[INFO] {message}")
    
    def log_debug(self, message: str) -> None:
        """
        Enregistre un message debug.
        
        Args:
            message: Message à enregistrer
        """
        self.logger.debug(f"[DEBUG] {message}")
    
    # ========== UTILITY METHODS ==========
    
    def get_logs(self, limit: int = 20) -> List[str]:
        """
        Retourne les N dernières lignes du fichier log.
        Utilisé par le dashboard pour afficher les logs.
        
        Args:
            limit: Nombre de lignes à retourner
        
        Returns:
            List de strings (dernières lignes, inverse order)
        """
        if not Path(self.log_file).exists():
            return ["Aucun historique disponible."]
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Filtrer les lignes vides et les logs Flask
            lines = [
                line.strip()
                for line in lines
                if line.strip() and "GET /" not in line and "POST /" not in line
            ]
            
            # Retourner les N dernières, en ordre inverse (dernier en premier)
            last_lines = lines[-limit:] if lines else []
            last_lines.reverse()
            
            return last_lines if last_lines else ["Aucun historique disponible."]
        
        except Exception as e:
            return [f"Erreur lecture logs: {str(e)}"]
    
    def clear_logs(self) -> None:
        """Vide le fichier log (à utiliser avec prudence)."""
        try:
            Path(self.log_file).write_text("")
            self.logger.info("[SYSTEM] Log file cleared")
        except Exception as e:
            self.logger.error(f"Failed to clear logs: {e}")
    
    @staticmethod
    def _get_file_size_kb(file_path: str) -> int:
        """
        Retourne la taille d'un fichier en KB.
        
        Args:
            file_path: Chemin du fichier
        
        Returns:
            Taille en KB (arrondie)
        """
        try:
            size_bytes = Path(file_path).stat().st_size
            return int(size_bytes / 1024)
        except Exception:
            return 0


# ========== SINGLETON GLOBAL ==========

# Instance unique du logger, importable partout
logger = CentralLogger()
