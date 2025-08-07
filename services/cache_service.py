#!/usr/bin/python
# -*- coding:utf-8 -*-
import time
import logging
import os
from typing import Any, Dict, Optional

class CacheService:
    """Simple in-memory cache service for currency data"""
    
    def __init__(self):
        """Initialize the cache service"""
        self.logger = logging.getLogger(__name__)
        self._cache = {}  # {key: {'data': data, 'timestamp': timestamp, 'ttl': ttl}}
        
        # Load cache configuration
        self.default_ttl = int(os.getenv('CACHE_DEFAULT_TTL', '60'))  # 1 minute default
        self.screen_cache_config = self._parse_screen_cache_config()
        
        self.logger.debug(f"Cache initialized with default TTL: {self.default_ttl}s")
        self.logger.debug(f"Per-screen config: {self.screen_cache_config}")
    
    def _parse_screen_cache_config(self) -> Dict[str, int]:
        """
        Parse per-screen cache configuration from environment
        
        Returns:
            Dict[str, int]: Screen name to TTL mapping
        """
        config = {}
        cache_per_screen = os.getenv('CACHE_PER_SCREEN', '')
        
        if cache_per_screen:
            try:
                # Format: "screen1:60,screen2:120"
                for item in cache_per_screen.split(','):
                    if ':' in item:
                        screen_name, ttl_str = item.strip().split(':', 1)
                        config[screen_name.strip()] = int(ttl_str.strip())
            except Exception as e:
                self.logger.warning(f"Error parsing CACHE_PER_SCREEN: {e}")
        
        return config
    
    def get_ttl_for_screen(self, screen_type: str) -> int:
        """
        Get cache TTL for a specific screen type
        
        Args:
            screen_type (str): Screen type (e.g., 'bitcoin_prices', 'exchange_rates')
            
        Returns:
            int: TTL in seconds
        """
        return self.screen_cache_config.get(screen_type, self.default_ttl)
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get cached data if still valid
        
        Args:
            key (str): Cache key
            
        Returns:
            Any: Cached data or None if expired/not found
        """
        if key not in self._cache:
            self.logger.debug(f"Cache miss: {key}")
            return None
        
        cache_entry = self._cache[key]
        current_time = time.time()
        
        # Check if cache entry has expired
        if current_time - cache_entry['timestamp'] > cache_entry['ttl']:
            self.logger.debug(f"Cache expired: {key}")
            del self._cache[key]
            return None
        
        self.logger.debug(f"Cache hit: {key}")
        return cache_entry['data']
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """
        Store data in cache
        
        Args:
            key (str): Cache key
            data (Any): Data to cache
            ttl (int, optional): Time to live in seconds. Uses default if not specified.
        """
        if ttl is None:
            ttl = self.default_ttl
        
        self._cache[key] = {
            'data': data,
            'timestamp': time.time(),
            'ttl': ttl
        }
        
        self.logger.debug(f"Cached: {key} (TTL: {ttl}s)")
    
    def invalidate(self, key: str) -> None:
        """
        Remove specific key from cache
        
        Args:
            key (str): Cache key to remove
        """
        if key in self._cache:
            del self._cache[key]
            self.logger.debug(f"Cache invalidated: {key}")
    
    def clear(self) -> None:
        """Clear all cached data"""
        cache_size = len(self._cache)
        self._cache.clear()
        self.logger.debug(f"Cache cleared ({cache_size} entries removed)")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        current_time = time.time()
        valid_entries = 0
        expired_entries = 0
        
        for key, entry in self._cache.items():
            if current_time - entry['timestamp'] <= entry['ttl']:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            'total_entries': len(self._cache),
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'default_ttl': self.default_ttl,
            'screen_configs': self.screen_cache_config
        }
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache
        
        Returns:
            int: Number of entries removed
        """
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self._cache.items():
            if current_time - entry['timestamp'] > entry['ttl']:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)


# Global cache instance
cache_service = CacheService()