#!/usr/bin/python
# -*- coding:utf-8 -*-
"""
Script to create a simple Bitcoin logo for e-paper display
"""
from PIL import Image, ImageDraw
import os

def create_btc_logo(size=40):
    """
    Create a simple Bitcoin logo using PIL drawing
    
    Args:
        size (int): Size of the logo (width and height)
        
    Returns:
        PIL.Image: Bitcoin logo image
    """
    # Create a new image with white background
    image = Image.new('1', (size, size), 255)
    draw = ImageDraw.Draw(image)
    
    # Draw outer circle
    circle_margin = 2
    draw.ellipse(
        [(circle_margin, circle_margin), 
         (size - circle_margin, size - circle_margin)], 
        outline=0, width=2
    )
    
    # Draw the "B" shape - simplified Bitcoin symbol
    # Vertical line on the left
    left_x = size // 4
    top_y = size // 4
    bottom_y = size * 3 // 4
    
    # Main vertical line
    draw.line([(left_x, top_y), (left_x, bottom_y)], fill=0, width=2)
    
    # Top horizontal line
    draw.line([(left_x, top_y), (left_x + size // 3, top_y)], fill=0, width=2)
    
    # Middle horizontal line
    middle_y = size // 2
    draw.line([(left_x, middle_y), (left_x + size // 3, middle_y)], fill=0, width=2)
    
    # Bottom horizontal line
    draw.line([(left_x, bottom_y), (left_x + size // 3, bottom_y)], fill=0, width=2)
    
    # Top arc
    arc_right = left_x + size // 3
    draw.arc(
        [(left_x, top_y), (arc_right + 8, middle_y)], 
        start=-90, end=90, fill=0, width=2
    )
    
    # Bottom arc
    draw.arc(
        [(left_x, middle_y), (arc_right + 8, bottom_y)], 
        start=-90, end=90, fill=0, width=2
    )
    
    # Add the vertical lines through the B (currency symbol style)
    currency_left = left_x - 4
    currency_right = arc_right + 4
    currency_top = top_y - 4
    currency_bottom = bottom_y + 4
    
    # Left currency line
    draw.line([(currency_left, currency_top), (currency_left, currency_bottom)], fill=0, width=1)
    # Right currency line  
    draw.line([(currency_right, currency_top), (currency_right, currency_bottom)], fill=0, width=1)
    
    return image

def create_simple_btc_logo(size=40):
    """
    Create an even simpler Bitcoin logo - just a circle with "₿"
    
    Args:
        size (int): Size of the logo
        
    Returns:
        PIL.Image: Simple Bitcoin logo
    """
    image = Image.new('1', (size, size), 255)
    draw = ImageDraw.Draw(image)
    
    # Draw circle
    margin = 2
    draw.ellipse(
        [(margin, margin), (size - margin, size - margin)], 
        outline=0, width=2
    )
    
    # Draw a simple "B" in the center
    center_x = size // 2
    center_y = size // 2
    
    # Simplified "B" using rectangles
    b_width = size // 3
    b_height = size // 2
    b_left = center_x - b_width // 2
    b_top = center_y - b_height // 2
    b_right = b_left + b_width
    b_bottom = b_top + b_height
    b_middle = center_y
    
    # Vertical line
    draw.line([(b_left, b_top), (b_left, b_bottom)], fill=0, width=2)
    
    # Horizontal lines
    draw.line([(b_left, b_top), (b_right - 4, b_top)], fill=0, width=2)
    draw.line([(b_left, b_middle), (b_right - 2, b_middle)], fill=0, width=2)
    draw.line([(b_left, b_bottom), (b_right - 4, b_bottom)], fill=0, width=2)
    
    # Currency lines
    draw.line([(center_x - 2, b_top - 6), (center_x - 2, b_bottom + 6)], fill=0, width=1)
    draw.line([(center_x + 2, b_top - 6), (center_x + 2, b_bottom + 6)], fill=0, width=1)
    
    return image

if __name__ == "__main__":
    # Create assets directory if it doesn't exist
    assets_dir = os.path.dirname(__file__)
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir)
    
    # Create and save different sizes
    sizes = [30, 40, 50]
    
    for size in sizes:
        # Create detailed logo
        logo = create_btc_logo(size)
        logo.save(os.path.join(assets_dir, f'btc_logo_{size}.png'))
        
        # Create simple logo
        simple_logo = create_simple_btc_logo(size)
        simple_logo.save(os.path.join(assets_dir, f'btc_logo_simple_{size}.png'))
    
    print("Bitcoin logos created in assets/ directory")
    print("Available sizes: 30x30, 40x40, 50x50")
    print("Two styles: detailed and simple")