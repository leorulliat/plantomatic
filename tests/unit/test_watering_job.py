"""
Unit Tests for Watering Job (core/jobs/watering.py)

Test Coverage:
- execute_watering() success (AUTO + MANUAL)
- Water empty scenario
- GPIO failures with safety
- Database and logger calls
- run_auto_watering()
- Error handling
"""

import pytest
import time
from unittest.mock import patch, MagicMock, call
from core.jobs.watering import execute_watering, run_auto_watering


class TestWateringSuccess:
    """Test successful watering execution."""
    
    def test_execute_watering_success_manual(self):
        """Test successful manual watering."""
        with patch('core.jobs.watering.gpio_manager') as mock_gpio, \
             patch('core.jobs.watering.db') as mock_db, \
             patch('core.jobs.watering.logger') as mock_logger, \
             patch('core.jobs.watering.time.sleep') as mock_sleep:
            
            mock_gpio.read_button.return_value = True
            
            result = execute_watering(event_type="MANUAL", duration_seconds=30)
            
            assert result['success'] is True
            assert "réussi" in result['message'].lower()
    
    def test_execute_watering_success_auto(self):
        """Test successful auto watering."""
        with patch('core.jobs.watering.gpio_manager') as mock_gpio, \
             patch('core.jobs.watering.db') as mock_db, \
             patch('core.jobs.watering.logger') as mock_logger, \
             patch('core.jobs.watering.time.sleep') as mock_sleep:
            
            mock_gpio.read_button.return_value = True
            
            result = execute_watering(event_type="AUTO", duration_seconds=30)
            
            assert result['success'] is True
            assert "AUTO" in result['message'].lower() or "auto" in result['message'].lower()
    
    def test_execute_watering_activates_gpio(self):
        """Test watering activates GPIO 17."""
        with patch('core.jobs.watering.gpio_manager') as mock_gpio, \
             patch('core.jobs.watering.db') as mock_db, \
             patch('core.jobs.watering.logger') as mock_logger, \
             patch('core.jobs.watering.time.sleep') as mock_sleep:
            
            mock_gpio.read_button.return_value = True
            
            execute_watering(duration_seconds=30)
            
            # Check GPIO was activated
            calls = mock_gpio.write_output.call_args_list
            assert calls[0] == call(17, True)  # Activate
            assert calls[1] == call(17, False)  # Deactivate
    
    def test_execute_watering_sleeps_correct_duration(self):
        """Test watering sleeps for correct duration."""
        with patch('core.jobs.watering.gpio_manager') as mock_gpio, \
             patch('core.jobs.watering.db') as mock_db, \
             patch('core.jobs.watering.logger') as mock_logger, \
             patch('core.jobs.watering.time.sleep') as mock_sleep:
            
            mock_gpio.read_button.return_value = True
            
            execute_watering(duration_seconds=45)
            
            mock_sleep.assert_called_once_with(45)
    
    def test_execute_watering_logs_success(self):
        """Test watering logs success."""
        with patch('core.jobs.watering.gpio_manager') as mock_gpio, \
             patch('core.jobs.watering.db') as mock_db, \
             patch('core.jobs.watering.logger') as mock_logger, \
             patch('core.jobs.watering.time.sleep') as mock_sleep:
            
            mock_gpio.read_button.return_value = True
            
            execute_watering(duration_seconds=30)
            
            # Check log_watering was called with SUCCESS
            mock_logger.log_watering.assert_called_once()
            call_args = mock_logger.log_watering.call_args
            assert call_args[1]['status'] == "SUCCESS"
    
    def test_execute_watering_inserts_in_db(self):
        """Test watering inserts event in DB."""
        with patch('core.jobs.watering.gpio_manager') as mock_gpio, \
             patch('core.jobs.watering.db') as mock_db, \
             patch('core.jobs.watering.logger') as mock_logger, \
             patch('core.jobs.watering.time.sleep') as mock_sleep:
            
            mock_gpio.read_button.return_value = True
            
            execute_watering(event_type="MANUAL", duration_seconds=30)
            
            mock_db.insert_watering_event.assert_called_once()
            call_args = mock_db.insert_watering_event.call_args
            assert call_args[1]['event_type'] == "MANUAL"
            assert call_args[1]['status'] == "SUCCESS"


class TestWateringEmpty:
    """Test water empty scenario."""
    
    def test_execute_watering_water_empty_cancelled(self):
        """Test watering is cancelled if water empty."""
        with patch('core.jobs.watering.gpio_manager') as mock_gpio, \
             patch('core.jobs.watering.db') as mock_db, \
             patch('core.jobs.watering.logger') as mock_logger:
            
            mock_gpio.read_button.return_value = False  # Water empty
            
            result = execute_watering(event_type="MANUAL", duration_seconds=30)
            
            assert result['success'] is False
            assert "Réservoir vide" in result['error']
    
    def test_execute_watering_water_empty_no_gpio_activation(self):
        """Test GPIO is NOT activated if water empty."""
        with patch('core.jobs.watering.gpio_manager') as mock_gpio, \
             patch('core.jobs.watering.db') as mock_db, \
             patch('core.jobs.watering.logger') as mock_logger:
            
            mock_gpio.read_button.return_value = False
            
            execute_watering(duration_seconds=30)
            
            # GPIO should NOT be called for activation
            mock_gpio.write_output.assert_not_called()
    
    def test_execute_watering_water_empty_logs_cancelled(self):
        """Test cancelled watering is logged."""
        with patch('core.jobs.watering.gpio_manager') as mock_gpio, \
             patch('core.jobs.watering.db') as mock_db, \
             patch('core.jobs.watering.logger') as mock_logger:
            
            mock_gpio.read_button.return_value = False
            
            execute_watering()
            
            # Check log_watering was called with CANCELLED
            call_args = mock_logger.log_watering.call_args
            assert call_args[1]['status'] == "CANCELLED"
    
    def test_execute_watering_water_empty_inserts_in_db(self):
        """Test cancelled watering is inserted in DB."""
        with patch('core.jobs.watering.gpio_manager') as mock_gpio, \
             patch('core.jobs.watering.db') as mock_db, \
             patch('core.jobs.watering.logger') as mock_logger:
            
            mock_gpio.read_button.return_value = False
            
            execute_watering()
            
            mock_db.insert_watering_event.assert_called_once()
            call_args = mock_db.insert_watering_event.call_args
            assert call_args[1]['status'] == "CANCELLED"


class TestWateringSafety:
    """Test safety features."""
    
    def test_execute_watering_deactivates_on_error(self):
        """Test GPIO is deactivated even if error occurs."""
        with patch('core.jobs.watering.gpio_manager') as mock_gpio, \
             patch('core.jobs.watering.db') as mock_db, \
             patch('core.jobs.watering.logger') as mock_logger, \
             patch('core.jobs.watering.time.sleep') as mock_sleep:
            
            mock_gpio.read_button.return_value = True
            mock_sleep.side_effect = Exception("Sleep error")  # Error during sleep
            
            result = execute_watering(duration_seconds=30)
            
            # Should return error
            assert result['success'] is False
            
            # BUT GPIO should be deactivated (safety)
            calls = mock_gpio.write_output.call_args_list
            # Should have at least activation and deactivation
            assert any(call[0] == (17, True) for call in calls)
            assert any(call[0] == (17, False) for call in calls)
    
    def test_execute_watering_logs_error(self):
        """Test error is logged."""
        with patch('core.jobs.watering.gpio_manager') as mock_gpio, \
             patch('core.jobs.watering.db') as mock_db, \
             patch('core.jobs.watering.logger') as mock_logger, \
             patch('core.jobs.watering.time.sleep') as mock_sleep:
            
            mock_gpio.read_button.return_value = True
            mock_sleep.side_effect = Exception("Sleep error")
            
            execute_watering()
            
            # Check error was logged
            mock_logger.log_error.assert_called_once()
    
    def test_execute_watering_inserts_failed_event(self):
        """Test failed watering event is inserted in DB."""
        with patch('core.jobs.watering.gpio_manager') as mock_gpio, \
             patch('core.jobs.watering.db') as mock_db, \
             patch('core.jobs.watering.logger') as mock_logger, \
             patch('core.jobs.watering.time.sleep') as mock_sleep:
            
            mock_gpio.read_button.return_value = True
            mock_sleep.side_effect = Exception("Sleep error")
            
            execute_watering()
            
            call_args = mock_db.insert_watering_event.call_args
            assert call_args[1]['status'] == "FAILED"


class TestRunAutoWatering:
    """Test run_auto_watering() function."""
    
    def test_run_auto_watering_calls_execute(self):
        """Test run_auto_watering calls execute_watering."""
        with patch('core.jobs.watering.execute_watering') as mock_execute, \
             patch('core.jobs.watering.logger') as mock_logger:
            
            mock_execute.return_value = {"success": True}
            
            result = run_auto_watering()
            
            mock_execute.assert_called_once_with(event_type="AUTO", duration_seconds=30)
    
    def test_run_auto_watering_returns_execute_result(self):
        """Test run_auto_watering returns execute_watering result."""
        with patch('core.jobs.watering.execute_watering') as mock_execute:
            mock_execute.return_value = {"success": True, "message": "OK"}
            
            result = run_auto_watering()
            
            assert result == {"success": True, "message": "OK"}
    
    def test_run_auto_watering_error_returns_error(self):
        """Test run_auto_watering error handling."""
        with patch('core.jobs.watering.execute_watering') as mock_execute, \
             patch('core.jobs.watering.logger') as mock_logger:
            
            mock_execute.side_effect = Exception("Watering error")
            
            result = run_auto_watering()
            
            assert result['success'] is False
            assert 'error' in result


class TestWateringGPIOEvents:
    """Test GPIO event logging."""
    
    def test_execute_watering_logs_gpio_activation(self):
        """Test GPIO activation is logged."""
        with patch('core.jobs.watering.gpio_manager') as mock_gpio, \
             patch('core.jobs.watering.db') as mock_db, \
             patch('core.jobs.watering.logger') as mock_logger, \
             patch('core.jobs.watering.time.sleep') as mock_sleep:
            
            mock_gpio.read_button.return_value = True
            
            execute_watering()
            
            # Check GPIO events were logged
            log_gpio_calls = [c for c in mock_logger.log_gpio_event.call_args_list]
            assert len(log_gpio_calls) >= 2  # At least 2 (activation + deactivation)
    
    def test_execute_watering_logs_gpio_deactivation(self):
        """Test GPIO deactivation is logged."""
        with patch('core.jobs.watering.gpio_manager') as mock_gpio, \
             patch('core.jobs.watering.db') as mock_db, \
             patch('core.jobs.watering.logger') as mock_logger, \
             patch('core.jobs.watering.time.sleep') as mock_sleep:
            
            mock_gpio.read_button.return_value = True
            
            execute_watering()
            
            # Check deactivation was logged
            log_gpio_calls = mock_logger.log_gpio_event.call_args_list
            deactivation_call = [c for c in log_gpio_calls if c[1].get('value') is False]
            assert len(deactivation_call) > 0
