#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys
import os
import logging
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add services to path
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

from services.currency_service import CurrencyService
from services.display_service import DisplayService
from services.cache_service import cache_service
from config.display_config import DisplayConfig

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class CurrencyTicker:
    """Main application class that orchestrates currency fetching and display"""
    
    def __init__(self, api_key, simulation_mode=None):
        """
        Initialize the currency ticker
        
        Args:
            api_key (str): API key for currency service
            simulation_mode (bool): Force simulation mode, None for auto-detect
        """
        self.logger = logging.getLogger(__name__)
        self.currency_service = CurrencyService(api_key)
        self.display_service = DisplayService(simulation_mode)
        self.display_config = DisplayConfig(self.currency_service)
        
        # Get refresh interval from environment, default to 15 seconds
        self.refresh_interval = int(os.getenv('REFRESH_INTERVAL', '15'))
        
        # Log cache configuration
        cache_stats = cache_service.get_cache_stats()
        self.logger.info(f"Cache initialized - Default TTL: {cache_stats['default_ttl']}s")
        if cache_stats['screen_configs']:
            self.logger.info(f"Per-screen cache: {cache_stats['screen_configs']}")
        
    def run(self):
        """Main function to cycle through and display different screens"""
        try:
            self.logger.info(f"Starting currency ticker with {self.display_config.get_screen_count()} screens")
            self.logger.info(f"Refresh interval: {self.refresh_interval} seconds")
            self.display_service.initialize_display()
            
            while True:
                # Get current screen data
                screen_data = self.display_config.get_current_screen_data()
                
                if screen_data:
                    title = screen_data.get('title', 'Unknown')
                    screen_num = screen_data.get('screen_number', 1)
                    total_screens = screen_data.get('total_screens', 1)
                    
                    self.logger.info(f"Displaying screen {screen_num}/{total_screens}: {title}")
                    
                    # Log rates information
                    rates_data = screen_data.get('rates_data', {})
                    for key, value in rates_data.items():
                        if key not in ['timestamp', 'base_currency'] and value is not None:
                            self.logger.info(f"{key}: {value}")
                
                # Create and display image with smart refresh
                self.display_service.display_screen_with_smart_refresh(screen_data)
                
                # Move to next screen for next iteration
                self.display_config.next_screen()
                
                # Clean up expired cache entries periodically (every 10th iteration)
                if hasattr(self, '_iteration_count'):
                    self._iteration_count += 1
                else:
                    self._iteration_count = 1
                
                if self._iteration_count % 10 == 0:
                    cleaned = cache_service.cleanup_expired()
                    if cleaned > 0:
                        self.logger.debug(f"Cleaned up {cleaned} expired cache entries")
                
                # Wait for refresh interval
                time.sleep(self.refresh_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Stopping currency ticker...")
            self._cleanup()
        except Exception as e:
            self.logger.error(f"Error in currency ticker: {e}")
            self._cleanup()
    
    def _cleanup(self):
        """Cleanup resources"""
        try:
            self.display_service.cleanup()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

def main():
    """Main entry point"""
    api_key = os.getenv('FREE_CURRENCY_API_KEY')
    if not api_key:
        logging.error("FREE_CURRENCY_API_KEY not found in environment variables")
        logging.info("Available env vars: %s", list(os.environ.keys()))
        return
    
    logging.info("Starting with API key: %s...", api_key[:10])
    ticker = CurrencyTicker(api_key)
    ticker.run()

if __name__ == "__main__":
    main()