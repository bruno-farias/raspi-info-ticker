#!/usr/bin/python
# -*- coding:utf-8 -*-
import logging
from datetime import datetime
import freecurrencyapi

class CurrencyService:
    """Service class to handle currency exchange rate operations"""
    
    def __init__(self, api_key):
        """Initialize the currency service with API key"""
        self.client = freecurrencyapi.Client(api_key)
        self.logger = logging.getLogger(__name__)
    
    def get_exchange_rates(self, base_currency='BRL', target_currencies=None):
        """
        Fetch exchange rates from the API
        
        Args:
            base_currency (str): Base currency code (default: BRL)
            target_currencies (list): List of target currency codes
        
        Returns:
            dict: Exchange rates data with timestamp, or None if error
        """
        if target_currencies is None:
            target_currencies = ['USD', 'EUR']
        
        try:
            self.logger.info(f"Fetching rates for {target_currencies} against {base_currency}")
            
            # Get latest rates with specified base currency
            rates = self.client.latest(
                base_currency=base_currency, 
                currencies=target_currencies
            )
            
            if 'data' not in rates:
                self.logger.error("No data in API response")
                return None
            
            # Convert rates from base currency perspective
            exchange_rates = {}
            for currency in target_currencies:
                if rates['data'].get(currency):
                    # If base is BRL and we get USD=0.2, then USD/BRL = 1/0.2 = 5
                    rate = 1 / rates['data'][currency]
                    exchange_rates[f'{currency}/{base_currency}'] = round(rate, 4)
                else:
                    self.logger.warning(f"No rate data for {currency}")
                    exchange_rates[f'{currency}/{base_currency}'] = 0
            
            return {
                **exchange_rates,
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'base_currency': base_currency
            }
                
        except Exception as e:
            self.logger.error(f"Error fetching exchange rates: {e}")
            return None
    
    def get_usd_brl_eur_brl_rates(self):
        """
        Convenience method to get USD/BRL and EUR/BRL rates
        
        Returns:
            dict: Exchange rates for USD/BRL and EUR/BRL with timestamp
        """
        return self.get_exchange_rates(base_currency='BRL', target_currencies=['USD', 'EUR'])