#!/usr/bin/env python3
import unittest
from unittest.mock import patch, Mock, MagicMock
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(__file__))

from config.display_config import DisplayConfig
from services.weather_service import WeatherService


class TestWeatherDisplay(unittest.TestCase):
    """Test cases for weather display functionality"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Mock currency service
        self.mock_currency_service = Mock()
        
        # Set up environment for weather service
        os.environ['OPEN_WEATHER_API_KEY'] = 'test_key'
        os.environ['OPEN_WEATHER_CITY'] = 'Vienna'
        os.environ['OPEN_WEATHER_COUNTRY'] = 'AT'
    
    def tearDown(self):
        """Clean up after each test method."""
        # Clean up environment variables
        env_vars = ['OPEN_WEATHER_API_KEY', 'OPEN_WEATHER_CITY', 'OPEN_WEATHER_COUNTRY']
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]
    
    def test_weather_screen_available(self):
        """Test that weather screen is available in DisplayConfig"""
        config = DisplayConfig(self.mock_currency_service)
        
        self.assertIn('weather', config.available_screens)
        title, data_func, display_func = config.available_screens['weather']
        self.assertEqual(title, 'Weather')
    
    @patch('services.weather_service.cache_service')
    def test_get_weather_data_integration(self, mock_cache):
        """Test weather data integration in DisplayConfig"""
        # Mock weather data
        weather_data = {
            'city': 'Vienna',
            'temperature': 22.5,
            'weather_description': 'Clear Sky',
            'weather_icon': '01d',
            'timestamp': '10:30:15'
        }
        mock_cache.get.return_value = weather_data
        
        config = DisplayConfig(self.mock_currency_service)
        result = config._get_weather_data()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['city'], 'Vienna')
        self.assertEqual(result['temperature'], 22.5)
        self.assertTrue(result['timestamp'].endswith('(cached)'))
    
    def test_display_weather_data(self):
        """Test weather data display formatting with improved layout"""
        config = DisplayConfig(self.mock_currency_service)
        
        weather_data = {
            'city': 'Vienna',
            'temperature': 22.5,
            'weather_description': 'Clear Sky',
            'weather_icon': '01d',
            'temp_min': 18.0,
            'temp_max': 25.0,
            'humidity': 65,
            'wind_speed': 3.2,
            'timestamp': '10:30:15'
        }
        
        result = config._display_weather_data(weather_data)
        
        # Should return dict with left_lines and right_details
        self.assertIsInstance(result, dict)
        self.assertIn('left_lines', result)
        self.assertIn('right_details', result)
        
        # Check left side content (main info)
        left_lines = result['left_lines']
        self.assertEqual(len(left_lines), 2)
        self.assertEqual(left_lines[0], 'Vienna: 22.5°C')
        self.assertEqual(left_lines[1], 'Clear Sky')
        
        # Check right side content (details)
        right_details = result['right_details']
        self.assertEqual(len(right_details), 3)
        self.assertEqual(right_details[0], 'Range: 18.0°C - 25.0°C')
        self.assertEqual(right_details[1], 'Humidity: 65%')
        self.assertEqual(right_details[2], 'Wind: 3.2m/s')
    
    def test_display_weather_data_no_data(self):
        """Test weather data display with no data"""
        config = DisplayConfig(self.mock_currency_service)
        
        result = config._display_weather_data(None)
        
        # Should return dict format even for no data
        self.assertIsInstance(result, dict)
        self.assertEqual(result['left_lines'], ['Failed to fetch weather'])
        self.assertEqual(result['right_details'], [])
    
    def test_display_weather_data_missing_fields(self):
        """Test weather data display with missing fields"""
        config = DisplayConfig(self.mock_currency_service)
        
        weather_data = {
            'temperature': 22.5,
            # Missing other fields - should default to 0 or 'Unknown'
        }
        
        result = config._display_weather_data(weather_data)
        
        # Should return dict format
        self.assertIsInstance(result, dict)
        
        # Check left side content (main info)
        left_lines = result['left_lines']
        self.assertEqual(len(left_lines), 2)
        self.assertEqual(left_lines[0], 'Unknown: 22.5°C')
        self.assertEqual(left_lines[1], 'Unknown')
        
        # Check right side content (details)
        right_details = result['right_details']
        self.assertEqual(len(right_details), 3)
        self.assertEqual(right_details[0], 'Range: 0°C - 0°C')
        self.assertEqual(right_details[1], 'Humidity: 0%')
        self.assertEqual(right_details[2], 'Wind: 0m/s')
    
    @patch('services.weather_service.cache_service')
    @patch.dict(os.environ, {'SCREEN_ORDER': 'weather'})
    def test_weather_screen_data_structure(self, mock_cache):
        """Test complete weather screen data structure"""
        # Mock weather data
        weather_data = {
            'city': 'Vienna',
            'temperature': 22.5,
            'weather_description': 'Clear Sky',
            'weather_icon': '01d',
            'timestamp': '10:30:15'
        }
        mock_cache.get.return_value = weather_data
        
        config = DisplayConfig(self.mock_currency_service)
        
        # Set current screen to weather (index 0 in this test)
        config.current_screen = 0
        screen_data = config.get_current_screen_data()
        
        self.assertIsNotNone(screen_data)
        self.assertEqual(screen_data['title'], 'Weather')
        self.assertTrue(screen_data['show_logo'])
        self.assertEqual(screen_data['logo_type'], 'weather')
        self.assertEqual(screen_data['weather_icon_filename'], '01d@2x.svg')
        self.assertIn('rates_data', screen_data)
    
    def test_weather_icon_mapping_integration(self):
        """Test weather icon mapping integration"""
        config = DisplayConfig(self.mock_currency_service)
        
        # Test different weather conditions
        test_cases = [
            ({'weather_icon': '01d'}, '01d@2x.svg'),
            ({'weather_icon': '10d'}, '10d@2x.svg'),
            ({'weather_icon': '11d'}, '11d@2x.svg'),
            ({'weather_icon': '13d'}, '13d@2x.svg'),
        ]
        
        for weather_data, expected_icon in test_cases:
            with self.subTest(weather_icon=weather_data['weather_icon']):
                filename = config.weather_service.get_weather_icon_filename(weather_data)
                self.assertEqual(filename, expected_icon)
    
    @patch.dict(os.environ, {'SCREEN_ORDER': 'weather,bitcoin_prices'})
    def test_weather_first_in_order(self):
        """Test weather screen first in custom order"""
        config = DisplayConfig(self.mock_currency_service)
        
        # Weather should be first screen (index 0)
        self.assertEqual(len(config.screens), 2)
        title, _, _ = config.screens[0]
        self.assertEqual(title, 'Weather')
    
    @patch.dict(os.environ, {'SCREEN_ORDER': 'bitcoin_prices,exchange_rates,weather'})
    def test_weather_last_in_order(self):
        """Test weather screen last in custom order"""
        config = DisplayConfig(self.mock_currency_service)
        
        # Weather should be last screen
        self.assertEqual(len(config.screens), 3)
        title, _, _ = config.screens[2]
        self.assertEqual(title, 'Weather')
    
    def test_weather_screen_cycling(self):
        """Test weather screen in cycling system"""
        with patch.dict(os.environ, {'SCREEN_ORDER': 'bitcoin_prices,weather'}):
            config = DisplayConfig(self.mock_currency_service)
            
            # Start at bitcoin (index 0)
            self.assertEqual(config.current_screen, 0)
            
            # Move to weather (index 1)
            config.next_screen()
            self.assertEqual(config.current_screen, 1)
            
            # Cycle back to bitcoin (index 0)
            config.next_screen()
            self.assertEqual(config.current_screen, 0)
    
    def test_weather_service_configuration_check(self):
        """Test weather service configuration in DisplayConfig"""
        config = DisplayConfig(self.mock_currency_service)
        
        # Should have weather service initialized
        self.assertIsNotNone(config.weather_service)
        self.assertIsInstance(config.weather_service, WeatherService)
        self.assertTrue(config.weather_service.configured)
    
    @patch('services.weather_service.cache_service')
    def test_weather_caching_integration(self, mock_cache):
        """Test weather data caching integration"""
        # Test cache miss then cache hit
        mock_cache.get.side_effect = [None, {'temperature': 25.0, 'timestamp': '12:00:00'}]
        mock_cache.get_ttl_for_screen.return_value = 300
        
        config = DisplayConfig(self.mock_currency_service)
        
        # First call should try cache (miss) and attempt API call
        with patch.object(config.weather_service, '_fetch_weather_from_api', return_value=None):
            result1 = config._get_weather_data()
            self.assertIsNone(result1)
        
        # Second call should use cache (hit)
        result2 = config._get_weather_data()
        self.assertIsNotNone(result2)
        self.assertTrue(result2['timestamp'].endswith('(cached)'))


class TestWeatherServiceEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions for weather functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.original_env = {}
        for var in ['OPEN_WEATHER_API_KEY', 'OPEN_WEATHER_CITY']:
            self.original_env[var] = os.environ.get(var)
    
    def tearDown(self):
        """Clean up test fixtures"""
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]
    
    def test_malformed_api_response(self):
        """Test handling of malformed API responses"""
        os.environ['OPEN_WEATHER_API_KEY'] = 'test_key'
        os.environ['OPEN_WEATHER_CITY'] = 'Vienna'
        
        service = WeatherService()
        
        # Test with missing required fields
        malformed_responses = [
            {},  # Empty response
            {'main': {}},  # Missing weather array
            {'weather': []},  # Empty weather array
            {'main': {'temp': 'invalid'}},  # Invalid temperature type
        ]
        
        for response in malformed_responses:
            with self.subTest(response=response):
                result = service._process_weather_data(response)
                # Should handle gracefully and return valid structure
                if result:
                    self.assertIsInstance(result, dict)
                    self.assertIn('temperature', result)
    
    def test_network_timeout(self):
        """Test network timeout handling"""
        os.environ['OPEN_WEATHER_API_KEY'] = 'test_key'
        os.environ['OPEN_WEATHER_CITY'] = 'Vienna'
        
        service = WeatherService()
        
        with patch('services.weather_service.requests') as mock_requests:
            import requests
            mock_requests.exceptions = requests.exceptions
            mock_requests.get.side_effect = requests.exceptions.Timeout('Timeout')
            
            result = service._fetch_weather_from_api()
            self.assertIsNone(result)
    
    def test_api_rate_limiting(self):
        """Test API rate limiting response"""
        os.environ['OPEN_WEATHER_API_KEY'] = 'test_key'
        os.environ['OPEN_WEATHER_CITY'] = 'Vienna'
        
        service = WeatherService()
        
        with patch('services.weather_service.requests') as mock_requests:
            import requests
            mock_requests.exceptions = requests.exceptions
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError('429 Too Many Requests')
            mock_requests.get.return_value = mock_response
            
            result = service._fetch_weather_from_api()
            self.assertIsNone(result)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)