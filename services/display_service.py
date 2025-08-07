#!/usr/bin/python
# -*- coding:utf-8 -*-
import os
import logging
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Try to import e-paper display, fallback to simulation mode if not available
try:
    from waveshare_epd import epd2in13_V4
    DISPLAY_AVAILABLE = True
except ImportError:
    DISPLAY_AVAILABLE = False

class DisplayService:
    """Service class to handle e-paper display operations"""
    
    def __init__(self, simulation_mode=None):
        """
        Initialize the display service
        
        Args:
            simulation_mode (bool): Force simulation mode, None for auto-detect
        """
        self.logger = logging.getLogger(__name__)
        
        if simulation_mode is None:
            self.simulation_mode = not DISPLAY_AVAILABLE
        else:
            self.simulation_mode = simulation_mode
        
        if not self.simulation_mode and DISPLAY_AVAILABLE:
            try:
                self.epd = epd2in13_V4.EPD()
                self.width = self.epd.height
                self.height = self.epd.width
                self.logger.info("E-paper display initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize e-paper display: {e}")
                self.simulation_mode = True
        
        if self.simulation_mode:
            self.width = 250  # epd2in13_V4 dimensions
            self.height = 122
            self.logger.info("Display service running in simulation mode")
        
        # Setup font paths
        self.picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
    
    def load_fonts(self):
        """Load fonts with fallback to default"""
        try:
            font_large = ImageFont.truetype(os.path.join(self.picdir, 'Font.ttc'), 20)
            font_medium = ImageFont.truetype(os.path.join(self.picdir, 'Font.ttc'), 16)
            font_small = ImageFont.truetype(os.path.join(self.picdir, 'Font.ttc'), 12)
            self.logger.debug("Custom fonts loaded successfully")
        except Exception as e:
            self.logger.debug(f"Custom fonts not available, using defaults: {e}")
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        return font_large, font_medium, font_small
    
    def create_currency_display_image(self, rates_data):
        """
        Create an image with currency information
        
        Args:
            rates_data (dict): Currency rates data or None
            
        Returns:
            PIL.Image: Generated display image
        """
        image = Image.new('1', (self.width, self.height), 255)  # 255: white background
        draw = ImageDraw.Draw(image)
        
        font_large, font_medium, font_small = self.load_fonts()
        
        if rates_data:
            # Title
            draw.text((10, 10), "Exchange Rates", font=font_large, fill=0)
            
            # USD/BRL
            usd_rate = rates_data.get('USD/BRL', 'N/A')
            usd_text = f"USD/BRL: {usd_rate}"
            draw.text((10, 35), usd_text, font=font_medium, fill=0)
            
            # EUR/BRL
            eur_rate = rates_data.get('EUR/BRL', 'N/A')
            eur_text = f"EUR/BRL: {eur_rate}"
            draw.text((10, 55), eur_text, font=font_medium, fill=0)
            
            # Data timestamp
            data_timestamp = rates_data.get('timestamp', 'N/A')
            time_text = f"Data: {data_timestamp}"
            draw.text((10, 75), time_text, font=font_small, fill=0)
            
            # Screen refresh timestamp
            refresh_text = f"Screen: {datetime.now().strftime('%H:%M:%S')}"
            draw.text((10, 90), refresh_text, font=font_small, fill=0)
            
            # Add border
            draw.rectangle([(0, 0), (self.width-1, self.height-1)], outline=0, width=2)
        else:
            draw.text((10, 50), "Failed to fetch rates", font=font_medium, fill=0)
            draw.rectangle([(0, 0), (self.width-1, self.height-1)], outline=0, width=1)
        
        return image
    
    def initialize_display(self):
        """Initialize the e-paper display"""
        if not self.simulation_mode:
            try:
                self.epd.init()
                self.epd.Clear(0xFF)
                self.logger.info("E-paper display initialized and cleared")
            except Exception as e:
                self.logger.error(f"Failed to initialize display: {e}")
                raise
    
    def display_image(self, image, filename="currency_display_simulation.png"):
        """
        Display image on e-paper display or save to file in simulation mode
        
        Args:
            image (PIL.Image): Image to display
            filename (str): Filename for simulation mode
        """
        if self.simulation_mode:
            try:
                image.save(filename)
                self.logger.info(f"Display simulation saved to {filename}")
            except Exception as e:
                self.logger.error(f"Failed to save simulation image: {e}")
        else:
            try:
                self.epd.display(self.epd.getbuffer(image))
                self.logger.debug("Image displayed on e-paper")
            except Exception as e:
                self.logger.error(f"Failed to display image: {e}")
                raise
    
    def clear_display(self):
        """Clear the e-paper display"""
        if not self.simulation_mode:
            try:
                self.epd.init()
                self.epd.Clear(0xFF)
                self.logger.info("Display cleared")
            except Exception as e:
                self.logger.error(f"Failed to clear display: {e}")
    
    def sleep_display(self):
        """Put the e-paper display to sleep mode"""
        if not self.simulation_mode:
            try:
                self.epd.sleep()
                self.logger.info("Display put to sleep")
            except Exception as e:
                self.logger.error(f"Failed to put display to sleep: {e}")
    
    def cleanup(self):
        """Cleanup display resources"""
        self.clear_display()
        self.sleep_display()