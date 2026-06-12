# Projet arrosage - Plantomatic
Système d'arrosage automatique des plantes d'intérieur sur Raspberry PI

### Démarrage
Avant chaque phase de dev, exécuter : 
```bash
source env/bin/activate
```
Pour activer l'env python.
Ou directement l'**alias** : 
```bash
plantomatic
```

## Systemd
```bash
sudo systemctl stop dashboard.service
```
**Pour redémarrer le dashboard (après avoir fait une modification dans le code) :**
```bash
sudo systemctl restart dashboard.service
```
**Pour voir les erreurs de ton code Python en temps réel :**
    
```bash
 sudo journalctl -u dashboard.service -f
 ```
*(Cette commande est magique : elle affiche ce que ton script Python aurait normalement écrit dans le terminal, très pratique pour le débogage à distance).*
