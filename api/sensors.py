"""
SensorReader — Lecteur capteurs d'humidité sol

Responsabilité : Lit les 5-6 capteurs d'humidité sol. Pour l'instant, retourne 
des données mockées. Plus tard, lira un ADC (MCP3008) quand le matériel sera prêt.

Usage:
    from api.sensors import SensorReader
    
    reader = SensorReader()
    all_humidity = reader.get_all_humidity()  # {1: 65.5, 2: 70.2, ...}
    avg = reader.get_average_humidity()        # 69.2
    sensor1 = reader.get_humidity_by_sensor(1) # 65.5
"""

import os
from typing import Dict


class SensorReader:
    """Lecteur capteurs d'humidité sol."""
    
    def __init__(self):
        """Initialise lecteur capteurs."""
        self.mock_mode = os.getenv("MOCK_GPIO") == "1"
    
    def get_all_humidity(self) -> Dict[int, float]:
        """
        Retourne humidité (%) pour CHAQUE capteur enregistré en DB.
        
        Returns:
            dict: {
                1: 65.5,    # sensor_id: humidity%
                2: 70.2,
                3: 68.1,
                ...
            }
        
        Mode MOCK:
            Retourne valeurs constantes (65-75%)
        Mode RÉEL:
            Lit ADC (MCP3008) pour chaque capteur enregistré
            Lève NotImplementedError si ADC non disponible
        
        Examples:
            reader = SensorReader()
            all_humidity = reader.get_all_humidity()
            for sensor_id, humidity in all_humidity.items():
                print(f"Capteur {sensor_id}: {humidity}%")
        """
        if self.mock_mode:
            # Données mockées (5 capteurs)
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
            raise NotImplementedError(
                "ADC MCP3008 non connecté. "
                "Configurez MOCK_GPIO=1 pour mode test."
            )
    
    def get_average_humidity(self) -> float:
        """
        Retourne la moyenne d'humidité sol (simple mean).
        
        Returns:
            float: Humidité moyenne %
        
        Examples:
            reader = SensorReader()
            avg = reader.get_average_humidity()  # Ex: 69.2
        """
        all_humidity = self.get_all_humidity()
        if not all_humidity:
            return 0.0
        return sum(all_humidity.values()) / len(all_humidity)
    
    def get_humidity_by_sensor(self, sensor_id: int) -> float:
        """
        Retourne humidité pour un capteur spécifique.
        
        Args:
            sensor_id: ID du capteur
        
        Returns:
            float: Humidité % (0.0 si capteur non trouvé)
        
        Examples:
            reader = SensorReader()
            humidity = reader.get_humidity_by_sensor(1)  # 65.5
        """
        all_humidity = self.get_all_humidity()
        return all_humidity.get(sensor_id, 0.0)
