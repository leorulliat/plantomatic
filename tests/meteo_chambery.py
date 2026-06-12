import requests

def obtenir_meteo_chambery():
    # Coordonnées géographiques de Chambéry
    latitude = 45.5646
    longitude = 5.9178
    
    # URL de l'API Open-Meteo (sans clé nécessaire)
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,relative_humidity_2m"
    
    try:
        # Envoi de la requête à l'API
        reponse = requests.get(url)
        # Conversion de la réponse en dictionnaire Python (JSON)
        donnees = reponse.json()
        
        # Extraction des données actuelles
        meteo_actuelle = donnees['current']
        temperature = meteo_actuelle['temperature_2m']
        humidite = meteo_actuelle['relative_humidity_2m']
        
        # Affichage du résultat
        print("--- MÉTÉO À CHAMBÉRY ---")
        print(f"Température actuelle : {temperature}°C")
        print(f"Humidité de l'air     : {humidite}%")
        print("------------------------")
        
    except Exception as e:
        print(f"Erreur lors de la récupération de la météo : {e}")

if __name__ == "__main__":
    obtenir_meteo_chambery()
