import os
import time
from datetime import datetime
from pathlib import Path
from api.logger import enregistrer_photo_capture

# Chargement sécurisé de dotenv si disponible
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Détection de picamera2 (uniquement présent sur Raspberry Pi branché à la caméra)
try:
    from picamera2 import Picamera2
    SUR_RASPBERRY = True
except (ImportError, Exception):
    SUR_RASPBERRY = False


def capturer_photo() -> tuple[bool, str]:
    """
    Capture une photo depuis la caméra (Raspberry Pi) ou simule la capture (PC/Windows).
    Utilise la variable d'environnement PHOTO_DIR si définie, sinon retombe sur le
    dossier par défaut du projet (~/plantomatic/photos).
    
    Retourne :
        tuple: (succes: bool, chemin_fichier_ou_erreur: str)
    """
    # 1. Détermination du dossier de stockage (depuis .env ou fallback)
    photo_dir_env = os.getenv("PHOTO_DIR")
    if photo_dir_env:
        output_dir = Path(photo_dir_env)
    else:
        # Fallback par défaut vers le dossier photos du projet
        project_root = Path(__file__).parent.parent
        output_dir = project_root / "photos"
    
    try:
        # Assurer que le dossier existe
        output_dir.mkdir(exist_ok=True, parents=True)
    except Exception as e:
        erreur_msg = f"Impossible de créer le dossier de stockage : {e}"
        enregistrer_photo_capture("", succes=False, erreur=erreur_msg)
        return False, erreur_msg

    # 2. Génération du nom de fichier horodaté
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = output_dir / f"plante_{timestamp}.jpg"

    # 3. Capture réelle ou Mock (Simulation)
    if SUR_RASPBERRY:
        try:
            # Initialisation de Picamera2
            picam2 = Picamera2()
            
            # Configuration rapide 1920x1080
            camera_config = picam2.create_still_configuration(main={"size": (1920, 1080)})
            picam2.configure(camera_config)
            
            # Démarrage
            picam2.start()
            
            # Pause courte (1 sec) pour stabiliser la luminosité (AEC)
            time.sleep(1)
            
            # Capture vers le fichier
            picam2.capture_file(str(file_path))
            
            # Fermeture propre
            picam2.stop()
            picam2.close()
            
            # Enregistrement dans les logs de l'arrosage
            enregistrer_photo_capture(str(file_path), succes=True)
            return True, str(file_path)
            
        except Exception as e:
            erreur_msg = f"Erreur matérielle caméra : {e}"
            enregistrer_photo_capture("", succes=False, erreur=erreur_msg)
            return False, erreur_msg
    else:
        # Simulation PC (Windows / Developpement)
        try:
            # Création d'un mini JPEG 1x1 pixel valide pour éviter les bugs de lecture du navigateur
            mini_jpeg = (
                b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00'
                b'\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19'
                b'\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9'
                b'=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00'
                b'\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03'
                b'\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03'
                b'\x05\x05\x04\x04\x00\x00\x01\x7d\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07'
                b'"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\x16\x00\x17\x18\x19\x1a%&'
                b'\'()*56789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92'
                b'\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4'
                b'\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6'
                b'\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6'
                b'\xf7\xf8\xf9\xfa\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xf7\xfa\x00'
                b'\xff\xd9'
            )
            with open(file_path, "wb") as f:
                f.write(mini_jpeg)
                
            enregistrer_photo_capture(str(file_path), succes=True)
            return True, str(file_path)
        except Exception as e:
            erreur_msg = f"Erreur simulation : {e}"
            enregistrer_photo_capture("", succes=False, erreur=erreur_msg)
            return False, erreur_msg
