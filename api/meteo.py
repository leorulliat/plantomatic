"""
MeteoAPI — Appel API open-meteo pour température, humidité, pression

Responsabilité : Récupère données météo pour Chambéry via API gratuite open-meteo.
Format léger, pas d'authentification, timeout court.

Usage:
    from api.meteo import MeteoAPI
    
    meteo_api = MeteoAPI()
    data = meteo_api.get_temperature_humidity_pressure()
    print(f"Température: {data['temperature']}°C")
    print(f"Humidité: {data['humidity']}%")
    print(f"Pression: {data['pressure']} hPa")
"""

import requests
from typing import Dict, Union


class MeteoAPI:
    """Accès API open-meteo pour données météo."""
    
    # Coordonnées Chambéry
    LATITUDE = 45.5646
    LONGITUDE = 5.9178
    TIMEOUT = 4  # 4 secondes max
    
    def get_temperature_humidity_pressure(self) -> Dict[str, Union[float, str, bool]]:
        """
        Requête API open-meteo pour température, humidité relative, pression.
        
        Returns:
            dict avec clés:
                - temperature: float (°C) ou "--" si erreur
                - humidity: float (%) ou "--" si erreur
                - pressure: float (hPa) ou "--" si erreur
                - error: bool (True si erreur, False sinon)
        
        Examples:
            meteo_api = MeteoAPI()
            data = meteo_api.get_temperature_humidity_pressure()
            
            if data['error']:
                print(f"Erreur API: {data}")
            else:
                print(f"Température: {data['temperature']}°C")
                print(f"Humidité: {data['humidity']}%")
        """
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={self.LATITUDE}&longitude={self.LONGITUDE}"
                f"&current=temperature_2m,relative_humidity_2m,pressure_msl"
                f"&timezone=Europe/Paris"
            )
            
            response = requests.get(url, timeout=self.TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            current = data.get('current', {})
            
            return {
                "temperature": current.get('temperature_2m', None),
                "humidity": current.get('relative_humidity_2m', None),
                "pressure": current.get('pressure_msl', None),
                "error": False
            }
        
        except requests.Timeout:
            return {
                "temperature": "--",
                "humidity": "--",
                "pressure": "--",
                "error": True
            }
        
        except requests.RequestException as e:
            # Network error, API error, JSON parsing, etc.
            return {
                "temperature": "--",
                "humidity": "--",
                "pressure": "--",
                "error": True
            }
        
        except Exception as e:
            # Unexpected error
            return {
                "temperature": "--",
                "humidity": "--",
                "pressure": "--",
                "error": True
            }


# Backward compatibility
def recuperer_meteo_chambery():
    """Fonction legacy pour compatibilité. À supprimer à terme."""
    meteo_api = MeteoAPI()
    data = meteo_api.get_temperature_humidity_pressure()
    
    if data['error']:
        return {"erreur": True, "temp": "--", "hum": "--"}
    else:
        return {
            "erreur": False,
            "temp": data['temperature'],
            "hum": data['humidity']
        }
