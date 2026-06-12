from gpiozero import Button; 
import time; 
c=Button(27, pull_up=True); 
print('Prêt !');
while True:
    print('État branché (is_pressed):', c.is_pressed); 
    time.sleep(0.5)