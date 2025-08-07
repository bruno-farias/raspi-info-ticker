#!/usr/bin/python
# -*- coding:utf-8 -*-
import logging
import requests
from datetime import datetime

class CryptoService:
    """Service class to handle cryptocurrency price operations"""
    
    def __init__(self, api_key=None):
        """
        Initialize the crypto service
        
        Args:
            api_key (str): API key if required (optional for some APIs)
        """
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)
        
        # Example APIs you can use:
        # 1. CoinGecko (free, no API key needed)
        # 2. CoinMarketCap (requires API key)
        # 3. Binance (free, no API key needed)
        
        self.base_urls = {
            'coingecko': 'https://api.coingecko.com/api/v3',
            'coinmarketcap': 'https://pro-api.coinmarketcap.com/v1',
            'binance': 'https://api.binance.com/api/v3'
        }
    
    def get_btc_prices_coingecko(self):
        """
        Get BTC prices using CoinGecko API
        
        Returns:
            dict: BTC prices in USD and EUR
        """
        try:
            self.logger.info("Fetching BTC prices from CoinGecko")
            
            url = f"{self.base_urls['coingecko']}/simple/price"
            params = {
                'ids': 'bitcoin',
                'vs_currencies': 'usd,eur',
                'include_24hr_change': 'true'  # Include price change data
            }
            
            headers = {}
            if self.api_key:
                headers['x-cg-demo-api-key'] = self.api_key
                self.logger.debug("Using CoinGecko API key")
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self.logger.debug(f"CoinGecko response: {data}")
            
            if 'bitcoin' in data:
                btc_data = data['bitcoin']
                
                # Format prices with proper rounding
                btc_usd = btc_data.get('usd')
                btc_eur = btc_data.get('eur')
                
                if btc_usd:
                    btc_usd = round(btc_usd, 2)
                if btc_eur:
                    btc_eur = round(btc_eur, 2)
                
                result = {
                    'BTC/USD': btc_usd,
                    'BTC/EUR': btc_eur,
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'source': 'CoinGecko'
                }
                
                # Add price change data if available
                if 'usd_24h_change' in btc_data:
                    result['usd_24h_change'] = round(btc_data['usd_24h_change'], 2)
                if 'eur_24h_change' in btc_data:
                    result['eur_24h_change'] = round(btc_data['eur_24h_change'], 2)
                
                return result
            else:
                self.logger.error("No bitcoin data in CoinGecko response")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error fetching from CoinGecko: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching BTC prices from CoinGecko: {e}")
            return None
    
    def get_btc_prices_coinmarketcap(self):
        """
        Get BTC prices using CoinMarketCap API (requires API key)
        
        Returns:
            dict: BTC prices in USD and EUR
        """
        if not self.api_key:
            self.logger.error("CoinMarketCap API key not provided")
            return None
            
        try:
            self.logger.info("Fetching BTC prices from CoinMarketCap")
            
            url = f"{self.base_urls['coinmarketcap']}/cryptocurrency/quotes/latest"
            headers = {
                'X-CMC_PRO_API_KEY': self.api_key,
            }
            params = {
                'symbol': 'BTC',
                'convert': 'USD,EUR'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self.logger.debug(f"CoinMarketCap response: {data}")
            
            if 'data' in data and 'BTC' in data['data']:
                btc_data = data['data']['BTC']['quote']
                return {
                    'BTC/USD': round(btc_data['USD']['price'], 2),
                    'BTC/EUR': round(btc_data['EUR']['price'], 2),
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'source': 'CoinMarketCap'
                }
            else:
                self.logger.error("No BTC data in CoinMarketCap response")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error fetching from CoinMarketCap: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching BTC prices from CoinMarketCap: {e}")
            return None
    
    def get_btc_prices_binance(self):
        """
        Get BTC prices using Binance API (free, no API key needed)
        Note: Binance gives prices in pairs, so we get BTCUSDT and BTCEUR
        
        Returns:
            dict: BTC prices in USD and EUR
        """
        try:
            self.logger.info("Fetching BTC prices from Binance")
            
            # Get BTC/USDT price
            url_usdt = f"{self.base_urls['binance']}/ticker/price"
            params_usdt = {'symbol': 'BTCUSDT'}
            
            response_usdt = requests.get(url_usdt, params=params_usdt, timeout=10)
            response_usdt.raise_for_status()
            
            # Get BTC/EUR price (if available)
            params_eur = {'symbol': 'BTCEUR'}
            response_eur = requests.get(url_usdt, params=params_eur, timeout=10)
            
            btc_usd = None
            btc_eur = None
            
            usdt_data = response_usdt.json()
            if 'price' in usdt_data:
                btc_usd = round(float(usdt_data['price']), 2)
            
            if response_eur.status_code == 200:
                eur_data = response_eur.json()
                if 'price' in eur_data:
                    btc_eur = round(float(eur_data['price']), 2)
            
            return {
                'BTC/USD': btc_usd,
                'BTC/EUR': btc_eur,
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'source': 'Binance'
            }
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error fetching from Binance: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching BTC prices from Binance: {e}")
            return None
    
    def get_btc_prices(self, preferred_source='coingecko'):
        """
        Get BTC prices with fallback to different sources
        
        Args:
            preferred_source (str): Preferred API source
            
        Returns:
            dict: BTC prices with fallback
        """
        sources = {
            'coingecko': self.get_btc_prices_coingecko,
            'coinmarketcap': self.get_btc_prices_coinmarketcap,
            'binance': self.get_btc_prices_binance
        }
        
        # Try preferred source first
        if preferred_source in sources:
            result = sources[preferred_source]()
            if result:
                return result
        
        # Fallback to other sources
        for source_name, source_func in sources.items():
            if source_name != preferred_source:
                self.logger.info(f"Trying fallback source: {source_name}")
                result = source_func()
                if result:
                    return result
        
        self.logger.error("All crypto API sources failed")
        return None