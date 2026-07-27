import os
import time
from datetime import datetime
from picamera2 import Picamera2

def capture_photo():
    # 1. Dossier de destination (~/plantomatic/photos)
    output_dir = os.path.expanduser("~/plantomatic/photos")
    os.makedirs(output_dir, exist_ok=True)

    # Nom horodaté
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(output_dir, f"plante_{timestamp}.jpg")

    print("Initialisation de la caméra...")
    # Initialisation de Picamera2
    picam2 = Picamera2()

    # Configuration minimale pour capture photo directe (1920x1080 pour garder une bonne résolution sans surcharger)
    camera_config = picam2.create_still_configuration(main={"size": (1920, 1080)})
    picam2.configure(camera_config)

    # Démarrage rapide
    picam2.start()
    
    # Pause courte (1 sec) pour stabiliser la luminosité/exposition (AEC)
    time.sleep(1)

    # Capture directement vers le fichier
    picam2.capture_file(file_path)
    print(f"✓ Photo sauvegardée : {file_path}")

    # Libération immédiate de la mémoire RAM
    picam2.stop()
    picam2.close()

if __name__ == "__main__":
    try:
        capture_photo()
    except Exception as e:
        print(f"❌ Erreur : {e}")
