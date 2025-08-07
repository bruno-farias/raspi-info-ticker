#!/usr/bin/python
# -*- coding:utf-8 -*-
"""
Display configuration system for cycling through different information screens
"""

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
        
        # Define the screens to cycle through
        # Each screen is a tuple of (title, data_function, display_function)
        self.screens = [
            ("Exchange Rates", self._get_fiat_rates, self._display_fiat_rates),
            ("Bitcoin Prices", self._get_btc_rates, self._display_btc_rates),
        ]
    
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
            return {
                'title': title,
                'rates_data': rates_data,
                'display_function': display_func,
                'screen_number': self.current_screen + 1,
                'total_screens': len(self.screens)
            }
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
        """Get BTC/USD and BTC/EUR rates"""
        return self.currency_service.get_btc_rates()
    
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
        if rates_data.get('BTC/EUR'):
            lines.append(f"BTC/EUR: €{rates_data['BTC/EUR']:,}")
            
        return lines