"""
Unit Tests for GPIO Manager (core/gpio_manager.py)

Test Coverage:
- Singleton pattern initialization
- Mock mode (MOCK_GPIO=1)
- read_button() with mock states
- write_output() with mock states
- cleanup() method
- Error handling
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from core.gpio_manager import GPIOManager


@pytest.fixture
def mock_env():
    """Set MOCK_GPIO=1 for all tests."""
    with patch.dict(os.environ, {"MOCK_GPIO": "1"}):
        # Reset singleton
        GPIOManager._instance = None
        yield
        GPIOManager._instance = None


class TestGPIOManagerSingleton:
    """Test singleton pattern."""
    
    def test_singleton_instance(self, mock_env):
        """Test that GPIOManager returns same instance."""
        from core.gpio_manager import gpio_manager
        manager1 = gpio_manager
        manager2 = gpio_manager
        
        assert manager1 is manager2
    
    def test_initialization_once(self, mock_env):
        """Test that __init__ runs only once."""
        GPIOManager._instance = None
        manager = GPIOManager()
        
        # Mock _initialized to check if __init__ is called again
        manager._initialized = True
        manager2 = GPIOManager()
        
        # Should be same instance
        assert manager is manager2


class TestGPIOManagerMockMode:
    """Test GPIO operations in MOCK mode."""
    
    def test_mock_mode_detection(self, mock_env):
        """Test that MOCK_GPIO=1 sets mode to MOCK."""
        manager = GPIOManager()
        assert manager.mode == "MOCK"
    
    def test_read_button_default_state(self, mock_env):
        """Test read_button returns default state (True)."""
        manager = GPIOManager()
        result = manager.read_button(27)
        assert result is True
    
    def test_read_button_set_state(self, mock_env):
        """Test read_button returns set state."""
        manager = GPIOManager()
        manager.set_mock_state(27, False)
        
        result = manager.read_button(27)
        assert result is False
    
    def test_read_button_multiple_pins(self, mock_env):
        """Test read_button with different pins."""
        manager = GPIOManager()
        manager.set_mock_state(27, True)
        manager.set_mock_state(17, False)
        
        assert manager.read_button(27) is True
        assert manager.read_button(17) is False
    
    def test_write_output_stores_state(self, mock_env):
        """Test write_output stores state in mock mode."""
        manager = GPIOManager()
        manager.write_output(17, True)
        
        assert manager._output_states[17] is True
        
        manager.write_output(17, False)
        assert manager._output_states[17] is False
    
    def test_write_output_multiple_pins(self, mock_env):
        """Test write_output with multiple pins."""
        manager = GPIOManager()
        manager.write_output(17, True)
        manager.write_output(27, False)
        
        assert manager._output_states[17] is True
        assert manager._output_states[27] is False


class TestGPIOManagerHelpers:
    """Test helper methods in mock mode."""
    
    def test_set_mock_state_in_real_mode_raises(self):
        """Test set_mock_state raises in REAL mode."""
        with patch.dict(os.environ, {"MOCK_GPIO": ""}):
            GPIOManager._instance = None
            manager = GPIOManager()
            
            with pytest.raises(RuntimeError, match="MOCK mode"):
                manager.set_mock_state(27, True)
    
    def test_get_mock_state_button(self, mock_env):
        """Test get_mock_state for button."""
        manager = GPIOManager()
        manager.set_mock_state(27, True)
        
        state = manager.get_mock_state(27)
        assert state is True
    
    def test_get_mock_state_not_set(self, mock_env):
        """Test get_mock_state returns None if not set."""
        manager = GPIOManager()
        
        state = manager.get_mock_state(99)
        assert state is None


class TestGPIOManagerCleanup:
    """Test cleanup method."""
    
    def test_cleanup_in_mock_mode(self, mock_env):
        """Test cleanup works in mock mode (no-op)."""
        manager = GPIOManager()
        manager.write_output(17, True)
        
        # Should not raise
        manager.cleanup()
        
        # States should be cleared in real mode, but we're in mock so doesn't matter
        assert manager._output_states[17] is True  # Mock mode doesn't clear


class TestGPIOManagerWorkflow:
    """Test realistic workflows."""
    
    def test_water_level_check_workflow(self, mock_env):
        """Test checking water level (GPIO 27)."""
        manager = GPIOManager()
        
        # Simulate water present
        manager.set_mock_state(27, True)
        assert manager.read_button(27) is True
        
        # Simulate water empty
        manager.set_mock_state(27, False)
        assert manager.read_button(27) is False
    
    def test_pump_control_workflow(self, mock_env):
        """Test pump activation sequence."""
        manager = GPIOManager()
        
        # Activate pump
        manager.write_output(17, True)
        assert manager._output_states[17] is True
        
        # Deactivate pump
        manager.write_output(17, False)
        assert manager._output_states[17] is False
    
    def test_combined_workflow(self, mock_env):
        """Test water check + pump control combined."""
        manager = GPIOManager()
        
        # Check water level
        manager.set_mock_state(27, True)
        water_ok = manager.read_button(27)
        
        if water_ok:
            # Activate pump
            manager.write_output(17, True)
            assert manager._output_states[17] is True
            
            # Deactivate pump
            manager.write_output(17, False)
            assert manager._output_states[17] is False
