"""
Unit Tests for Check Job (core/jobs/check.py)

Test Coverage:
- Successful check execution
- API failures (meteo, sensors, GPIO)
- Database recording
- Logger calls
- Error handling
- Return value format
"""

import pytest
from unittest.mock import patch, MagicMock
from core.jobs.check import run_check


@pytest.fixture
def mock_meteo_success():
    """Mock successful meteo API call."""
    return {
        'temperature': 22.5,
        'humidity': 65,
        'pressure': 1013.25,
        'error': False
    }


@pytest.fixture
def mock_sensors():
    """Mock successful sensor reading."""
    return {
        1: 65.5,
        2: 70.2,
        3: 68.1,
        4: 72.8,
        5: 69.4
    }


class TestCheckJobSuccess:
    """Test successful check execution."""
    
    def test_run_check_success(self, mock_meteo_success, mock_sensors):
        """Test successful check returns SUCCESS status."""
        with patch('core.jobs.check.MeteoAPI') as mock_meteo_class, \
             patch('core.jobs.check.SensorReader') as mock_sensor_class, \
             patch('core.jobs.check.gpio_manager') as mock_gpio, \
             patch('core.jobs.check.db') as mock_db, \
             patch('core.jobs.check.logger') as mock_logger:
            
            # Setup mocks
            mock_meteo = MagicMock()
            mock_meteo.get_temperature_humidity_pressure.return_value = mock_meteo_success
            mock_meteo_class.return_value = mock_meteo
            
            mock_sensor = MagicMock()
            mock_sensor.get_all_humidity.return_value = mock_sensors
            mock_sensor.get_average_humidity.return_value = 69.2
            mock_sensor_class.return_value = mock_sensor
            
            mock_gpio.read_button.return_value = True
            
            # Run
            result = run_check()
            
            # Verify
            assert result['status'] == "SUCCESS"
            assert 'data' in result
            assert result['data']['temperature'] == 22.5
            assert result['data']['humidity'] == 65
            assert result['data']['water_ok'] is True
    
    def test_run_check_calls_meteo_api(self, mock_meteo_success, mock_sensors):
        """Test check calls MeteoAPI."""
        with patch('core.jobs.check.MeteoAPI') as mock_meteo_class, \
             patch('core.jobs.check.SensorReader') as mock_sensor_class, \
             patch('core.jobs.check.gpio_manager') as mock_gpio, \
             patch('core.jobs.check.db') as mock_db, \
             patch('core.jobs.check.logger') as mock_logger:
            
            mock_meteo = MagicMock()
            mock_meteo.get_temperature_humidity_pressure.return_value = mock_meteo_success
            mock_meteo_class.return_value = mock_meteo
            
            mock_sensor = MagicMock()
            mock_sensor.get_all_humidity.return_value = mock_sensors
            mock_sensor.get_average_humidity.return_value = 69.2
            mock_sensor_class.return_value = mock_sensor
            
            mock_gpio.read_button.return_value = True
            
            run_check()
            
            # Verify API was called
            mock_meteo.get_temperature_humidity_pressure.assert_called_once()
    
    def test_run_check_reads_sensors(self, mock_meteo_success, mock_sensors):
        """Test check reads all sensors."""
        with patch('core.jobs.check.MeteoAPI') as mock_meteo_class, \
             patch('core.jobs.check.SensorReader') as mock_sensor_class, \
             patch('core.jobs.check.gpio_manager') as mock_gpio, \
             patch('core.jobs.check.db') as mock_db, \
             patch('core.jobs.check.logger') as mock_logger:
            
            mock_meteo = MagicMock()
            mock_meteo.get_temperature_humidity_pressure.return_value = mock_meteo_success
            mock_meteo_class.return_value = mock_meteo
            
            mock_sensor = MagicMock()
            mock_sensor.get_all_humidity.return_value = mock_sensors
            mock_sensor.get_average_humidity.return_value = 69.2
            mock_sensor_class.return_value = mock_sensor
            
            mock_gpio.read_button.return_value = True
            
            run_check()
            
            # Verify sensors were read
            mock_sensor.get_all_humidity.assert_called_once()
            mock_sensor.get_average_humidity.assert_called_once()
    
    def test_run_check_reads_water_level(self, mock_meteo_success, mock_sensors):
        """Test check reads GPIO water level."""
        with patch('core.jobs.check.MeteoAPI') as mock_meteo_class, \
             patch('core.jobs.check.SensorReader') as mock_sensor_class, \
             patch('core.jobs.check.gpio_manager') as mock_gpio, \
             patch('core.jobs.check.db') as mock_db, \
             patch('core.jobs.check.logger') as mock_logger:
            
            mock_meteo = MagicMock()
            mock_meteo.get_temperature_humidity_pressure.return_value = mock_meteo_success
            mock_meteo_class.return_value = mock_meteo
            
            mock_sensor = MagicMock()
            mock_sensor.get_all_humidity.return_value = mock_sensors
            mock_sensor.get_average_humidity.return_value = 69.2
            mock_sensor_class.return_value = mock_sensor
            
            mock_gpio.read_button.return_value = True
            
            run_check()
            
            # Verify GPIO was read (pin 27)
            mock_gpio.read_button.assert_called_once_with(27)
    
    def test_run_check_inserts_reading_in_db(self, mock_meteo_success, mock_sensors):
        """Test check inserts reading in database."""
        with patch('core.jobs.check.MeteoAPI') as mock_meteo_class, \
             patch('core.jobs.check.SensorReader') as mock_sensor_class, \
             patch('core.jobs.check.gpio_manager') as mock_gpio, \
             patch('core.jobs.check.db') as mock_db, \
             patch('core.jobs.check.logger') as mock_logger:
            
            mock_meteo = MagicMock()
            mock_meteo.get_temperature_humidity_pressure.return_value = mock_meteo_success
            mock_meteo_class.return_value = mock_meteo
            
            mock_sensor = MagicMock()
            mock_sensor.get_all_humidity.return_value = mock_sensors
            mock_sensor.get_average_humidity.return_value = 69.2
            mock_sensor_class.return_value = mock_sensor
            
            mock_gpio.read_button.return_value = True
            
            run_check()
            
            # Verify DB insert
            mock_db.insert_reading.assert_called_once_with(
                temp_celsius=22.5,
                humidity_percent=65,
                pressure_hpa=1013.25,
                water_level_ok=True
            )
    
    def test_run_check_inserts_soil_humidity_per_sensor(self, mock_meteo_success, mock_sensors):
        """Test check inserts soil humidity per sensor."""
        with patch('core.jobs.check.MeteoAPI') as mock_meteo_class, \
             patch('core.jobs.check.SensorReader') as mock_sensor_class, \
             patch('core.jobs.check.gpio_manager') as mock_gpio, \
             patch('core.jobs.check.db') as mock_db, \
             patch('core.jobs.check.logger') as mock_logger:
            
            mock_meteo = MagicMock()
            mock_meteo.get_temperature_humidity_pressure.return_value = mock_meteo_success
            mock_meteo_class.return_value = mock_meteo
            
            mock_sensor = MagicMock()
            mock_sensor.get_all_humidity.return_value = mock_sensors
            mock_sensor.get_average_humidity.return_value = 69.2
            mock_sensor_class.return_value = mock_sensor
            
            mock_gpio.read_button.return_value = True
            
            run_check()
            
            # Verify soil humidity inserts
            assert mock_db.insert_soil_humidity.call_count == 5


class TestCheckJobErrorHandling:
    """Test error handling."""
    
    def test_run_check_meteo_error_continues(self, mock_sensors):
        """Test check continues if meteo API fails."""
        with patch('core.jobs.check.MeteoAPI') as mock_meteo_class, \
             patch('core.jobs.check.SensorReader') as mock_sensor_class, \
             patch('core.jobs.check.gpio_manager') as mock_gpio, \
             patch('core.jobs.check.db') as mock_db, \
             patch('core.jobs.check.logger') as mock_logger:
            
            # Meteo API fails
            mock_meteo = MagicMock()
            mock_meteo.get_temperature_humidity_pressure.return_value = {
                'temperature': "--",
                'humidity': "--",
                'pressure': "--",
                'error': True
            }
            mock_meteo_class.return_value = mock_meteo
            
            mock_sensor = MagicMock()
            mock_sensor.get_all_humidity.return_value = mock_sensors
            mock_sensor.get_average_humidity.return_value = 69.2
            mock_sensor_class.return_value = mock_sensor
            
            mock_gpio.read_button.return_value = True
            
            result = run_check()
            
            # Should still succeed (returns SUCCESS even with meteo error)
            assert result['status'] == "SUCCESS"
            assert result['data']['temperature'] is None
            assert mock_db.insert_reading.called
    
    def test_run_check_sensor_error_continues(self, mock_meteo_success):
        """Test check continues if sensor reading fails."""
        with patch('core.jobs.check.MeteoAPI') as mock_meteo_class, \
             patch('core.jobs.check.SensorReader') as mock_sensor_class, \
             patch('core.jobs.check.gpio_manager') as mock_gpio, \
             patch('core.jobs.check.db') as mock_db, \
             patch('core.jobs.check.logger') as mock_logger:
            
            mock_meteo = MagicMock()
            mock_meteo.get_temperature_humidity_pressure.return_value = mock_meteo_success
            mock_meteo_class.return_value = mock_meteo
            
            # Sensor fails
            mock_sensor = MagicMock()
            mock_sensor.get_all_humidity.side_effect = Exception("ADC not available")
            mock_sensor_class.return_value = mock_sensor
            
            mock_gpio.read_button.return_value = True
            
            result = run_check()
            
            # Should still succeed
            assert result['status'] == "SUCCESS"
            assert mock_db.insert_reading.called
    
    def test_run_check_gpio_error_continues(self, mock_meteo_success, mock_sensors):
        """Test check continues if GPIO read fails."""
        with patch('core.jobs.check.MeteoAPI') as mock_meteo_class, \
             patch('core.jobs.check.SensorReader') as mock_sensor_class, \
             patch('core.jobs.check.gpio_manager') as mock_gpio, \
             patch('core.jobs.check.db') as mock_db, \
             patch('core.jobs.check.logger') as mock_logger:
            
            mock_meteo = MagicMock()
            mock_meteo.get_temperature_humidity_pressure.return_value = mock_meteo_success
            mock_meteo_class.return_value = mock_meteo
            
            mock_sensor = MagicMock()
            mock_sensor.get_all_humidity.return_value = mock_sensors
            mock_sensor.get_average_humidity.return_value = 69.2
            mock_sensor_class.return_value = mock_sensor
            
            # GPIO fails
            mock_gpio.read_button.side_effect = Exception("GPIO not available")
            
            result = run_check()
            
            # Should still succeed
            assert result['status'] == "SUCCESS"
            assert mock_db.insert_reading.called
    
    def test_run_check_fatal_error_returns_failed(self, mock_meteo_success, mock_sensors):
        """Test fatal error in DB insert returns FAILED."""
        with patch('core.jobs.check.MeteoAPI') as mock_meteo_class, \
             patch('core.jobs.check.SensorReader') as mock_sensor_class, \
             patch('core.jobs.check.gpio_manager') as mock_gpio, \
             patch('core.jobs.check.db') as mock_db, \
             patch('core.jobs.check.logger') as mock_logger:
            
            mock_meteo = MagicMock()
            mock_meteo.get_temperature_humidity_pressure.return_value = mock_meteo_success
            mock_meteo_class.return_value = mock_meteo
            
            mock_sensor = MagicMock()
            mock_sensor.get_all_humidity.return_value = mock_sensors
            mock_sensor.get_average_humidity.return_value = 69.2
            mock_sensor_class.return_value = mock_sensor
            
            mock_gpio.read_button.return_value = True
            
            # DB insert fails
            mock_db.insert_reading.side_effect = Exception("DB error")
            
            result = run_check()
            
            # Should return FAILED
            assert result['status'] == "FAILED"
            assert 'error' in result


class TestCheckJobLogging:
    """Test logging calls."""
    
    def test_run_check_logs_check(self, mock_meteo_success, mock_sensors):
        """Test check logs the check event."""
        with patch('core.jobs.check.MeteoAPI') as mock_meteo_class, \
             patch('core.jobs.check.SensorReader') as mock_sensor_class, \
             patch('core.jobs.check.gpio_manager') as mock_gpio, \
             patch('core.jobs.check.db') as mock_db, \
             patch('core.jobs.check.logger') as mock_logger:
            
            mock_meteo = MagicMock()
            mock_meteo.get_temperature_humidity_pressure.return_value = mock_meteo_success
            mock_meteo_class.return_value = mock_meteo
            
            mock_sensor = MagicMock()
            mock_sensor.get_all_humidity.return_value = mock_sensors
            mock_sensor.get_average_humidity.return_value = 69.2
            mock_sensor_class.return_value = mock_sensor
            
            mock_gpio.read_button.return_value = True
            
            run_check()
            
            # Verify logger.log_check was called
            mock_logger.log_check.assert_called_once()
