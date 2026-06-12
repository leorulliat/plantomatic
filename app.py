from flask import Flask, render_template, jsonify, request
from api.meteo import recuperer_meteo_chambery
from api.logger import lire_les_logs, enregistrer_check_2h
import subprocess # Pour appeler notre script de cycle proprement

try:
    from gpiozero import Button
    SUR_RASPBERRY = True
except (ImportError, Exception):
    SUR_RASPBERRY = False

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    eau_presente = True
    
    if SUR_RASPBERRY:
        # On ouvre la connexion à la broche au moment T
        # On utilise exactement les mêmes paramètres que ton script de test qui fonctionne
        capteur_eau = Button(27, pull_up=True)
        
        # On lit la valeur en direct
        # Si ton script de test inversait la logique, remets le "not" devant si besoin
        eau_presente = capteur_eau.is_pressed
        
        # On ferme proprement la connexion pour libérer la broche immédiatement
        capteur_eau.close()
    
    meteo = recuperer_meteo_chambery()
    return jsonify({"niveau": {"eau_presente": eau_presente}, "meteo": meteo})

@app.route('/api/logs')
def api_logs():
    logs = lire_les_logs(nb_lignes=20)
    return jsonify({"logs": logs})

@app.route('/api/arroser', methods=['POST'])
def api_arroser():
    """Route déclenchée au clic sur le bouton du smartphone"""
    eau_presente = capteur_eau.is_pressed if SUR_RASPBERRY else True
    if SUR_RASPBERRY:
        # On importe la fonction du script et on l'exécute en mode MANUEL
        from cycle import executer_cycle
        succes, message = executer_cycle(mode="MANUEL", duree=30)
        if succes:
            return jsonify({"message": "L'arrosage de 30s s'est terminé avec succès !"})
        else:
            return jsonify({"message": f"Échec : {message}"}), 500
    else:
        # Simulation visuelle si tu testes sur ton PC portable
        from api.logger import enregistrer_arrosage_manuel
        enregistrer_arrosage_manuel("Correct (Simulation PC)", 30)
        return jsonify({"message": "Simulé avec succès (Hors Raspberry Pi) !"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)