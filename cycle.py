#!/usr/bin/env python3
import sys
import time
from gpiozero import Button, OutputDevice
from api.logger import enregistrer_arrosage_manuel, enregistrer_arrosage_auto

# Configurations des Pins
PIN_CAPTEUR = 27
PIN_RELAIS_2 = 17  # Change la broche ici selon ton câblage réel vers le GT108

def executer_cycle(mode="AUTO", duree=30):
    """
    Exécute un cycle complet d'arrosage sécurisé.
    mode : "AUTO" (pour le cron) ou "MANUEL" (depuis l'interface web)
    """
    # Initialisation sécurisée du relais (ÉTEINT par défaut)
    # active_high=False si ton module relais GT108 s'active sur un état BAS (Low-Level Trigger)
    relais = OutputDevice(PIN_RELAIS_2, active_high=True, initial_value=False)
    capteur_eau = Button(PIN_CAPTEUR, pull_up=True)
    
    # 1. Vérification de sécurité avant de démarrer
    eau_disponible = capteur_eau.is_pressed
    statut_eau = "Correct" if eau_disponible else "VIDE !"
    
    if not eau_disponible:
        # Enregistrement de l'échec critique dans les logs
        if mode == "MANUEL":
            enregistrer_arrosage_manuel("VIDE ! (Annulé)", duree=0)
        else:
            enregistrer_arrosage_auto("VIDE ! (Annulé)", duree=0)
        print("Erreur : Le réservoir est vide, arrosage annulé.")
        return False, "Erreur : Réservoir vide !"

    # 2. Lancement de l'arrosage
    try:
        relais.on() # Active la pompe
        print(f"[{mode}] Pompe activée pour {duree} secondes...")
        time.sleep(duree)
        relais.off() # Coupe la pompe
        
        # 3. Enregistrement du succès
        if mode == "MANUEL":
            enregistrer_arrosage_manuel("Correct", duree)
        else:
            enregistrer_arrosage_auto("Correct", duree)
            
        return True, "Arrosage réussi !"
        
    except Exception as e:
        relais.off() # Sécurité absolue : on coupe en cas de plantage du script
        print(f"Erreur pendant l'arrosage : {e}")
        return False, f"Erreur système : {e}"

if __name__ == "__main__":
    # Si le script est appelé directement en ligne de commande (ex: par le Cron)
    # On peut lui passer des arguments optionnels (ex: python cycle.py AUTO 45)
    type_appel = sys.argv[1] if len(sys.argv) > 1 else "AUTO"
    duree_appel = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    executer_cycle(mode=type_appel, duree=duree_appel)