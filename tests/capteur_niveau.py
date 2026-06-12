import time
from gpiozero import Button

# Configuration du GPIO 27 avec résistance de tirage vers le 3.3V (Pull-Up)
# On utilise Button car un capteur de niveau fonctionne mécaniquement comme un bouton.
capteur_eau = Button(27, pull_up=True)

print("--- Début du test du capteur de niveau FLSW3 ---")
print("Faites glisser le flotteur à la main pour simuler le niveau d'eau.")
print("Appuyez sur Ctrl+C pour quitter.\n")

try:
    while True:
        if capteur_eau.is_pressed:
            # is_pressed est VRAI quand le GPIO est relié au GND (contact fermé)
            print("💧 État : Eau présente (Réservoir OK) - Contact FERMÉ")
        else:
            # Le contact est ouvert
            print("⚠️ Alerte : Manque d'eau (Sécurité) - Contact OUVERT")
        
        # Pause de 0.5 seconde pour ne pas surcharger le processeur
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nTest interrompu par l'utilisateur.")