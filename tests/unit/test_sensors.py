"""
Unit Tests for SensorReader (api/sensors.py)

Test Coverage:
- Mock mode (MOCK_GPIO=1)
- Real mode error handling
- get_all_humidity()
- get_average_humidity()
- get_humidity_by_sensor()
"""

import pytest
import os
from unittest.mock import patch
from api.sensors import SensorReader


@pytest.fixture
def mock_env():
    """Set MOCK_GPIO=1 for tests."""
    with patch.dict(os.environ, {"MOCK_GPIO": "1"}):
        yield


class TestSensorReaderMockMode:
    """Test SensorReader in MOCK mode."""
    
    def test_mock_mode_detection(self, mock_env):
        """Test that MOCK_GPIO=1 is detected."""
        reader = SensorReader()
        assert reader.mock_mode is True
    
    def test_get_all_humidity_mock(self, mock_env):
        """Test get_all_humidity returns mock data."""
        reader = SensorReader()
        result = reader.get_all_humidity()
        
        assert isinstance(result, dict)
        assert len(result) == 5
        assert all(isinstance(v, float) for v in result.values())
    
    def test_get_all_humidity_values_in_range(self, mock_env):
        """Test mock humidity values are in reasonable range."""
        reader = SensorReader()
        result = reader.get_all_humidity()
        
        for sensor_id, humidity in result.items():
            assert 0 <= humidity <= 100, f"Sensor {sensor_id} has invalid humidity: {humidity}"
    
    def test_get_all_humidity_sensor_ids(self, mock_env):
        """Test mock returns expected sensor IDs."""
        reader = SensorReader()
        result = reader.get_all_humidity()
        
        expected_ids = {1, 2, 3, 4, 5}
        assert set(result.keys()) == expected_ids
    
    def test_get_all_humidity_values_consistent(self, mock_env):
        """Test mock returns consistent values across calls."""
        reader = SensorReader()
        result1 = reader.get_all_humidity()
        result2 = reader.get_all_humidity()
        
        assert result1 == result2


class TestSensorReaderAverageHumidity:
    """Test get_average_humidity() method."""
    
    def test_get_average_humidity_mock(self, mock_env):
        """Test get_average_humidity returns average."""
        reader = SensorReader()
        avg = reader.get_average_humidity()
        
        assert isinstance(avg, float)
        assert 60 <= avg <= 80  # Mock values are in this range
    
    def test_get_average_humidity_calculation(self, mock_env):
        """Test average is correctly calculated."""
        reader = SensorReader()
        all_humidity = reader.get_all_humidity()
        avg = reader.get_average_humidity()
        
        expected_avg = sum(all_humidity.values()) / len(all_humidity)
        assert avg == expected_avg
    
    def test_get_average_humidity_empty(self, mock_env):
        """Test average returns 0.0 when no sensors."""
        reader = SensorReader()
        
        # Mock empty response
        with patch.object(reader, 'get_all_humidity', return_value={}):
            avg = reader.get_average_humidity()
            assert avg == 0.0


class TestSensorReaderBySensor:
    """Test get_humidity_by_sensor() method."""
    
    def test_get_humidity_by_sensor_existing(self, mock_env):
        """Test get humidity for existing sensor."""
        reader = SensorReader()
        humidity = reader.get_humidity_by_sensor(1)
        
        assert isinstance(humidity, float)
        assert 0 <= humidity <= 100
    
    def test_get_humidity_by_sensor_all_sensors(self, mock_env):
        """Test get humidity for all sensors."""
        reader = SensorReader()
        all_humidity = reader.get_all_humidity()
        
        for sensor_id in all_humidity.keys():
            humidity = reader.get_humidity_by_sensor(sensor_id)
            assert humidity == all_humidity[sensor_id]
    
    def test_get_humidity_by_sensor_nonexistent(self, mock_env):
        """Test get humidity for nonexistent sensor returns 0.0."""
        reader = SensorReader()
        humidity = reader.get_humidity_by_sensor(999)
        
        assert humidity == 0.0


class TestSensorReaderRealMode:
    """Test SensorReader in REAL mode (no MOCK_GPIO)."""
    
    def test_real_mode_raises_not_implemented(self):
        """Test real mode raises NotImplementedError."""
        with patch.dict(os.environ, {"MOCK_GPIO": ""}):
            reader = SensorReader()
            
            with pytest.raises(NotImplementedError, match="MCP3008"):
                reader.get_all_humidity()
    
    def test_real_mode_average_also_raises(self):
        """Test average also raises in real mode."""
        with patch.dict(os.environ, {"MOCK_GPIO": ""}):
            reader = SensorReader()
            
            with pytest.raises(NotImplementedError):
                reader.get_average_humidity()


class TestSensorReaderIntegration:
    """Test integration scenarios."""
    
    def test_full_workflow_mock(self, mock_env):
        """Test complete sensor reading workflow."""
        reader = SensorReader()
        
        # Get all sensors
        all_humidity = reader.get_all_humidity()
        assert len(all_humidity) > 0
        
        # Get average
        avg = reader.get_average_humidity()
        assert avg > 0
        
        # Get specific sensor
        first_sensor_id = min(all_humidity.keys())
        specific_humidity = reader.get_humidity_by_sensor(first_sensor_id)
        assert specific_humidity == all_humidity[first_sensor_id]
    
    def test_humidity_consistency(self, mock_env):
        """Test that average equals mean of individual sensors."""
        reader = SensorReader()
        
        all_humidity = reader.get_all_humidity()
        avg = reader.get_average_humidity()
        
        # Average should equal mean of all sensors
        expected_avg = sum(all_humidity.values()) / len(all_humidity)
        assert avg == expected_avg
    
    def test_multiple_instances_independent(self, mock_env):
        """Test that multiple SensorReader instances are independent."""
        reader1 = SensorReader()
        reader2 = SensorReader()
        
        # Should work independently
        result1 = reader1.get_all_humidity()
        result2 = reader2.get_all_humidity()
        
        assert result1 == result2
