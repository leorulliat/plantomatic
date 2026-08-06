import os
from datetime import datetime, timezone
from flask import Flask, render_template, jsonify, request, send_from_directory
from api.meteo import recuperer_meteo_chambery
from api.logger import lire_les_logs, enregistrer_check_2h, enregistrer_photo_suppression
from config.settings import get_photo_storage_dir
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


def format_photo_timestamp(value, tz_name=None):
    """Convertit une date de photo vers un format lisible en timezone locale."""
    if not value:
        return "Date inconnue"

    value_str = str(value).strip()
    if not value_str:
        return "Date inconnue"

    if len(value_str) == 10 and value_str.count('/') == 2:
        return value_str

    try:
        if isinstance(value, datetime):
            dt = value
        else:
            normalized = value_str.replace(' ', 'T', 1)
            if normalized.endswith('Z'):
                normalized = normalized[:-1] + '+00:00'
            dt = datetime.fromisoformat(normalized)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                dt = datetime.strptime(value_str, fmt)
                break
            except ValueError:
                continue
        else:
            return value_str

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    if tz_name:
        from zoneinfo import ZoneInfo
        dt = dt.astimezone(ZoneInfo(tz_name))
    else:
        dt = dt.astimezone()

    return dt.strftime("%d/%m/%Y %H:%M:%S")


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
    data = request.get_json(silent=True) or {}
    duree = int(data.get('duration_seconds', 30)) if isinstance(data.get('duration_seconds', 30), (int, float, str)) else 30
    if isinstance(duree, float):
        duree = int(duree)
    duree = max(5, min(45, duree))

    if SUR_RASPBERRY:
        # On importe la fonction du script et on l'exécute en mode MANUEL
        from cycle import executer_cycle
        succes, message = executer_cycle(mode="MANUEL", duree=duree)
        if succes:
            return jsonify({"message": f"L'arrosage de {duree}s s'est terminé avec succès !"})
        else:
            return jsonify({"message": f"Échec : {message}"}), 500
    else:
        # Simulation visuelle si tu testes sur ton PC portable
        from api.logger import enregistrer_arrosage_manuel
        enregistrer_arrosage_manuel("Correct (Simulation PC)", duree)
        return jsonify({"message": f"Simulé avec succès (Hors Raspberry Pi) pour {duree}s !"})

@app.route('/api/camera', methods=['POST'])
def api_camera():
    """Déclenche la prise de photo depuis l'interface web"""
    from api.camera import capturer_photo
    succes, resultat = capturer_photo()
    if succes:
        return jsonify({
            "success": True,
            "message": "Photo capturée avec succès !",
            "photo": resultat
        })
    else:
        return jsonify({
            "success": False,
            "message": f"Échec de la capture : {resultat}"
        }), 500

@app.route('/photos/<path:filename>')
def servir_photo(filename):
    """Sert les photos sauvegardées depuis le dossier photo actif."""
    photo_dir = get_photo_storage_dir()
    return send_from_directory(str(photo_dir), filename)

@app.route('/api/photos', methods=['GET'])
def api_photos():
    """Retourne la liste des photos prises par ordre chronologique inversé"""
    try:
        photos = []
        from core.database import db
        events = db.get_camera_events(limit=100)
        for event in events:
            filename = os.path.basename(event['photo_path'])
            photos.append({
                "filename": filename,
                "created_at": format_photo_timestamp(event['timestamp']),
                "created_at_raw": event['timestamp'],
                "file_size_kb": event['file_size_kb'],
                "temp_celsius": event['temp_celsius'],
                "water_level_ok": bool(event['water_level_ok']) if event['water_level_ok'] is not None else None
            })
        return jsonify({"photos": photos})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/photos/<path:filename>', methods=['DELETE'])
def api_supprimer_photo(filename):
    """Supprime une photo depuis l'interface de visualisation."""
    photo_dir = get_photo_storage_dir()
    try:
        photo_path = (photo_dir / filename).resolve()
        base_dir = photo_dir.resolve()
        if not str(photo_path).startswith(str(base_dir) + os.sep):
            return jsonify({"success": False, "error": "Nom de fichier invalide"}), 400
        if not photo_path.exists() or not photo_path.is_file():
            return jsonify({"success": False, "error": "Fichier introuvable"}), 404

        photo_path.unlink()
        from core.database import db
        db.delete_camera_event(str(photo_path))
        enregistrer_photo_suppression(str(photo_path))
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)