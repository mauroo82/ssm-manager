"""
Generate icon.ico for SSM Manager.
Renders Bootstrap bi-hdd-network-fill SVG via pymupdf (no Cairo required).
Run with: python generate_icon.py
"""

import io
from PIL import Image
import fitz  # pymupdf


# Bootstrap bi-hdd-network-fill path (viewBox 0 0 16 16)
HDD_NETWORK_PATH = (
    "M2 2a2 2 0 0 0-2 2v1a2 2 0 0 0 2 2h5.5v3A1.5 1.5 0 0 0 6 11.5H.5a.5.5 0 0 0 0 1"
    "H6A1.5 1.5 0 0 0 7.5 14h1a1.5 1.5 0 0 0 1.5-1.5H15.5a.5.5 0 0 0 0-1H10A1.5 1.5 0 0 0"
    " 8.5 10V7H14a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H2zm6.5 4.5v1H7v-1h1.5zm2 0v1H9v-1h1.5z"
    "M14 4.5v1H12.5v-1H14zm-8 0v1H4.5v-1H6zm-2 0v1H2.5v-1H4z"
)

NAVY_HEX   = "#1a2332"
ORANGE_HEX = "#FF9900"


def build_svg(size: int) -> str:
    """Build SVG: navy rounded-rect background + orange bi-hdd-network-fill icon."""
    pad   = size * 0.14
    icon_size = size - 2 * pad
    scale = icon_size / 16.0
    r     = size * 0.18

    return f"""<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <rect x="0" y="0" width="{size}" height="{size}"
        rx="{r:.2f}" ry="{r:.2f}" fill="{NAVY_HEX}"/>
  <g transform="translate({pad:.4f},{pad:.4f}) scale({scale:.6f})">
    <path d="{HDD_NETWORK_PATH}" fill="{ORANGE_HEX}"/>
  </g>
</svg>"""


def svg_to_pil(svg_str: str, size: int) -> Image.Image:
    """Render SVG bytes to PIL RGBA Image using pymupdf."""
    svg_bytes = svg_str.encode("utf-8")
    doc = fitz.open(stream=svg_bytes, filetype="svg")
    page = doc[0]

    # Render at 4× then downsample for crisp edges at small sizes
    scale = max(4, 256 // size)
    mat   = fitz.Matrix(scale, scale)
    pix   = page.get_pixmap(matrix=mat, alpha=False)

    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    img = img.resize((size, size), Image.LANCZOS)
    return img.convert("RGBA")


def main():
    sizes  = [16, 24, 32, 48, 64, 128, 256]
    images = []

    for s in sizes:
        img = svg_to_pil(build_svg(s), s)
        images.append(img)
        print(f"  rendered {s}×{s}")

    images[0].save(
        "icon.ico",
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print("icon.ico generated successfully.")

    images[-1].save("ssm-manager-site/img/favicon.png", format="PNG")
    print("ssm-manager-site/img/favicon.png generated.")


if __name__ == "__main__":
    main()
