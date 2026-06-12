import logging
import os

LOG_FILE = "arrosage.log"

# 1. Configuration de NOTRE système de logs pour l'arrosage
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)

# 2. LIGNES MAGIQUES : On force Flask (werkzeug) à n'écrire dans notre fichier qu'en cas d'ERREUR majeure.
# Cela va instantanément bloquer les lignes "GET /api/status..."
log_flask = logging.getLogger('werkzeug')
log_flask.setLevel(logging.ERROR)


def enregistrer_check_2h(temperature, humidite, eau_presente):
    """Contrôle automatique toutes les 2h"""
    statut_eau = "Correct" if eau_presente else "VIDE !"
    logging.info(f"[CHECK] Météo: {temperature}°C ({humidite}%) | Réservoir: {statut_eau}")

def enregistrer_arrosage_manuel(statut_eau, duree=30):
    """Déclenchement manuel depuis le smartphone"""
    logging.info(f"[MANUEL] Relais activé pendant {duree}s | Eau au départ: {statut_eau}")

def enregistrer_arrosage_auto(statut_eau, duree=30):
    """Arrosage automatique planifié"""
    logging.info(f"[AUTO] Planification exécutée ({duree}s) | Eau au départ: {statut_eau}")

def lire_les_logs(nb_lignes=20):
    if not os.path.exists(LOG_FILE):
        return ["Aucun historique disponible."]
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lignes = f.readlines()
        
        # Filtrage de sécurité : si de vieux logs de Flask traînent encore dans le fichier,
        # on les ignore à l'affichage pour garder l'interface propre.
        lignes_nettoyees = [l.strip() for l in lignes if "GET /" not in l and "POST /" not in l]
        
        dernieres_lignes = lignes_nettoyees[-nb_lignes:]
        dernieres_lignes.reverse()
        return dernieres_lignes