#!/usr/bin/python
# -*- coding:utf-8 -*-
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime
from PIL import Image

# Add the project directory to sys.path to import services
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from services.currency_service import CurrencyService
from services.display_service import DisplayService
from main import CurrencyTicker

class TestCurrencyService(unittest.TestCase):
    """Test the CurrencyService class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.api_key = "test_api_key"
        
        # Mock the freecurrencyapi client
        with patch('services.currency_service.freecurrencyapi.Client') as mock_client_class:
            self.mock_client = Mock()
            mock_client_class.return_value = self.mock_client
            self.currency_service = CurrencyService(self.api_key)
    
    def test_init(self):
        """Test CurrencyService initialization"""
        self.assertEqual(self.currency_service.client, self.mock_client)
    
    @patch('services.currency_service.datetime')
    def test_get_exchange_rates_success(self, mock_datetime):
        """Test successful exchange rate fetching"""
        # Mock datetime
        mock_datetime.now.return_value.strftime.return_value = "12:34:56"
        
        # Mock API response
        mock_response = {
            'data': {
                'USD': 0.2,  # 1 BRL = 0.2 USD, so 1 USD = 5 BRL
                'EUR': 0.18  # 1 BRL = 0.18 EUR, so 1 EUR = 5.5556 BRL
            }
        }
        self.mock_client.latest.return_value = mock_response
        
        result = self.currency_service.get_exchange_rates()
        
        self.assertIsNotNone(result)
        self.assertEqual(result['USD/BRL'], 5.0)
        self.assertAlmostEqual(result['EUR/BRL'], 5.5556, places=4)
        self.assertEqual(result['timestamp'], "12:34:56")
        
        # Verify API was called with correct parameters
        self.mock_client.latest.assert_called_once_with(
            base_currency='BRL', 
            currencies=['USD', 'EUR']
        )
    
    def test_get_usd_brl_eur_brl_rates(self):
        """Test convenience method for USD/BRL and EUR/BRL"""
        with patch.object(self.currency_service, 'get_exchange_rates') as mock_get_rates:
            mock_get_rates.return_value = {'USD/BRL': 5.0, 'EUR/BRL': 5.5}
            
            result = self.currency_service.get_usd_brl_eur_brl_rates()
            
            mock_get_rates.assert_called_once_with(base_currency='BRL', target_currencies=['USD', 'EUR'])
            self.assertEqual(result, {'USD/BRL': 5.0, 'EUR/BRL': 5.5})


class TestDisplayService(unittest.TestCase):
    """Test the DisplayService class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Force simulation mode for testing
        self.display_service = DisplayService(simulation_mode=True)
    
    def test_init_simulation_mode(self):
        """Test DisplayService initialization in simulation mode"""
        self.assertTrue(self.display_service.simulation_mode)
        self.assertEqual(self.display_service.width, 250)
        self.assertEqual(self.display_service.height, 122)
    
    @patch('services.display_service.ImageFont')
    def test_create_currency_display_image_with_data(self, mock_font):
        """Test creating display image with valid data"""
        mock_font.truetype.side_effect = Exception("Font not found")
        mock_font.load_default.return_value = Mock()
        
        rates_data = {
            'USD/BRL': 5.25,
            'EUR/BRL': 5.75,
            'timestamp': '12:30:00'
        }
        
        image = self.display_service.create_currency_display_image(rates_data)
        
        self.assertIsInstance(image, Image.Image)
        self.assertEqual(image.size, (250, 122))  # Expected dimensions
        self.assertEqual(image.mode, '1')  # Monochrome
    
    @patch('services.display_service.Image')
    def test_display_image_simulation(self, mock_image_class):
        """Test displaying image in simulation mode"""
        mock_image = Mock()
        mock_image.save = Mock()
        
        self.display_service.display_image(mock_image, "test.png")
        
        mock_image.save.assert_called_once_with("test.png")


class TestCurrencyTicker(unittest.TestCase):
    """Test the main CurrencyTicker orchestrator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.api_key = "test_api_key"
        
        # Mock the services
        with patch('main.CurrencyService') as mock_currency_service, \
             patch('main.DisplayService') as mock_display_service:
            
            self.mock_currency_service = Mock()
            self.mock_display_service = Mock()
            
            mock_currency_service.return_value = self.mock_currency_service
            mock_display_service.return_value = self.mock_display_service
            
            self.ticker = CurrencyTicker(self.api_key, simulation_mode=True)
    
    def test_init(self):
        """Test CurrencyTicker initialization"""
        self.assertEqual(self.ticker.currency_service, self.mock_currency_service)
        self.assertEqual(self.ticker.display_service, self.mock_display_service)
    
    @patch('time.sleep')
    def test_run_single_iteration(self, mock_sleep):
        """Test a single iteration of the run loop"""
        # Mock the services
        rates_data = {'USD/BRL': 5.25, 'EUR/BRL': 5.75}
        mock_image = Mock()
        
        self.mock_currency_service.get_usd_brl_eur_brl_rates.return_value = rates_data
        self.mock_display_service.create_currency_display_image.return_value = mock_image
        
        # Make sleep raise KeyboardInterrupt to exit the loop after one iteration
        mock_sleep.side_effect = KeyboardInterrupt()
        
        self.ticker.run()
        
        # Verify services were called
        self.mock_display_service.initialize_display.assert_called_once()
        self.mock_currency_service.get_usd_brl_eur_brl_rates.assert_called_once()
        self.mock_display_service.create_currency_display_image.assert_called_once_with(rates_data)
        self.mock_display_service.display_image.assert_called_once_with(mock_image)
        self.mock_display_service.cleanup.assert_called_once()
    
    def test_cleanup(self):
        """Test cleanup method"""
        self.ticker._cleanup()
        self.mock_display_service.cleanup.assert_called_once()

class TestCurrencyTickerIntegration(unittest.TestCase):
    """Integration tests that don't mock the API client"""
    
    @patch('main.DISPLAY_AVAILABLE', False)
    def test_real_api_structure(self):
        """Test that we handle real API response structure correctly"""
        # This test uses a mock but with realistic API response structure
        with patch('main.freecurrencyapi.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            # Realistic API response structure based on freecurrencyapi docs
            realistic_response = {
                'data': {
                    'USD': 0.1875,  # 1 BRL = 0.1875 USD
                    'EUR': 0.1705   # 1 BRL = 0.1705 EUR
                }
            }
            mock_client.latest.return_value = realistic_response
            
            ticker = CurrencyTicker("fake_key")
            
            with patch('main.datetime') as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "15:30:45"
                result = ticker.get_exchange_rates()
            
            self.assertIsNotNone(result)
            # 1/0.1875 = 5.3333
            self.assertAlmostEqual(result['USD/BRL'], 5.3333, places=4)
            # 1/0.1705 = 5.8651  
            self.assertAlmostEqual(result['EUR/BRL'], 5.8651, places=4)
            self.assertEqual(result['timestamp'], "15:30:45")

if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)