import os
from PIL import Image

# Source image path
source_image_path = r"C:/Users/Administrator/.gemini/antigravity/brain/0e4deb16-13e5-4c5b-bb99-08317514d21b/ech_workers_icon_text_1765496943819.png"
# Target directory
target_dir = r"c:\Users\Administrator\Desktop\ech-ipa\swift-ios\Assets.xcassets\AppIcon.appiconset"

# Ensure target directory exists
os.makedirs(target_dir, exist_ok=True)

# Define sizes
sizes = {
    "Icon-60@2x.png": (120, 120),
    "Icon-60@3x.png": (180, 180),
    "Icon-76.png": (76, 76),
    "Icon-76@2x.png": (152, 152),
    "Icon-83.5@2x.png": (167, 167),
    "Icon-1024.png": (1024, 1024)
}

try:
    with Image.open(source_image_path) as img:
        # Convert to RGBA to ensure transparency support if needed, though icons usually don't have transparency
        img = img.convert("RGBA")
        
        for filename, size in sizes.items():
            resized_img = img.resize(size, Image.Resampling.LANCZOS)
            save_path = os.path.join(target_dir, filename)
            resized_img.save(save_path, "PNG")
            print(f"Saved {filename} ({size})")
            
except Exception as e:
    print(f"Error: {e}")
