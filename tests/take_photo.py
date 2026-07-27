import sys
from pathlib import Path

# Ajouter le dossier parent (racine du projet) au chemin de recherche Python
# Cela permet d'importer 'api.camera' quel que soit l'endroit d'où le script est exécuté.
sys.path.append(str(Path(__file__).parent.parent))

try:
    from api.camera import capturer_photo
except ImportError as e:
    print(f"❌ Erreur d'import : {e}")
    sys.exit(1)

if __name__ == "__main__":
    print("Déclenchement de la capture...")
    succes, resultat = capturer_photo()
    
    if succes:
        print(f"✓ Capture réussie ! Photo sauvegardée : {resultat}")
    else:
        print(f"❌ Échec de la capture : {resultat}")
