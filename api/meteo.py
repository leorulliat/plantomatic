import requests

LATITUDE = 45.5646
LONGITUDE = 5.9178

def recuperer_meteo_chambery():
    meteo_data = {"erreur": False, "temp": "--", "hum": "--"}
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LATITUDE}&longitude={LONGITUDE}&current=temperature_2m,relative_humidity_2m"
    try:
        reponse = requests.get(url, timeout=4)
        donnees = reponse.json()
        meteo_data["temp"] = donnees['current']['temperature_2m']
        meteo_data["hum"] = donnees['current']['relative_humidity_2m']
    except Exception:
        meteo_data["erreur"] = True
    return meteo_data
