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

logging.basicConfig(level=logging.INFO)

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
        
    def run(self):
        """Main function to fetch and display exchange rates"""
        try:
            self.logger.info("Starting currency ticker")
            self.display_service.initialize_display()
            
            while True:
                self.logger.info("Fetching exchange rates...")
                rates_data = self.currency_service.get_usd_brl_eur_brl_rates()
                
                if rates_data:
                    self.logger.info(f"USD/BRL: {rates_data.get('USD/BRL', 'N/A')}")
                    self.logger.info(f"EUR/BRL: {rates_data.get('EUR/BRL', 'N/A')}")
                
                # Create and display image
                image = self.display_service.create_currency_display_image(rates_data)
                self.display_service.display_image(image)
                
                # Wait 10 seconds before next update
                time.sleep(10)
                
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
        return
    
    ticker = CurrencyTicker(api_key)
    ticker.run()

if __name__ == "__main__":
    main()