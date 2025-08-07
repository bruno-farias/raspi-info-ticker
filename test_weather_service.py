#!/usr/bin/env python3
import unittest
from unittest.mock import patch, Mock, MagicMock
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(__file__))

from services.weather_service import WeatherService


class TestWeatherService(unittest.TestCase):
    """Test cases for WeatherService"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Reset environment variables
        self.original_env = {}
        self.env_vars = [
            'OPEN_WEATHER_API_KEY',
            'OPEN_WEATHER_CITY', 
            'OPEN_WEATHER_STATE',
            'OPEN_WEATHER_COUNTRY'
        ]
        
        # Store original values
        for var in self.env_vars:
            self.original_env[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
    
    def tearDown(self):
        """Clean up after each test method."""
        # Restore original environment variables
        for var in self.env_vars:
            if self.original_env[var] is not None:
                os.environ[var] = self.original_env[var]
            elif var in os.environ:
                del os.environ[var]
    
    def test_init_missing_config(self):
        """Test WeatherService initialization without configuration"""
        service = WeatherService()
        self.assertFalse(service.configured)
        self.assertIsNone(service.api_key)
        self.assertIsNone(service.city)
    
    def test_init_partial_config(self):
        """Test WeatherService initialization with partial configuration"""
        os.environ['OPEN_WEATHER_API_KEY'] = 'test_key'
        # Missing city
        service = WeatherService()
        self.assertFalse(service.configured)
        self.assertEqual(service.api_key, 'test_key')
        self.assertIsNone(service.city)
    
    def test_init_full_config(self):
        """Test WeatherService initialization with full configuration"""
        os.environ['OPEN_WEATHER_API_KEY'] = 'test_key'
        os.environ['OPEN_WEATHER_CITY'] = 'Vienna'
        os.environ['OPEN_WEATHER_STATE'] = 'Vienna'
        os.environ['OPEN_WEATHER_COUNTRY'] = 'AT'
        
        service = WeatherService()
        self.assertTrue(service.configured)
        self.assertEqual(service.api_key, 'test_key')
        self.assertEqual(service.city, 'Vienna')
        self.assertEqual(service.state, 'Vienna')
        self.assertEqual(service.country, 'AT')
    
    @patch('services.weather_service.cache_service')
    def test_get_weather_data_not_configured(self, mock_cache):
        """Test get_weather_data when service is not configured"""
        service = WeatherService()
        result = service.get_weather_data()
        self.assertIsNone(result)
        mock_cache.get.assert_not_called()
    
    @patch('services.weather_service.cache_service')
    def test_get_weather_data_cached(self, mock_cache):
        """Test get_weather_data returns cached data"""
        os.environ['OPEN_WEATHER_API_KEY'] = 'test_key'
        os.environ['OPEN_WEATHER_CITY'] = 'Vienna'
        
        # Mock cached data
        cached_data = {
            'city': 'Vienna',
            'temperature': 22.5,
            'weather_description': 'Clear Sky',
            'timestamp': '10:30:15'
        }
        mock_cache.get.return_value = cached_data
        
        service = WeatherService()
        result = service.get_weather_data()
        
        # Should return cached data with updated timestamp
        self.assertIsNotNone(result)
        self.assertEqual(result['city'], 'Vienna')
        self.assertEqual(result['temperature'], 22.5)
        self.assertTrue(result['timestamp'].endswith('(cached)'))
        
        mock_cache.get.assert_called_once_with('weather_Vienna_')
    
    @patch('services.weather_service.cache_service')
    @patch('services.weather_service.requests')
    def test_get_weather_data_fresh(self, mock_requests, mock_cache):
        """Test get_weather_data fetches fresh data when not cached"""
        os.environ['OPEN_WEATHER_API_KEY'] = 'test_key'
        os.environ['OPEN_WEATHER_CITY'] = 'Vienna'
        os.environ['OPEN_WEATHER_COUNTRY'] = 'AT'
        
        # Mock no cache
        mock_cache.get.return_value = None
        mock_cache.get_ttl_for_screen.return_value = 300
        
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'name': 'Vienna',
            'sys': {'country': 'AT'},
            'main': {
                'temp': 22.5,
                'feels_like': 24.0,
                'temp_min': 20.0,
                'temp_max': 25.0,
                'humidity': 65,
                'pressure': 1013
            },
            'weather': [{
                'main': 'Clear',
                'description': 'clear sky',
                'icon': '01d'
            }],
            'wind': {
                'speed': 3.5
            }
        }
        mock_requests.get.return_value = mock_response
        
        service = WeatherService()
        
        # Mock datetime.now() for consistent timestamp
        with patch('services.weather_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = '10:30:15'
            result = service.get_weather_data()
        
        # Verify API call
        mock_requests.get.assert_called_once()
        call_args = mock_requests.get.call_args
        self.assertEqual(call_args[0][0], 'https://api.openweathermap.org/data/2.5/weather')
        self.assertEqual(call_args[1]['params']['q'], 'Vienna,AT')
        self.assertEqual(call_args[1]['params']['appid'], 'test_key')
        self.assertEqual(call_args[1]['params']['units'], 'metric')
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result['city'], 'Vienna')
        self.assertEqual(result['country'], 'AT')
        self.assertEqual(result['temperature'], 22.5)
        self.assertEqual(result['weather_description'], 'Clear Sky')
        self.assertEqual(result['weather_icon'], '01d')
        self.assertEqual(result['timestamp'], '10:30:15')
        
        # Verify caching
        mock_cache.set.assert_called_once()
    
    @patch('services.weather_service.cache_service')
    @patch('services.weather_service.requests')
    def test_fetch_weather_api_error(self, mock_requests, mock_cache):
        """Test API error handling"""
        os.environ['OPEN_WEATHER_API_KEY'] = 'test_key'
        os.environ['OPEN_WEATHER_CITY'] = 'Vienna'
        
        mock_cache.get.return_value = None
        
        # Mock requests.exceptions for proper exception handling
        import requests
        mock_requests.exceptions = requests.exceptions
        mock_requests.get.side_effect = requests.exceptions.RequestException('Network error')
        
        service = WeatherService()
        result = service.get_weather_data()
        
        self.assertIsNone(result)
        mock_cache.set.assert_not_called()
    
    def test_process_weather_data(self):
        """Test weather data processing"""
        os.environ['OPEN_WEATHER_API_KEY'] = 'test_key'
        os.environ['OPEN_WEATHER_CITY'] = 'Vienna'
        
        service = WeatherService()
        
        raw_data = {
            'name': 'Vienna',
            'sys': {'country': 'AT'},
            'main': {
                'temp': 22.7,
                'feels_like': 24.3,
                'temp_min': 20.1,
                'temp_max': 25.8,
                'humidity': 65,
                'pressure': 1013
            },
            'weather': [{
                'main': 'Rain',
                'description': 'light rain',
                'icon': '10d'
            }],
            'wind': {
                'speed': 3.7
            }
        }
        
        with patch('services.weather_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = '15:45:30'
            result = service._process_weather_data(raw_data)
        
        expected = {
            'city': 'Vienna',
            'country': 'AT',
            'temperature': 22.7,
            'feels_like': 24.3,
            'temp_min': 20.1,
            'temp_max': 25.8,
            'weather_main': 'Rain',
            'weather_description': 'Light Rain',
            'weather_icon': '10d',
            'humidity': 65,
            'pressure': 1013,
            'wind_speed': 3.7,
            'timestamp': '15:45:30',
            'source': 'OpenWeatherMap'
        }
        
        self.assertEqual(result, expected)
    
    def test_get_weather_icon_filename(self):
        """Test weather icon filename mapping"""
        service = WeatherService()
        
        # Test various weather conditions
        test_cases = [
            # Clear sky
            ({'weather_icon': '01d'}, '01d@2x.svg'),
            ({'weather_icon': '01n'}, '01n@2x.svg'),
            
            # Clouds
            ({'weather_icon': '02d'}, '02d@2x.svg'),
            ({'weather_icon': '03d'}, '03d@2x.svg'),
            ({'weather_icon': '04d'}, '04d@2x.svg'),
            
            # Rain
            ({'weather_icon': '09d'}, '09d@2x.svg'),
            ({'weather_icon': '10d'}, '10d@2x.svg'),
            ({'weather_icon': '10n'}, '10n@2x.svg'),
            
            # Special conditions
            ({'weather_icon': '11d'}, '11d@2x.svg'),
            ({'weather_icon': '13d'}, '13d@2x.svg'),
            ({'weather_icon': '50d'}, '50d@2x.svg'),
            
            # Unknown/default - should fallback to sunny day
            ({'weather_icon': 'unknown'}, '01d@2x.svg'),
        ]
        
        for weather_data, expected_filename in test_cases:
            with self.subTest(weather_data=weather_data):
                result = service.get_weather_icon_filename(weather_data)
                self.assertEqual(result, expected_filename)
    
    def test_get_weather_icon_filename_no_data(self):
        """Test weather icon filename with no data"""
        service = WeatherService()
        result = service.get_weather_icon_filename(None)
        self.assertIsNone(result)
        
        # Empty dict should return None due to falsy check
        result = service.get_weather_icon_filename({})
        self.assertIsNone(result)
        
        # Dict with missing weather_icon should use default '01d' -> '01d@2x.svg'
        result = service.get_weather_icon_filename({'temperature': 25})
        self.assertEqual(result, '01d@2x.svg')
    
    def test_location_string_building(self):
        """Test different location configurations"""
        test_cases = [
            # City only
            ({'city': 'Vienna'}, 'Vienna'),
            # City and country
            ({'city': 'Vienna', 'country': 'AT'}, 'Vienna,AT'),
            # City, state, and country
            ({'city': 'Vienna', 'state': 'Vienna', 'country': 'AT'}, 'Vienna,Vienna,AT'),
        ]
        
        for i, (env_config, expected_location) in enumerate(test_cases, 1):
            with self.subTest(test_case=i):
                # Clear environment
                for var in self.env_vars:
                    if var in os.environ:
                        del os.environ[var]
                
                # Set test configuration
                os.environ['OPEN_WEATHER_API_KEY'] = 'test_key'
                for key, value in env_config.items():
                    env_var = f'OPEN_WEATHER_{key.upper()}'
                    os.environ[env_var] = value
                
                service = WeatherService()
                
                with patch('services.weather_service.requests') as mock_requests:
                    mock_response = Mock()
                    mock_response.json.return_value = {'main': {}, 'weather': [{}], 'wind': {}}
                    mock_requests.get.return_value = mock_response
                    
                    service._fetch_weather_from_api()
                    
                    # Check the location parameter in the API call
                    call_args = mock_requests.get.call_args
                    actual_location = call_args[1]['params']['q']
                    self.assertEqual(actual_location, expected_location)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)