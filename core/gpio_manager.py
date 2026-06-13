"""
GPIO Manager — Broker GPIO centralisé (Singleton)

Responsabilité : Gère TOUS les accès GPIO (lecture/écriture) pour éviter les conflits.
Support du mode mock pour tests sans RPi.

Usage:
    from core.gpio_manager import gpio_manager
    
    eau_ok = gpio_manager.read_button(27)
    gpio_manager.write_output(17, True)
    time.sleep(30)
    gpio_manager.write_output(17, False)
"""

import os
import time
from typing import Dict, Optional


class GPIOManager:
    """Singleton broker pour accès GPIO centralisé."""
    
    _instance: Optional['GPIOManager'] = None
    
    def __new__(cls):
        """Implémente le singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialise le manager (une seule fois)."""
        if self._initialized:
            return
        
        self.mode = "MOCK" if os.getenv("MOCK_GPIO") == "1" else "REAL"
        self._buttons: Dict[int, object] = {}  # Cache Button instances
        self._outputs: Dict[int, object] = {}  # Cache OutputDevice instances
        self._button_states: Dict[int, bool] = {}  # Mock states for MOCK mode
        self._output_states: Dict[int, bool] = {}  # Mock states for MOCK mode
        
        if self.mode == "REAL":
            try:
                from gpiozero import Device
                # Use lgpio backend (native RPi)
                Device.pin_factory = None  # Auto-detect available factory
            except ImportError:
                raise ImportError(
                    "gpiozero not installed. Install with: pip install gpiozero"
                )
        
        self._initialized = True
    
    def read_button(self, pin: int, pull_up: bool = True) -> bool:
        """
        Lit l'état d'un bouton/capteur (GPIO comme input).
        
        Args:
            pin: Numéro GPIO (ex: 27 pour capteur eau)
            pull_up: Résistance de tirage (True = pull-up)
        
        Returns:
            bool: True si contact fermé (GND), False si ouvert
        
        Raises:
            RuntimeError: Si l'accès GPIO échoue
        
        Examples:
            eau_presente = gpio_manager.read_button(27)
            if eau_presente:
                print("Réservoir plein")
        """
        if self.mode == "MOCK":
            return self._button_states.get(pin, True)
        
        try:
            if pin not in self._buttons:
                from gpiozero import Button
                self._buttons[pin] = Button(pin, pull_up=pull_up)
            
            button = self._buttons[pin]
            # Button.is_pressed returns True when contact is closed (GND)
            return button.is_pressed
        
        except Exception as e:
            raise RuntimeError(f"Failed to read GPIO {pin}: {str(e)}")
    
    def write_output(
        self, 
        pin: int, 
        state: bool, 
        active_high: bool = True
    ) -> None:
        """
        Écrit un signal sur un GPIO (output).
        
        Args:
            pin: Numéro GPIO (ex: 17 pour relais)
            state: True=ON (3.3V ou 0V selon active_high), False=OFF
            active_high: True si relais s'active sur 3.3V, False si sur 0V
        
        Returns:
            None
        
        Raises:
            RuntimeError: Si l'accès GPIO échoue
        
        Examples:
            gpio_manager.write_output(17, True)   # Active relais
            time.sleep(30)
            gpio_manager.write_output(17, False)  # Coupe relais
        """
        if self.mode == "MOCK":
            self._output_states[pin] = state
            return
        
        try:
            if pin not in self._outputs:
                from gpiozero import OutputDevice
                self._outputs[pin] = OutputDevice(
                    pin, 
                    active_high=active_high,
                    initial_value=False
                )
            
            output = self._outputs[pin]
            if state:
                output.on()
            else:
                output.off()
        
        except Exception as e:
            raise RuntimeError(f"Failed to write GPIO {pin}: {str(e)}")
    
    def cleanup(self) -> None:
        """
        Ferme tous les GPIO proprement.
        Appelé au shutdown Flask via atexit ou teardown.
        
        Returns:
            None
        """
        if self.mode == "REAL":
            try:
                # Coupe tous les outputs (sécurité)
                for output in self._outputs.values():
                    output.off()
                
                # Close all devices
                for button in self._buttons.values():
                    button.close()
                for output in self._outputs.values():
                    output.close()
                
                self._buttons.clear()
                self._outputs.clear()
            except Exception as e:
                print(f"Warning during GPIO cleanup: {e}")
    
    def set_mock_state(self, pin: int, state: bool) -> None:
        """
        (Méthode de test) Configure l'état simulé d'un GPIO en mode MOCK.
        
        Args:
            pin: Numéro GPIO
            state: État simulé
        
        Returns:
            None
        
        Raises:
            RuntimeError: Si pas en mode MOCK
        
        Examples:
            gpio_manager.set_mock_state(27, True)  # Simule eau présente
        """
        if self.mode != "MOCK":
            raise RuntimeError("set_mock_state() only works in MOCK mode")
        self._button_states[pin] = state
    
    def get_mock_state(self, pin: int) -> Optional[bool]:
        """
        (Méthode de test) Récupère l'état simulé d'un GPIO en mode MOCK.
        
        Args:
            pin: Numéro GPIO
        
        Returns:
            bool: État du GPIO
        
        Raises:
            RuntimeError: Si pas en mode MOCK
        """
        if self.mode != "MOCK":
            raise RuntimeError("get_mock_state() only works in MOCK mode")
        return self._button_states.get(pin)


# Singleton global
gpio_manager = GPIOManager()
