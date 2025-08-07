#!/usr/bin/python
# -*- coding:utf-8 -*-
"""
Display configuration system for cycling through different information screens
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from services.crypto_service import CryptoService
from services.weather_service import WeatherService

class DisplayConfig:
    """Configuration class for display cycling system"""
    
    def __init__(self, currency_service):
        """
        Initialize display configuration
        
        Args:
            currency_service: Instance of CurrencyService
        """
        self.currency_service = currency_service
        self.current_screen = 0
        
        # Initialize crypto service
        crypto_api_key = os.getenv('CRYPTO_API_KEY')
        self.crypto_service = CryptoService(crypto_api_key)
        self.crypto_source = os.getenv('CRYPTO_API_SOURCE', 'coingecko')
        
        # Initialize weather service
        self.weather_service = WeatherService()
        
        # Define available screens
        self.available_screens = {
            'exchange_rates': ("Exchange Rates", self._get_fiat_rates, self._display_fiat_rates),
            'bitcoin_prices': ("Bitcoin Prices", self._get_btc_rates, self._display_btc_rates),
            'weather': ("Weather", self._get_weather_data, self._display_weather_data),
        }
        
        # Get screen order from environment or use default
        screen_order = os.getenv('SCREEN_ORDER', 'bitcoin_prices,exchange_rates')
        ordered_screen_ids = [s.strip() for s in screen_order.split(',') if s.strip()]
        
        # Build screens list in the configured order
        self.screens = []
        for screen_id in ordered_screen_ids:
            if screen_id in self.available_screens:
                self.screens.append(self.available_screens[screen_id])
            else:
                print(f"Warning: Unknown screen '{screen_id}' in SCREEN_ORDER")
        
        # Fallback if no valid screens found
        if not self.screens:
            print("No valid screens found, using default order")
            self.screens = list(self.available_screens.values())
    
    def get_screen_count(self):
        """Get total number of configured screens"""
        return len(self.screens)
    
    def get_current_screen_data(self):
        """
        Get data for the current screen
        
        Returns:
            dict: Screen data with title, rates, and metadata
        """
        if not self.screens:
            return None
            
        title, data_func, display_func = self.screens[self.current_screen]
        rates_data = data_func()
        
        if rates_data:
            screen_data = {
                'title': title,
                'rates_data': rates_data,
                'display_function': display_func,
                'screen_number': self.current_screen + 1,
                'total_screens': len(self.screens)
            }
            
            # Add logo/icon information for specific screens
            if title == "Bitcoin Prices":
                screen_data['show_logo'] = True
                screen_data['logo_type'] = 'btc'
            elif title == "Weather":
                screen_data['show_logo'] = True
                screen_data['logo_type'] = 'weather'
                # Add weather icon filename
                if rates_data:
                    icon_filename = self.weather_service.get_weather_icon_filename(rates_data)
                    screen_data['weather_icon_filename'] = icon_filename
            
            return screen_data
        return None
    
    def next_screen(self):
        """Move to the next screen in the cycle"""
        self.current_screen = (self.current_screen + 1) % len(self.screens)
    
    def add_screen(self, title, data_function, display_function):
        """
        Add a new screen to the cycle
        
        Args:
            title (str): Screen title
            data_function (callable): Function to fetch data
            display_function (callable): Function to format display
        """
        self.screens.append((title, data_function, display_function))
    
    def _get_fiat_rates(self):
        """Get USD/BRL and EUR/BRL rates"""
        return self.currency_service.get_usd_brl_eur_brl_rates()
    
    def _get_btc_rates(self):
        """Get BTC/USD and BTC/EUR rates from crypto service"""
        return self.crypto_service.get_btc_prices(preferred_source=self.crypto_source)
    
    def _get_weather_data(self):
        """Get weather data from weather service"""
        return self.weather_service.get_weather_data()
    
    def _display_fiat_rates(self, rates_data):
        """
        Format fiat currency rates for display
        
        Args:
            rates_data (dict): Currency rates data
            
        Returns:
            list: List of display lines
        """
        if not rates_data:
            return ["Failed to fetch rates"]
        
        lines = []
        if 'USD/BRL' in rates_data:
            lines.append(f"USD/BRL: {rates_data['USD/BRL']}")
        if 'EUR/BRL' in rates_data:
            lines.append(f"EUR/BRL: {rates_data['EUR/BRL']}")
            
        return lines
    
    def _display_btc_rates(self, rates_data):
        """
        Format Bitcoin rates for display
        
        Args:
            rates_data (dict): Bitcoin rates data
            
        Returns:
            list: List of display lines
        """
        if not rates_data:
            return ["Failed to fetch BTC rates"]
        
        lines = []
        if rates_data.get('BTC/USD'):
            lines.append(f"BTC/USD: ${rates_data['BTC/USD']:,}")
        else:
            lines.append("BTC/USD: Not available")
            
        if rates_data.get('BTC/EUR'):
            lines.append(f"BTC/EUR: €{rates_data['BTC/EUR']:,}")
        else:
            lines.append("BTC/EUR: Not available")
            
        return lines
    
    def _display_weather_data(self, weather_data):
        """
        Format weather data for display
        
        Args:
            weather_data (dict): Weather data
            
        Returns:
            list: List of display lines
        """
        if not weather_data:
            return ["Failed to fetch weather"]
        
        lines = []
        
        # Temperature and location
        city = weather_data.get('city', 'Unknown')
        temp = weather_data.get('temperature', 0)
        lines.append(f"{city}: {temp}°C")
        
        # Weather description
        description = weather_data.get('weather_description', 'Unknown')
        lines.append(f"{description}")
        
        return lines