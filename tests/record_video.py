import os
import time
from datetime import datetime
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder

def capture_video(duration_seconds=5):
    """
    Enregistre une vidéo d'une durée spécifiée en secondes.
    """
    # 1. Dossier de destination (~/plantomatic/videos)
    output_dir = os.path.expanduser("~/plantomatic/videos")
    os.makedirs(output_dir, exist_ok=True)

    # Nom horodaté du fichier (.h264)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(output_dir, f"plante_{timestamp}.h264")

    print("Initialisation de la caméra...")
    picam2 = Picamera2()

    # Configuration optimisée pour l'enregistrement vidéo (720p)
    video_config = picam2.create_video_configuration(main={"size": (1280, 720)})
    picam2.configure(video_config)

    # Démarrage de l'enregistrement avec l'encodeur H264
    print(f"Enregistrement en cours pour {duration_seconds} secondes : {file_path}")
    picam2.start_recording(H264Encoder(), file_path)

    # Attente pendant la durée de la vidéo
    time.sleep(duration_seconds)

    # Arrêt de l'enregistrement et libération des ressources
    print("Fin de l'enregistrement...")
    picam2.stop_recording()
    picam2.close()

    print(f"✓ Vidéo sauvegardée dans : {file_path}")
    return file_path

if __name__ == "__main__":
    try:
        capture_video(duration_seconds=5)
    except Exception as e:
        print(f"❌ Erreur lors de la capture vidéo : {e}")