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
            'clock': ("Clock", self._get_clock_data, self._display_clock_data),
        }
        
        # Get screen order from environment or use default (now includes clock)
        screen_order = os.getenv('SCREEN_ORDER', 'bitcoin_prices,exchange_rates,clock')
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
        Format Bitcoin rates for display with 24h change indicators
        
        Args:
            rates_data (dict): Bitcoin rates data
            
        Returns:
            list: List of display lines
        """
        if not rates_data:
            return ["Failed to fetch BTC rates"]
        
        lines = []
        
        # Format USD price with change indicator
        if rates_data.get('BTC/USD'):
            usd_line = f"BTC/USD: ${rates_data['BTC/USD']:,}"
            
            # Add 24h change indicator if available
            if 'usd_24h_change' in rates_data:
                change = rates_data['usd_24h_change']
                if change > 0:
                    usd_line += f" ↑+{change}%"
                elif change < 0:
                    usd_line += f" ↓{change}%"
                else:
                    usd_line += f" ={change}%"
            
            lines.append(usd_line)
        else:
            lines.append("BTC/USD: Not available")
        
        # Format EUR price with change indicator  
        if rates_data.get('BTC/EUR'):
            eur_line = f"BTC/EUR: €{rates_data['BTC/EUR']:,}"
            
            # Add 24h change indicator if available
            if 'eur_24h_change' in rates_data:
                change = rates_data['eur_24h_change']
                if change > 0:
                    eur_line += f" ↑+{change}%"
                elif change < 0:
                    eur_line += f" ↓{change}%"
                else:
                    eur_line += f" ={change}%"
            
            lines.append(eur_line)
        else:
            lines.append("BTC/EUR: Not available")
            
        return lines
    
    def _display_weather_data(self, weather_data):
        """
        Format weather data for display with improved layout to avoid collisions
        Returns both left-side text and right-side details for positioning
        
        Args:
            weather_data (dict): Weather data
            
        Returns:
            dict: Layout data with 'left_lines' and 'right_details' sections
        """
        if not weather_data:
            return {"left_lines": ["Failed to fetch weather"], "right_details": []}
        
        # Main info for left side (below title, next to weather icon)
        city = weather_data.get('city', 'Unknown')
        temp = weather_data.get('temperature', 0)
        description = weather_data.get('weather_description', 'Unknown')
        
        left_lines = [
            f"{city}: {temp}°C",
            f"{description}"
        ]
        
        # Detailed stats for right side (below weather icon)  
        temp_min = weather_data.get('temp_min', 0)
        temp_max = weather_data.get('temp_max', 0)
        humidity = weather_data.get('humidity', 0)
        wind_speed = weather_data.get('wind_speed', 0)
        
        right_details = [
            f"Range: {temp_min}°C - {temp_max}°C",
            f"Humidity: {humidity}%",
            f"Wind: {wind_speed}m/s"
        ]
        
        return {
            "left_lines": left_lines,
            "right_details": right_details
        }
    
    def _get_clock_data(self):
        """
        Get current time and date data
        
        Returns:
            dict: Clock data with current time and date
        """
        from datetime import datetime
        
        now = datetime.now()
        
        return {
            'time': now.strftime('%H:%M:%S'),
            'date': now.strftime('%A, %B %d, %Y'),
            'short_date': now.strftime('%Y-%m-%d'),
            'timestamp': now.strftime('%H:%M:%S'),
            'day_name': now.strftime('%A'),
            'month_name': now.strftime('%B'),
            'day': now.strftime('%d'),
            'year': now.strftime('%Y')
        }
    
    def _display_clock_data(self, clock_data):
        """
        Format clock data for display
        
        Args:
            clock_data (dict): Clock data
            
        Returns:
            list: List of display lines
        """
        if not clock_data:
            return ["Clock unavailable"]
        
        lines = []
        
        # Large time display
        time_str = clock_data.get('time', 'N/A')
        lines.append(f"Time: {time_str}")
        
        # Date display
        date_str = clock_data.get('date', 'N/A')
        lines.append(f"{date_str}")
        
        return lines