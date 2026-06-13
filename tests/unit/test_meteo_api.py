"""
Unit Tests for MeteoAPI (api/meteo.py)

Test Coverage:
- API call success
- Timeout handling
- Network error handling
- Malformed response handling
- Backward compatibility (legacy function)
"""

import pytest
from unittest.mock import patch, MagicMock
import requests
from api.meteo import MeteoAPI, recuperer_meteo_chambery


class TestMeteoAPISuccess:
    """Test successful API calls."""
    
    def test_get_temperature_humidity_pressure_success(self):
        """Test successful API response."""
        mock_response = {
            'current': {
                'temperature_2m': 22.5,
                'relative_humidity_2m': 65,
                'pressure_msl': 1013.25
            }
        }
        
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            
            api = MeteoAPI()
            result = api.get_temperature_humidity_pressure()
            
            assert result['temperature'] == 22.5
            assert result['humidity'] == 65
            assert result['pressure'] == 1013.25
            assert result['error'] is False
    
    def test_api_call_with_correct_url(self):
        """Test API is called with correct URL."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {
                'current': {
                    'temperature_2m': 20.0,
                    'relative_humidity_2m': 60,
                    'pressure_msl': 1010.0
                }
            }
            
            api = MeteoAPI()
            api.get_temperature_humidity_pressure()
            
            # Check URL contains correct coordinates
            call_args = mock_get.call_args[0][0]
            assert '45.5646' in call_args  # Latitude
            assert '5.9178' in call_args   # Longitude
            assert 'current=' in call_args
    
    def test_api_call_with_timeout(self):
        """Test API is called with timeout parameter."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {
                'current': {
                    'temperature_2m': 20.0,
                    'relative_humidity_2m': 60,
                    'pressure_msl': 1010.0
                }
            }
            
            api = MeteoAPI()
            api.get_temperature_humidity_pressure()
            
            # Check timeout
            assert mock_get.call_args[1]['timeout'] == 4


class TestMeteoAPITimeoutHandling:
    """Test timeout handling."""
    
    def test_timeout_returns_dashes(self):
        """Test that timeout returns dashes and error=True."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.Timeout()
            
            api = MeteoAPI()
            result = api.get_temperature_humidity_pressure()
            
            assert result['temperature'] == "--"
            assert result['humidity'] == "--"
            assert result['pressure'] == "--"
            assert result['error'] is True
    
    def test_timeout_is_retryable(self):
        """Test that timeout case can be retried."""
        api = MeteoAPI()
        
        # First call fails
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.Timeout()
            result1 = api.get_temperature_humidity_pressure()
            assert result1['error'] is True
        
        # Second call succeeds
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {
                'current': {
                    'temperature_2m': 22.5,
                    'relative_humidity_2m': 65,
                    'pressure_msl': 1013.25
                }
            }
            result2 = api.get_temperature_humidity_pressure()
            assert result2['error'] is False


class TestMeteoAPIErrorHandling:
    """Test error handling."""
    
    def test_connection_error_returns_dashes(self):
        """Test that connection error returns dashes."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.ConnectionError()
            
            api = MeteoAPI()
            result = api.get_temperature_humidity_pressure()
            
            assert result['temperature'] == "--"
            assert result['error'] is True
    
    def test_http_error_returns_dashes(self):
        """Test that HTTP error returns dashes."""
        with patch('requests.get') as mock_get:
            response = MagicMock()
            response.raise_for_status.side_effect = requests.HTTPError()
            mock_get.return_value = response
            
            api = MeteoAPI()
            result = api.get_temperature_humidity_pressure()
            
            assert result['temperature'] == "--"
            assert result['error'] is True
    
    def test_json_decode_error_returns_dashes(self):
        """Test that JSON decode error returns dashes."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.side_effect = ValueError("Invalid JSON")
            
            api = MeteoAPI()
            result = api.get_temperature_humidity_pressure()
            
            assert result['temperature'] == "--"
            assert result['error'] is True
    
    def test_missing_fields_returns_none(self):
        """Test that missing fields in response return None."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {'current': {}}
            
            api = MeteoAPI()
            result = api.get_temperature_humidity_pressure()
            
            assert result['temperature'] is None
            assert result['humidity'] is None
            assert result['pressure'] is None
            assert result['error'] is False
    
    def test_unexpected_exception_returns_dashes(self):
        """Test that unexpected exceptions return dashes."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = ValueError("Unexpected error")
            
            api = MeteoAPI()
            result = api.get_temperature_humidity_pressure()
            
            assert result['temperature'] == "--"
            assert result['error'] is True


class TestMeteoAPIIntegration:
    """Test integration aspects."""
    
    def test_multiple_calls_independent(self):
        """Test that multiple API calls are independent."""
        api = MeteoAPI()
        
        # First call
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {
                'current': {
                    'temperature_2m': 20.0,
                    'relative_humidity_2m': 60,
                    'pressure_msl': 1010.0
                }
            }
            result1 = api.get_temperature_humidity_pressure()
            assert result1['temperature'] == 20.0
        
        # Second call
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {
                'current': {
                    'temperature_2m': 25.0,
                    'relative_humidity_2m': 70,
                    'pressure_msl': 1015.0
                }
            }
            result2 = api.get_temperature_humidity_pressure()
            assert result2['temperature'] == 25.0


class TestBackwardCompatibility:
    """Test backward compatibility with legacy function."""
    
    def test_recuperer_meteo_chambery_success(self):
        """Test legacy function returns correct format on success."""
        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = {
                'current': {
                    'temperature_2m': 22.5,
                    'relative_humidity_2m': 65,
                    'pressure_msl': 1013.25
                }
            }
            
            result = recuperer_meteo_chambery()
            
            assert result['erreur'] is False
            assert result['temp'] == 22.5
            assert result['hum'] == 65
    
    def test_recuperer_meteo_chambery_error(self):
        """Test legacy function returns error format on failure."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.Timeout()
            
            result = recuperer_meteo_chambery()
            
            assert result['erreur'] is True
            assert result['temp'] == "--"
            assert result['hum'] == "--"
