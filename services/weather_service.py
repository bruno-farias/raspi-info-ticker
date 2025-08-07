#!/usr/bin/python
# -*- coding:utf-8 -*-
import logging
import requests
from datetime import datetime
import os
import sys

# Import cache service
try:
    from .cache_service import cache_service
except ImportError:
    sys.path.append(os.path.dirname(__file__))
    from cache_service import cache_service

class WeatherService:
    """Service class to handle weather data operations"""
    
    def __init__(self):
        """Initialize the weather service"""
        self.logger = logging.getLogger(__name__)
        
        # Load configuration from environment
        self.api_key = os.getenv('OPEN_WEATHER_API_KEY')
        self.city = os.getenv('OPEN_WEATHER_CITY')
        self.state = os.getenv('OPEN_WEATHER_STATE', '')
        self.country = os.getenv('OPEN_WEATHER_COUNTRY', '')
        
        if not self.api_key or not self.city:
            self.logger.warning("Weather service not configured - missing API key or city")
            self.configured = False
        else:
            self.configured = True
            self.logger.info(f"Weather service configured for {self.city}")
    
    def get_weather_data(self):
        """
        Get current weather data with caching
        
        Returns:
            dict: Weather data with temperature, description, icon, etc.
        """
        if not self.configured:
            return None
        
        cache_key = f"weather_{self.city}_{self.country}"
        screen_type = "weather"
        
        # Try to get from cache first
        cached_data = cache_service.get(cache_key)
        if cached_data:
            self.logger.debug(f"Using cached weather data for {self.city}")
            # Update the timestamp to show when this cached data is being returned
            cached_data = cached_data.copy()
            original_time = cached_data.get('timestamp', 'Unknown')
            cached_data['timestamp'] = f"{original_time} (cached)"
            return cached_data
        
        # Fetch fresh data
        self.logger.info(f"Fetching fresh weather data for {self.city}")
        fresh_data = self._fetch_weather_from_api()
        
        # Cache the result if successful
        if fresh_data:
            ttl = cache_service.get_ttl_for_screen(screen_type)
            cache_service.set(cache_key, fresh_data, ttl)
        
        return fresh_data
    
    def _fetch_weather_from_api(self):
        """
        Fetch weather data from OpenWeatherMap API
        
        Returns:
            dict: Processed weather data or None if error
        """
        try:
            # Build location string
            location_parts = [self.city]
            if self.state:
                location_parts.append(self.state)
            if self.country:
                location_parts.append(self.country)
            location = ','.join(location_parts)
            
            # API URL
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': location,
                'appid': self.api_key,
                'units': 'metric'  # Celsius, metric system
            }
            
            self.logger.debug(f"Fetching weather from: {url} with location: {location}")
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self.logger.debug(f"Weather API response: {data}")
            
            return self._process_weather_data(data)
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error fetching weather data: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching weather data: {e}")
            return None
    
    def _process_weather_data(self, raw_data):
        """
        Process raw weather data from API
        
        Args:
            raw_data (dict): Raw API response
            
        Returns:
            dict: Processed weather data
        """
        try:
            # Extract main weather info
            main = raw_data.get('main', {})
            weather = raw_data.get('weather', [{}])[0]
            wind = raw_data.get('wind', {})
            
            # Temperature
            temp_current = main.get('temp', 0)
            temp_feels_like = main.get('feels_like', 0)
            temp_min = main.get('temp_min', 0)
            temp_max = main.get('temp_max', 0)
            
            # Weather condition
            weather_main = weather.get('main', 'Unknown')  # e.g., "Rain", "Snow", "Clear"
            weather_description = weather.get('description', 'Unknown')  # e.g., "light rain"
            weather_icon = weather.get('icon', '01d')  # e.g., "10d"
            
            # Additional info
            humidity = main.get('humidity', 0)
            pressure = main.get('pressure', 0)
            wind_speed = wind.get('speed', 0)
            
            # Location
            city_name = raw_data.get('name', self.city)
            country_code = raw_data.get('sys', {}).get('country', self.country)
            
            processed_data = {
                'city': city_name,
                'country': country_code,
                'temperature': round(temp_current, 1),
                'feels_like': round(temp_feels_like, 1),
                'temp_min': round(temp_min, 1),
                'temp_max': round(temp_max, 1),
                'weather_main': weather_main,
                'weather_description': weather_description.title(),
                'weather_icon': weather_icon,
                'humidity': humidity,
                'pressure': pressure,
                'wind_speed': round(wind_speed, 1),
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'source': 'OpenWeatherMap'
            }
            
            self.logger.info(f"Weather processed: {city_name} {temp_current}°C, {weather_description}")
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Error processing weather data: {e}")
            return None
    
    def get_weather_icon_filename(self, weather_data):
        """
        Get the appropriate weather icon filename based on weather data
        
        Args:
            weather_data (dict): Weather data containing weather info
            
        Returns:
            str: Icon filename to look for
        """
        if not weather_data:
            return None
        
        # OpenWeatherMap icon mapping to downloaded official icons
        # See: https://openweathermap.org/weather-conditions
        icon_map = {
            # Clear sky
            '01d': '01d@2x.png',     # clear sky day
            '01n': '01n@2x.png',     # clear sky night
            
            # Few clouds
            '02d': '02d@2x.png',     # few clouds day
            '02n': '02n@2x.png',     # few clouds night
            
            # Scattered clouds
            '03d': '03d@2x.png',     # scattered clouds day
            '03n': '03n@2x.png',     # scattered clouds night
            
            # Broken clouds
            '04d': '04d@2x.png',     # broken clouds day
            '04n': '04n@2x.png',     # broken clouds night
            
            # Shower rain
            '09d': '09d@2x.png',     # shower rain day
            '09n': '09n@2x.png',     # shower rain night
            
            # Rain
            '10d': '10d@2x.png',     # rain day
            '10n': '10n@2x.png',     # rain night
            
            # Thunderstorm
            '11d': '11d@2x.png',     # thunderstorm day
            '11n': '11n@2x.png',     # thunderstorm night
            
            # Snow
            '13d': '13d@2x.png',     # snow day
            '13n': '13n@2x.png',     # snow night
            
            # Mist/Fog
            '50d': '50d@2x.png',     # mist day
            '50n': '50n@2x.png',     # mist night
        }
        
        weather_icon = weather_data.get('weather_icon', '01d')
        icon_filename = icon_map.get(weather_icon, '01d@2x.png')  # fallback to sunny day icon
        
        self.logger.debug(f"Weather icon {weather_icon} mapped to {icon_filename}")
        return icon_filename