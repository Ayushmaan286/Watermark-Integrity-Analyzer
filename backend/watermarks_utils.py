from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
import os


UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)




def add_text_watermark(input_path: str, output_path: str, text: str = "SAMPLE", opacity: float = 0.25, fontsize: int = 48, position: tuple | None = None):
"""Add a semi-transparent text watermark using PIL."""
base = Image.open(input_path).convert("RGBA")
txt = Image.new('RGBA', base.size, (255,255,255,0))


draw = ImageDraw.Draw(txt)
try:
font = ImageFont.truetype("arial.ttf", fontsize)
except Exception:
font = ImageFont.load_default()


w, h = base.size
if position is None:
# bottom-right with margin
position = (w - fontsize * len(text) // 2 - 20, h - fontsize - 20)


# RGBA alpha (0-255)
alpha = int(255 * opacity)
draw.text(position, text, fill=(255,255,255,alpha), font=font)


combined = Image.alpha_composite(base, txt)
combined = combined.convert('RGB')
combined.save(output_path)
return output_path




def add_image_watermark(input_path: str, watermark_path: str, output_path: str, scale: float = 0.2, opacity: float = 0.5, position: tuple | None = None):
base = Image.open(input_path).convert('RGBA')
watermark = Image.open(watermark_path).convert('RGBA')


# resize watermark
bw, bh = base.size
ww = int(bw * scale)
aspect = watermark.width / watermark.height
watermark = watermark.resize((ww, int(ww / aspect)), Image.ANTIALIAS)


if position is None:
position = (bw - watermark.width - 20, bh - watermark.height - 20)


# adjust alpha
alpha = watermark.split()[3]
alpha = alpha.point(lambda p: int(p * opacity))
watermark.putalpha(alpha)


layer = Image.new('RGBA', base.size, (0,0,0,0))
layer.paste(watermark, position, watermark)
combined = Image.alpha_composite(base, layer).convert('RGB')
combined.save(output_path)
return output_path




# --- Detection: simple template matching over multiple scales ---


return output_path