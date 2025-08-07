#!/usr/bin/python
# -*- coding:utf-8 -*-
import os
import sys
import logging
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Add waveshare_epd to path if it exists locally (matching example.py structure)
libdir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'waveshare_epd')
if os.path.exists(libdir):
    sys.path.append(os.path.dirname(libdir))

# Try to import e-paper display, fallback to simulation mode if not available
try:
    from waveshare_epd import epd2in13_V4
    DISPLAY_AVAILABLE = True
    print("DEBUG: waveshare_epd imported successfully")
except ImportError as e:
    DISPLAY_AVAILABLE = False
    print(f"DEBUG: waveshare_epd import failed: {e}")
    print(f"DEBUG: Checked path: {waveshare_path}")
    print(f"DEBUG: Path exists: {os.path.exists(waveshare_path)}")
except RuntimeError as e:
    DISPLAY_AVAILABLE = False
    print(f"DEBUG: GPIO initialization failed (hardware issue): {e}")
    print("DEBUG: Running in simulation mode - e-paper display not connected or GPIO in use")
except Exception as e:
    DISPLAY_AVAILABLE = False
    print(f"DEBUG: waveshare_epd initialization failed: {e}")

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
    
    def load_btc_logo(self, size=35):
        """
        Load and prepare Bitcoin logo image (supports PNG, WebP, SVG)
        
        Args:
            size (int): Desired size for the logo
            
        Returns:
            PIL.Image: Processed Bitcoin logo or None if not found
        """
        # Try different file formats in order of preference
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
        logo_files = [
            'bitcoin.svg',
            'bitcoin-logo.svg',
            'bitcoin-bw.webp', 
            'wrapped-bitcoin.png',
            'bitcoin.png',
            'btc-logo.svg'
        ]
        
        for filename in logo_files:
            logo_path = os.path.join(assets_dir, filename)
            if os.path.exists(logo_path):
                try:
                    return self._load_logo_file(logo_path, size)
                except Exception as e:
                    self.logger.warning(f"Failed to load {filename}: {e}")
                    continue
        
        self.logger.warning(f"No Bitcoin logo found in {assets_dir}")
        return None
    
    def _load_logo_file(self, logo_path, size):
        """
        Load a logo file (PNG, WebP, or SVG)
        
        Args:
            logo_path (str): Path to the logo file
            size (int): Desired size
            
        Returns:
            PIL.Image: Processed logo image
        """
        file_ext = os.path.splitext(logo_path)[1].lower()
        
        if file_ext == '.svg':
            return self._load_svg_logo(logo_path, size)
        else:
            return self._load_bitmap_logo(logo_path, size)
    
    def _load_svg_logo(self, svg_path, size):
        """
        Load and convert SVG logo to bitmap
        
        Args:
            svg_path (str): Path to SVG file
            size (int): Desired size
            
        Returns:
            PIL.Image: Converted bitmap image
        """
        try:
            # Try to import cairosvg for SVG conversion
            import cairosvg
            from io import BytesIO
            
            # Convert SVG to PNG in memory
            png_data = cairosvg.svg2png(
                url=svg_path,
                output_width=size,
                output_height=size
            )
            
            # Load PNG data into PIL Image
            logo = Image.open(BytesIO(png_data))
            
            # Convert to grayscale
            if logo.mode != 'L':
                logo = logo.convert('L')
            
            # Convert to 1-bit monochrome for e-paper
            logo = logo.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
            
            self.logger.debug(f"SVG logo loaded and converted: {logo.size}")
            return logo
            
        except ImportError:
            # Fallback: Try with Pillow's built-in SVG support (limited)
            self.logger.warning("cairosvg not available, trying alternative SVG loading")
            
            try:
                # Some versions of Pillow can handle simple SVGs
                logo = Image.open(svg_path)
                return self._process_bitmap_logo(logo, size)
            except Exception as e:
                self.logger.error(f"Cannot load SVG without cairosvg: {e}")
                raise
        
        except Exception as e:
            self.logger.error(f"Error loading SVG logo: {e}")
            raise
    
    def _load_bitmap_logo(self, logo_path, size):
        """
        Load bitmap logo (PNG, WebP, etc.)
        
        Args:
            logo_path (str): Path to bitmap file
            size (int): Desired size
            
        Returns:
            PIL.Image: Processed bitmap image
        """
        logo = Image.open(logo_path)
        return self._process_bitmap_logo(logo, size)
    
    def _process_bitmap_logo(self, logo, size):
        """
        Process bitmap logo for e-paper display
        
        Args:
            logo (PIL.Image): Input logo image
            size (int): Desired size
            
        Returns:
            PIL.Image: Processed logo
        """
        # Convert to grayscale if needed
        if logo.mode != 'L':
            logo = logo.convert('L')
        
        # Resize to desired size while maintaining aspect ratio
        logo.thumbnail((size, size), Image.Resampling.LANCZOS)
        
        # Convert to 1-bit (monochrome) for e-paper display
        logo = logo.convert('1', dither=Image.Dither.FLOYDSTEINBERG)
        
        self.logger.debug(f"Bitmap logo processed: {logo.size}")
        return logo
    
    def draw_btc_logo_fallback(self, draw, x, y, size=35):
        """
        Draw a simple Bitcoin logo as fallback when image is not available
        
        Args:
            draw: PIL ImageDraw object
            x (int): X position for logo center
            y (int): Y position for logo center
            size (int): Size of the logo
        """
        # Calculate bounds
        half_size = size // 2
        left = x - half_size
        top = y - half_size
        right = x + half_size
        bottom = y + half_size
        
        # Draw outer circle
        circle_margin = 2
        draw.ellipse(
            [(left + circle_margin, top + circle_margin), 
             (right - circle_margin, bottom - circle_margin)], 
            outline=0, width=2
        )
        
        # Draw simple "B" in the center
        center_x = x
        center_y = y
        
        # "B" dimensions
        b_width = size // 3
        b_height = size // 2
        b_left = center_x - b_width // 2
        b_top = center_y - b_height // 2
        b_right = b_left + b_width
        b_bottom = b_top + b_height
        b_middle = center_y
        
        # Vertical line of the "B"
        draw.line([(b_left, b_top), (b_left, b_bottom)], fill=0, width=2)
        
        # Horizontal lines of the "B"
        draw.line([(b_left, b_top), (b_right - 4, b_top)], fill=0, width=2)
        draw.line([(b_left, b_middle), (b_right - 2, b_middle)], fill=0, width=2)
        draw.line([(b_left, b_bottom), (b_right - 4, b_bottom)], fill=0, width=2)
        
        # Currency symbol lines
        currency_offset = 2
        draw.line([(center_x - currency_offset, b_top - 6), (center_x - currency_offset, b_bottom + 6)], fill=0, width=1)
        draw.line([(center_x + currency_offset, b_top - 6), (center_x + currency_offset, b_bottom + 6)], fill=0, width=1)
    
    def create_display_image(self, screen_data):
        """
        Create an image with configurable screen data
        
        Args:
            screen_data (dict): Screen data with title, rates, and display function
            
        Returns:
            PIL.Image: Generated display image
        """
        image = Image.new('1', (self.width, self.height), 255)  # 255: white background
        draw = ImageDraw.Draw(image)
        
        font_large, font_medium, font_small = self.load_fonts()
        
        if screen_data and screen_data.get('rates_data'):
            # Title with screen indicator
            title = screen_data.get('title', 'Info')
            screen_num = screen_data.get('screen_number', 1)
            total_screens = screen_data.get('total_screens', 1)
            title_text = f"{title} ({screen_num}/{total_screens})"
            draw.text((10, 10), title_text, font=font_large, fill=0)
            
            # Check if this screen should show a logo
            show_logo = screen_data.get('show_logo', False)
            logo_type = screen_data.get('logo_type', None)
            
            # Get formatted display lines
            display_function = screen_data.get('display_function')
            rates_data = screen_data.get('rates_data')
            
            if display_function and rates_data:
                lines = display_function(rates_data)
                y_pos = 35
                for line in lines[:2]:  # Max 2 lines for rates
                    draw.text((10, y_pos), line, font=font_medium, fill=0)
                    y_pos += 20
            
            # Draw logo if requested
            if show_logo and logo_type == 'btc':
                # Position logo on the right side, centered vertically for the rates area
                logo_x = self.width - 40  # 40 pixels from right edge
                logo_y = 50  # Center it in the rates display area
                
                # Try to load the image logo first
                logo_image = self.load_btc_logo(size=35)
                
                if logo_image:
                    # Calculate position for pasting (top-left corner)
                    paste_x = logo_x - logo_image.width // 2
                    paste_y = logo_y - logo_image.height // 2
                    
                    # Paste the logo image onto the main image
                    image.paste(logo_image, (paste_x, paste_y))
                    self.logger.debug(f"Bitcoin image logo displayed at ({paste_x}, {paste_y})")
                else:
                    # Fallback to drawn logo
                    self.draw_btc_logo_fallback(draw, logo_x, logo_y, size=35)
                    self.logger.debug("Using fallback drawn Bitcoin logo")
            
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
            draw.text((10, 50), "No data available", font=font_medium, fill=0)
            draw.rectangle([(0, 0), (self.width-1, self.height-1)], outline=0, width=1)
        
        return image
    
    def create_currency_display_image(self, rates_data):
        """
        Backward compatibility method - create image with currency information
        
        Args:
            rates_data (dict): Currency rates data or None
            
        Returns:
            PIL.Image: Generated display image
        """
        # Convert old format to new screen_data format
        screen_data = {
            'title': 'Exchange Rates',
            'rates_data': rates_data,
            'display_function': self._legacy_display_function,
            'screen_number': 1,
            'total_screens': 1
        } if rates_data else None
        
        return self.create_display_image(screen_data)
    
    def _legacy_display_function(self, rates_data):
        """Legacy display function for backward compatibility"""
        lines = []
        if rates_data.get('USD/BRL'):
            lines.append(f"USD/BRL: {rates_data['USD/BRL']}")
        if rates_data.get('EUR/BRL'):
            lines.append(f"EUR/BRL: {rates_data['EUR/BRL']}")
        return lines
    
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