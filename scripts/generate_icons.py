import os
from PIL import Image, ImageDraw, ImageFont

def create_paisa_pilot_icon(size=512):
    # Create canvas with RGBA
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Scale factor
    scale = size / 40.0
    
    # Draw rounded rectangle (coral tile)
    # Gradient approximation with subtle vertical steps
    top_color = (255, 90, 95, 255)    # #FF5A5F
    bot_color = (255, 123, 107, 255)  # #FF7B6B
    
    # Draw base rounded rect
    corner_radius = int(12 * scale)
    draw.rounded_rectangle([0, 0, size, size], radius=corner_radius, fill=top_color)
    
    # Add subtle gradient overlay
    for y in range(size):
        factor = y / float(size)
        r = int(top_color[0] + (bot_color[0] - top_color[0]) * factor)
        g = int(top_color[1] + (bot_color[1] - top_color[1]) * factor)
        b = int(top_color[2] + (bot_color[2] - top_color[2]) * factor)
        # Apply within the rounded bounds
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))
        
    # Re-apply alpha mask for rounded corners
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, size, size], radius=corner_radius, fill=255)
    img.putalpha(mask)
    
    # Now draw the wings and Rupee symbol
    draw = ImageDraw.Draw(img)
    wing_color = (255, 255, 255, int(255 * 0.75))
    symbol_color = (255, 255, 255, 255)
    
    wing_width = max(1, int(2.4 * scale))
    symbol_width = max(2, int(2.8 * scale))
    
    # Wings left
    # <path d="M5 11l7 5" />
    draw.line([(5 * scale, 11 * scale), (12 * scale, 16 * scale)], fill=wing_color, width=wing_width)
    # <path d="M4 19l8 2" />
    draw.line([(4 * scale, 19 * scale), (12 * scale, 21 * scale)], fill=wing_color, width=wing_width)
    # <path d="M7 27h5" />
    draw.line([(7 * scale, 27 * scale), (12 * scale, 27 * scale)], fill=wing_color, width=wing_width)
    
    # Wings right
    # <path d="M35 11l-7 5" />
    draw.line([(35 * scale, 11 * scale), (28 * scale, 16 * scale)], fill=wing_color, width=wing_width)
    # <path d="M36 19l-8 2" />
    draw.line([(36 * scale, 19 * scale), (28 * scale, 21 * scale)], fill=wing_color, width=wing_width)
    # <path d="M33 27h-5" />
    draw.line([(33 * scale, 27 * scale), (28 * scale, 27 * scale)], fill=wing_color, width=wing_width)
    
    # Rupee Symbol:
    # Top horizontal bar: M14 12h12
    draw.line([(14 * scale, 12 * scale), (26 * scale, 12 * scale)], fill=symbol_color, width=symbol_width)
    # Second horizontal bar: M14 17h12
    draw.line([(14 * scale, 17 * scale), (26 * scale, 17 * scale)], fill=symbol_color, width=symbol_width)
    # Vertical spine: M14 12 to 14 22
    draw.line([(14 * scale, 12 * scale), (14 * scale, 22 * scale)], fill=symbol_color, width=symbol_width)
    # Top curve / arc: from (14, 12) to (19, 12), curve to (19, 22), to (14, 22)
    # Bounding box for arc: x from (19 - 5 = 14) to (19 + 5 = 24), y from 12 to 22
    arc_box = [(14 * scale, 12 * scale), (24 * scale, 22 * scale)]
    draw.arc(arc_box, start=270, end=90, fill=symbol_color, width=symbol_width)
    draw.line([(14 * scale, 12 * scale), (19 * scale, 12 * scale)], fill=symbol_color, width=symbol_width)
    draw.line([(14 * scale, 22 * scale), (19 * scale, 22 * scale)], fill=symbol_color, width=symbol_width)
    # Downward slash: M15 22l9 10
    draw.line([(15 * scale, 22 * scale), (24 * scale, 32 * scale)], fill=symbol_color, width=symbol_width)
    
    return img

def create_round_icon(base_img):
    size = base_img.size[0]
    img = base_img.copy()
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([0, 0, size, size], fill=255)
    img.putalpha(mask)
    return img

def create_foreground_icon(size=432):
    # Android adaptive foreground (icon centered in a transparent 108dp canvas)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # Icon sits in central 72dp (approx 66% of canvas)
    inner_size = int(size * 0.66)
    offset = (size - inner_size) // 2
    inner_icon = create_paisa_pilot_icon(inner_size)
    img.paste(inner_icon, (offset, offset), inner_icon)
    return img

if __name__ == "__main__":
    res_dir = "web/android/app/src/main/res"
    
    sizes = {
        "mipmap-mdpi": (48, 108),
        "mipmap-hdpi": (72, 162),
        "mipmap-xhdpi": (96, 216),
        "mipmap-xxhdpi": (144, 324),
        "mipmap-xxxhdpi": (192, 432)
    }
    
    for folder, (sq_size, fg_size) in sizes.items():
        folder_path = os.path.join(res_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        
        # 1. Square launcher icon
        sq_img = create_paisa_pilot_icon(sq_size)
        sq_img.save(os.path.join(folder_path, "ic_launcher.png"), "PNG")
        
        # 2. Round launcher icon
        rd_img = create_round_icon(sq_img)
        rd_img.save(os.path.join(folder_path, "ic_launcher_round.png"), "PNG")
        
        # 3. Adaptive foreground icon
        fg_img = create_foreground_icon(fg_size)
        fg_img.save(os.path.join(folder_path, "ic_launcher_foreground.png"), "PNG")
        
        print(f"Generated icons for {folder}: {sq_size}x{sq_size}, fg {fg_size}x{fg_size}")
        
    print("All Android launcher icons successfully updated!")
