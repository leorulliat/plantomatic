import time
from gpiozero import OutputDevice

# Configuration temporaire pour le test sans fil VCC
relais1 = OutputDevice(17, active_high=True, initial_value=False)

print("--- Test alternatif (2 fils : IN1 + GND) ---")

try:
    while True:
        print("Envoi du signal (ON)")
        relais1.on()  # Envoie 3.3V sur le GPIO 17
        time.sleep(5)
        
        print("Arrêt du signal (OFF)")
        relais1.off() # Repasse à 0V
        time.sleep(1)

except KeyboardInterrupt:
    print("\nTest interrompu.")
finally:
    relais1.close()