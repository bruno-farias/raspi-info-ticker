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
    print(f"DEBUG: Checked libdir: {libdir}")
    print(f"DEBUG: Libdir exists: {os.path.exists(libdir)}")
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
        
        # Track display state for partial refresh optimization
        self.refresh_count = 0
        self.partial_refresh_initialized = False
        self.last_screen_number = None
        self.base_image = None
        self.current_cycle = 0
    
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
    
    def load_weather_icon(self, icon_filename, size=35):
        """
        Load weather icon from assets/weather directory
        
        Args:
            icon_filename (str): Icon filename (e.g., 'sunny.svg', 'rain.png')
            size (int): Desired size for the icon
            
        Returns:
            PIL.Image: Processed weather icon or None if not found
        """
        if not icon_filename:
            return None
        
        try:
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'weather')
            icon_path = os.path.join(assets_dir, icon_filename)
            
            if os.path.exists(icon_path):
                return self._load_logo_file(icon_path, size)
            else:
                # Try different extensions if exact filename not found
                base_name = os.path.splitext(icon_filename)[0]
                extensions = ['.svg', '.png', '.webp', '.jpg', '.jpeg']
                
                for ext in extensions:
                    test_path = os.path.join(assets_dir, f"{base_name}{ext}")
                    if os.path.exists(test_path):
                        return self._load_logo_file(test_path, size)
                
                self.logger.warning(f"Weather icon not found: {icon_filename}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error loading weather icon {icon_filename}: {e}")
            return None
    
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
            
            # Convert SVG to PNG in memory with better settings for e-paper
            png_data = cairosvg.svg2png(
                url=svg_path,
                output_width=size,
                output_height=size,
                background_color='white'  # Ensure white background
            )
            
            # Load PNG data into PIL Image
            logo = Image.open(BytesIO(png_data))
            
            # Ensure we have RGBA mode first for proper processing
            if logo.mode == 'RGBA':
                # Create a white background
                background = Image.new('RGB', logo.size, (255, 255, 255))
                # Composite the logo onto white background
                background.paste(logo, mask=logo.split()[-1])  # Use alpha channel as mask
                logo = background
            
            # Convert to grayscale
            if logo.mode != 'L':
                logo = logo.convert('L')
            
            # Apply threshold to make it more crisp for e-paper
            # This helps with rendering issues on monochrome displays
            import numpy as np
            logo_array = np.array(logo)
            # Apply threshold: anything darker than 128 becomes black (0), rest becomes white (255)
            logo_array = np.where(logo_array < 128, 0, 255).astype(np.uint8)
            logo = Image.fromarray(logo_array, mode='L')
            
            # Convert to 1-bit monochrome for e-paper
            logo = logo.convert('1')  # No dithering for cleaner logo
            
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
        
        except ImportError as e:
            if 'numpy' in str(e):
                self.logger.warning("numpy not available, using simpler SVG processing")
                # Fallback without numpy
                png_data = cairosvg.svg2png(
                    url=svg_path,
                    output_width=size,
                    output_height=size,
                    background_color='white'
                )
                logo = Image.open(BytesIO(png_data))
                if logo.mode != 'L':
                    logo = logo.convert('L')
                logo = logo.convert('1')
                return logo
            else:
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
        Process bitmap logo for e-paper display with improved weather icon handling
        
        Args:
            logo (PIL.Image): Input logo image
            size (int): Desired size
            
        Returns:
            PIL.Image: Processed logo
        """
        # Handle RGBA images (like OpenWeatherMap icons) with transparency
        if logo.mode == 'RGBA':
            # Create white background
            background = Image.new('RGB', logo.size, (255, 255, 255))
            # Composite logo onto white background using alpha channel
            background.paste(logo, mask=logo.split()[-1])
            logo = background
        
        # Convert to grayscale if needed
        if logo.mode != 'L':
            logo = logo.convert('L')
        
        # Resize to desired size while maintaining aspect ratio
        logo.thumbnail((size, size), Image.Resampling.LANCZOS)
        
        # Apply contrast enhancement for better e-paper visibility
        try:
            import numpy as np
            # Convert to numpy array for processing
            logo_array = np.array(logo)
            
            # Use adaptive thresholding for weather icons
            # Check if image has sufficient contrast before applying high threshold
            min_val, max_val = logo_array.min(), logo_array.max()
            contrast = max_val - min_val
            
            if contrast > 100:  # Good contrast - use moderate threshold
                threshold = 128  # Standard threshold
            else:  # Low contrast - use lower threshold to preserve details
                threshold = 100  # Lower threshold for subtle icons
                
            self.logger.debug(f"Weather icon contrast: {contrast}, using threshold: {threshold}")
            logo_array = np.where(logo_array < threshold, 0, 255).astype(np.uint8)
            logo = Image.fromarray(logo_array, mode='L')
            
            # Convert to 1-bit monochrome without dithering for cleaner weather icons
            logo = logo.convert('1')
            
        except ImportError:
            # Fallback without numpy - use PIL's built-in conversion with adaptive threshold
            # First, try to determine if we need a lower threshold
            extrema = logo.getextrema()
            contrast = extrema[1] - extrema[0] if extrema[1] is not None else 0
            
            if contrast > 100:
                threshold = 128  # Standard threshold
            else:
                threshold = 100  # Lower threshold for subtle icons
                
            self.logger.debug(f"Weather icon contrast (fallback): {contrast}, using threshold: {threshold}")
            # Apply point transformation for better contrast
            logo = logo.point(lambda x: 0 if x < threshold else 255, mode='L')
            logo = logo.convert('1')
        
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
    
    def _draw_weather_fallback(self, draw, x, y, size=35):
        """
        Draw a simple weather fallback icon (cloud shape)
        
        Args:
            draw: PIL ImageDraw object
            x (int): X position for icon center
            y (int): Y position for icon center
            size (int): Size of the icon
        """
        # Draw a simple cloud shape
        half_size = size // 2
        
        # Main cloud body (ellipse)
        draw.ellipse(
            [(x - half_size + 5, y - half_size // 2), 
             (x + half_size - 5, y + half_size // 2)], 
            outline=0, width=2
        )
        
        # Cloud bumps (smaller circles)
        bump_size = size // 4
        draw.ellipse(
            [(x - half_size, y - bump_size), 
             (x - half_size + bump_size * 2, y + bump_size)], 
            outline=0, width=1
        )
        draw.ellipse(
            [(x + half_size - bump_size * 2, y - bump_size), 
             (x + half_size, y + bump_size)], 
            outline=0, width=1
        )
    
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
                display_result = display_function(rates_data)
                
                # Handle different display formats
                if title == "Weather" and isinstance(display_result, dict):
                    # New weather layout with separate left and right sections
                    left_lines = display_result.get('left_lines', [])
                    right_details = display_result.get('right_details', [])
                    
                    # Draw left side lines (main weather info)
                    y_pos = 35
                    for line in left_lines[:2]:  # Max 2 lines on left
                        draw.text((10, y_pos), line, font=font_small, fill=0)
                        y_pos += 15
                    
                    # Draw right side details (below weather icon)
                    if right_details:
                        right_x = self.width - 85  # Position for right-aligned text
                        right_y = 65  # Start below the weather icon
                        
                        for detail in right_details[:3]:  # Max 3 detail lines
                            # Right-align the text by calculating text width
                            bbox = draw.textbbox((0, 0), detail, font=font_small)
                            text_width = bbox[2] - bbox[0]
                            actual_x = self.width - text_width - 10  # 10px margin from right edge
                            
                            draw.text((actual_x, right_y), detail, font=font_small, fill=0)
                            right_y += 12  # Tighter spacing for right side details
                            
                else:
                    # Traditional layout for non-weather screens (backward compatibility)
                    lines = display_result if isinstance(display_result, list) else []
                    y_pos = 35
                    
                    # Determine max lines based on screen type
                    max_lines = 4 if title == "Weather" else 2
                    line_spacing = 15 if title == "Weather" else 20
                    font_to_use = font_small if title == "Weather" else font_medium
                    
                    for line in lines[:max_lines]:
                        draw.text((10, y_pos), line, font=font_to_use, fill=0)
                        y_pos += line_spacing
            
            # Draw logo/icon if requested
            if show_logo:
                # Adjust logo position based on screen type
                if title == "Weather":
                    logo_x = self.width - 40  # 40 pixels from right edge
                    logo_y = 45  # Higher position for weather due to more text
                elif logo_type == 'btc':
                    # Bitcoin logo in bottom right corner to avoid text overlap
                    logo_x = self.width - 25  # 25 pixels from right edge
                    logo_y = self.height - 25  # 25 pixels from bottom edge
                else:
                    logo_x = self.width - 40  # Default position
                    logo_y = 50
                
                if logo_type == 'btc':
                    # Bitcoin logo
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
                
                elif logo_type == 'weather':
                    # Weather icon
                    icon_filename = screen_data.get('weather_icon_filename')
                    if icon_filename:
                        self.logger.info(f"Loading weather icon: {icon_filename}")
                        weather_icon = self.load_weather_icon(icon_filename, size=35)
                        
                        if weather_icon:
                            # Calculate position for pasting (top-left corner)
                            paste_x = logo_x - weather_icon.width // 2
                            paste_y = logo_y - weather_icon.height // 2
                            
                            # Paste the weather icon onto the main image
                            image.paste(weather_icon, (paste_x, paste_y))
                            self.logger.info(f"✓ Weather icon {icon_filename} displayed at ({paste_x}, {paste_y})")
                        else:
                            # Draw a simple weather fallback (cloud shape)
                            self._draw_weather_fallback(draw, logo_x, logo_y)
                            self.logger.warning(f"⚠ Weather icon {icon_filename} failed to load, using fallback cloud icon")
                    else:
                        # No icon filename provided
                        self._draw_weather_fallback(draw, logo_x, logo_y)
                        self.logger.warning("⚠ No weather icon filename provided, using fallback cloud icon")
            
            # Data timestamp in bottom left corner (skip for clock screen since it shows current time)
            title = screen_data.get('title', '')
            if title != 'Clock':
                data_timestamp = rates_data.get('timestamp', 'N/A')
                time_text = f"Data: {data_timestamp}"
                # Position timestamp at bottom left corner
                timestamp_y = self.height - 15  # 15 pixels from bottom
                draw.text((5, timestamp_y), time_text, font=font_small, fill=0)
            
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
        """Initialize the e-paper display with partial refresh capability"""
        if not self.simulation_mode:
            try:
                # Initial full refresh to clear the display
                self.epd.init()
                self.epd.Clear(0xFF)
                self.logger.info("E-paper display initialized and cleared")
                
                # Reset partial refresh state
                self.partial_refresh_initialized = False
                self.last_screen_number = None
                self.base_image = None
                self.current_cycle = 0
                self.refresh_count = 0
                self.logger.info("Partial refresh mode ready - ultra-smooth transitions!")
            except Exception as e:
                self.logger.error(f"Failed to initialize display: {e}")
                raise
    
    def display_image(self, image, filename="currency_display_simulation.png"):
        """
        Display image on e-paper display or save to file in simulation mode
        Uses fast refresh to eliminate blinking, with periodic full refresh to prevent ghosting
        
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
                self.refresh_count += 1
                
                # Do a full refresh every 20 displays to prevent ghosting
                if self.refresh_count % 20 == 0:
                    self.logger.info(f"Performing full refresh #{self.refresh_count//20} to prevent ghosting")
                    self.epd.init()
                    self.epd.display(self.epd.getbuffer(image))
                    # Re-initialize fast mode
                    self.epd.init_fast()
                    self.fast_refresh_initialized = True
                else:
                    # Use fast refresh for smooth transitions (no blinking)
                    if not self.fast_refresh_initialized:
                        self.epd.init_fast()
                        self.fast_refresh_initialized = True
                    
                    self.epd.display_fast(self.epd.getbuffer(image))
                    self.logger.debug(f"Fast refresh #{self.refresh_count} - no blinking")
                    
            except Exception as e:
                self.logger.error(f"Failed to display image: {e}")
                raise
    
    def display_screen_with_smart_refresh(self, screen_data):
        """
        Create and display screen with intelligent refresh strategy:
        - Partial refresh between screens (no blinking)
        - Full refresh after complete cycle (clean display)
        """
        if not screen_data:
            return
        
        # Create the image
        image = self.create_display_image(screen_data)
        
        # Get screen cycle information
        screen_num = screen_data.get('screen_number', 1)
        total_screens = screen_data.get('total_screens', 1)
        
        if self.simulation_mode:
            # Simulation mode - just save the image
            filename = f"screen_{screen_num}_of_{total_screens}.png"
            image.save(filename)
            self.logger.info(f"Display simulation saved to {filename}")
            
            # Simulate cycle detection BEFORE updating last_screen_number
            cycle_completed = (self.last_screen_number is not None and 
                              screen_num == 1 and 
                              self.last_screen_number == total_screens)
            if cycle_completed:
                self.current_cycle += 1
                self.logger.info(f"🔄 [SIMULATION] Cycle {self.current_cycle} completed")
            
            # Track screen numbers even in simulation mode for testing
            self.last_screen_number = screen_num
            self.refresh_count += 1
            return
        
        try:
            # Detect if we've completed a full cycle
            cycle_completed = (self.last_screen_number is not None and 
                              screen_num == 1 and 
                              self.last_screen_number == total_screens)
            
            if cycle_completed:
                self.current_cycle += 1
                self.logger.info(f"🔄 Cycle {self.current_cycle} completed - performing full refresh")
                
                # Full refresh to maintain display quality
                self.epd.init()
                self.epd.display(self.epd.getbuffer(image))
                
                # Set this as the new base image for partial updates
                self.base_image = image.copy()
                self.epd.displayPartBaseImage(self.epd.getbuffer(self.base_image))
                self.partial_refresh_initialized = True
                
            elif not self.partial_refresh_initialized or self.base_image is None:
                # First display or need to initialize partial refresh
                self.logger.info("🚀 Initializing partial refresh mode")
                self.epd.init()
                self.epd.display(self.epd.getbuffer(image))
                
                # Set as base image for partial updates
                self.base_image = image.copy()
                self.epd.displayPartBaseImage(self.epd.getbuffer(self.base_image))
                self.partial_refresh_initialized = True
                
            else:
                # Partial refresh - only update changed parts (super smooth!)
                self.logger.debug(f"⚡ Partial refresh: Screen {screen_num}/{total_screens} - no blinking")
                self.epd.displayPartial(self.epd.getbuffer(image))
            
            self.last_screen_number = screen_num
            self.refresh_count += 1
            
        except Exception as e:
            self.logger.error(f"Failed to display screen with smart refresh: {e}")
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