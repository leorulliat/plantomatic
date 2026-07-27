import os
from flask import Flask, render_template, jsonify, request, send_from_directory
from api.meteo import recuperer_meteo_chambery
from api.logger import lire_les_logs, enregistrer_check_2h
import subprocess # Pour appeler notre script de cycle proprement

# Chargement sécurisé de dotenv si disponible
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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

@app.route('/api/camera', methods=['POST'])
def api_camera():
    """Déclenche la prise de photo depuis l'interface web"""
    from api.camera import capturer_photo
    succes, resultat = capturer_photo()
    if succes:
        nom_fichier = os.path.basename(resultat)
        return jsonify({
            "success": True,
            "message": "Photo capturée avec succès !",
            "filename": nom_fichier
        })
    else:
        return jsonify({
            "success": False,
            "message": f"Échec de la capture : {resultat}"
        }), 500

@app.route('/photos/<path:filename>')
def servir_photo(filename):
    """Sert les photos sauvegardées depuis le dossier PHOTO_DIR"""
    photo_dir = os.getenv("PHOTO_DIR")
    if not photo_dir:
        # Fallback par défaut vers le dossier photos du projet
        project_root = os.path.dirname(os.path.abspath(__file__))
        photo_dir = os.path.join(project_root, "photos")
    return send_from_directory(photo_dir, filename)

@app.route('/api/photos', methods=['GET'])
def api_photos():
    """Retourne la liste des photos prises par ordre chronologique inversé"""
    photo_dir = os.getenv("PHOTO_DIR")
    if not photo_dir:
        # Fallback par défaut vers le dossier photos du projet
        project_root = os.path.dirname(os.path.abspath(__file__))
        photo_dir = os.path.join(project_root, "photos")
        
    if not os.path.exists(photo_dir):
        return jsonify({"photos": []})
        
    try:
        # Lister les fichiers jpg/jpeg
        fichiers = [f for f in os.listdir(photo_dir) if f.lower().endswith(('.jpg', '.jpeg'))]
        # Trier par ordre alphabétique décroissant (équivalent à l'ordre chronologique inversé pour notre horodatage)
        fichiers.sort(reverse=True)
        return jsonify({"photos": fichiers})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)