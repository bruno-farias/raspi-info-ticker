#!/usr/bin/python
# -*- coding:utf-8 -*-
import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the project directory to sys.path to import services
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from services.currency_service import CurrencyService
from services.display_service import DisplayService

class TestCurrencyServiceIntegration(unittest.TestCase):
    """Integration tests for CurrencyService with more realistic scenarios"""
    
    def test_error_handling_no_data(self):
        """Test handling when API returns no data"""
        with patch('services.currency_service.freecurrencyapi.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.latest.return_value = {}  # No 'data' key
            
            currency_service = CurrencyService("test_key")
            result = currency_service.get_exchange_rates()
            
            self.assertIsNone(result)
    
    def test_error_handling_api_exception(self):
        """Test handling when API raises exception"""
        with patch('services.currency_service.freecurrencyapi.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.latest.side_effect = Exception("Network error")
            
            currency_service = CurrencyService("test_key")
            result = currency_service.get_exchange_rates()
            
            self.assertIsNone(result)
    
    def test_custom_currencies(self):
        """Test fetching custom currency pairs"""
        with patch('services.currency_service.freecurrencyapi.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            mock_response = {
                'data': {
                    'GBP': 0.15,  # 1 BRL = 0.15 GBP
                    'JPY': 25.0   # 1 BRL = 25 JPY
                }
            }
            mock_client.latest.return_value = mock_response
            
            currency_service = CurrencyService("test_key")
            
            with patch('services.currency_service.datetime') as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "10:15:30"
                result = currency_service.get_exchange_rates(
                    base_currency='BRL', 
                    target_currencies=['GBP', 'JPY']
                )
            
            self.assertIsNotNone(result)
            self.assertAlmostEqual(result['GBP/BRL'], 6.6667, places=4)  # 1/0.15
            self.assertEqual(result['JPY/BRL'], 0.04)  # 1/25
            self.assertEqual(result['timestamp'], "10:15:30")
            self.assertEqual(result['base_currency'], 'BRL')

class TestDisplayServiceIntegration(unittest.TestCase):
    """Integration tests for DisplayService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.display_service = DisplayService(simulation_mode=True)
    
    def test_font_fallback(self):
        """Test font loading with fallback to default"""
        with patch('services.display_service.ImageFont') as mock_font:
            # Simulate font file not found
            mock_font.truetype.side_effect = Exception("Font file not found")
            mock_default_font = Mock()
            mock_font.load_default.return_value = mock_default_font
            
            font_large, font_medium, font_small = self.display_service.load_fonts()
            
            self.assertEqual(font_large, mock_default_font)
            self.assertEqual(font_medium, mock_default_font)
            self.assertEqual(font_small, mock_default_font)
    
    def test_image_creation_edge_cases(self):
        """Test image creation with edge case data"""
        # Test with empty rates_data
        image = self.display_service.create_currency_display_image({})
        self.assertIsNotNone(image)
        
        # Test with partial data
        partial_data = {
            'USD/BRL': 5.25,
            # Missing EUR/BRL and timestamp
        }
        image = self.display_service.create_currency_display_image(partial_data)
        self.assertIsNotNone(image)
        
        # Test with very large numbers
        large_numbers_data = {
            'USD/BRL': 999999.9999,
            'EUR/BRL': 0.0001,
            'timestamp': '23:59:59'
        }
        image = self.display_service.create_currency_display_image(large_numbers_data)
        self.assertIsNotNone(image)

if __name__ == '__main__':
    unittest.main(verbosity=2)