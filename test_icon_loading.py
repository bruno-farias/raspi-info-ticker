#!/usr/bin/python3
"""
Test weather icon loading to debug why it's not showing
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from services.display_service import DisplayService
from PIL import Image

def test_icon_loading():
    print("=== Testing Weather Icon Loading ===\n")
    
    # Initialize display service
    display_service = DisplayService(simulation_mode=True)
    
    # Test loading a weather icon that should exist
    test_icons = ['01d@2x.svg', '02d@2x.svg', '03d@2x.svg', '10d@2x.svg']
    
    for icon_filename in test_icons:
        print(f"Testing: {icon_filename}")
        
        # Check if file exists
        assets_dir = os.path.join(os.path.dirname(__file__), 'assets', 'weather')
        icon_path = os.path.join(assets_dir, icon_filename)
        print(f"  Path: {icon_path}")
        print(f"  Exists: {os.path.exists(icon_path)}")
        
        if os.path.exists(icon_path):
            # Try to load with our function
            try:
                icon = display_service.load_weather_icon(icon_filename, size=35)
                if icon:
                    print(f"  ✓ Loaded successfully")
                    print(f"    Size: {icon.size}")
                    print(f"    Mode: {icon.mode}")
                    
                    # Check if the icon is not completely white
                    extrema = icon.getextrema()
                    print(f"    Pixel range: {extrema}")
                    
                    # Save a test version
                    test_filename = f"test_{icon_filename}"
                    icon.save(test_filename)
                    print(f"    Saved as: {test_filename}")
                else:
                    print(f"  ✗ Failed to load (returned None)")
            except Exception as e:
                print(f"  ✗ Error loading: {e}")
                import traceback
                traceback.print_exc()
        print()

if __name__ == "__main__":
    test_icon_loading()
