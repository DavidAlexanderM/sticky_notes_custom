"""
generate_app_icon.py - Generates multi-resolution Windows .ico for Sticky Notes.
Draws a modern rounded notepad card with a folded corner and note lines.
"""

from pathlib import Path
from PIL import Image, ImageDraw

def create_sticky_icon() -> Path:
    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    ico_path = assets_dir / "icon.ico"

    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = []

    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        padding = max(1, int(size * 0.08))
        x0, y0 = padding, padding
        x1, y1 = size - padding, size - padding
        corner_r = max(2, int(size * 0.12))

        # Main note body (warm vibrant amber/yellow)
        card_bg = (255, 213, 79, 255)      # Material Amber 300
        card_border = (255, 179, 0, 255)   # Material Amber 600
        fold_bg = (255, 236, 179, 255)     # Lighter fold
        line_color = (191, 134, 0, 200)    # Amber lines

        # Draw rounded rectangle for base note
        draw.rounded_rectangle([x0, y0, x1, y1], radius=corner_r, fill=card_bg, outline=card_border, width=max(1, int(size * 0.03)))

        # Draw folded top-right corner if size is large enough
        if size >= 24:
            fold_size = int((x1 - x0) * 0.3)
            fx = x1 - fold_size
            fy = y0 + fold_size
            # Fold triangle
            draw.polygon([(fx, y0), (x1, fy), (fx, fy)], fill=fold_bg, outline=card_border)

        # Draw note lines
        if size >= 32:
            num_lines = 3
            line_start_y = int(y0 + (y1 - y0) * 0.45)
            line_spacing = int((y1 - line_start_y) / (num_lines + 1))
            line_x0 = int(x0 + (x1 - x0) * 0.2)
            line_x1 = int(x1 - (x1 - x0) * 0.2)
            line_w = max(1, int(size * 0.03))

            for i in range(num_lines):
                ly = line_start_y + i * line_spacing
                draw.line([(line_x0, ly), (line_x1, ly)], fill=line_color, width=line_w)

        images.append(img)

    # Save multi-size ICO
    images[-1].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1]
    )

    # Save high-resolution PNG for Qt & cross-platform fallbacks
    png_path = assets_dir / "icon.png"
    images[-1].save(png_path, format="PNG")

    print(f"[OK] Generated Windows icon: {ico_path} (Sizes: {sizes})")
    print(f"[OK] Generated High-DPI icon PNG: {png_path}")
    return ico_path

if __name__ == "__main__":
    create_sticky_icon()
