# watermarks_utils.py
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
import math

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import numpy as np
import cv2

# Configure upload directory used by main.py
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _open_image(path: str) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    return img


def _save_image(img: Image.Image, out_path: str, quality: int = 95):
    # Convert to RGB if output extension is jpg/jpeg
    out = Path(out_path)
    if out.suffix.lower() in {".jpg", ".jpeg"}:
        rgb = img.convert("RGB")
        rgb.save(out_path, quality=quality)
    else:
        img.save(out_path)


def add_text_watermark(
    in_path: str,
    out_path: str,
    text: str = "SAMPLE",
    opacity: float = 0.25,
    fontsize: Optional[int] = None,
    position: str = "bottom_right",
    margin: int = 20,
    tile: bool = False,
):
    """
    Add a text watermark to the image.

    - in_path: source image path
    - out_path: destination image path
    - text: watermark text
    - opacity: 0..1
    - fontsize: if None, computed relative to image size
    - position: 'bottom_right'|'center'|'top_left' etc.
    - tile: if True, tile watermark across image
    """
    img = _open_image(in_path)
    w, h = img.size

    # choose font size relative to image if not given
    if fontsize is None:
        fontsize = max(12, int(min(w, h) * 0.05))

    try:
        # try a common system font first; fallback to default PIL font
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", fontsize)
    except Exception:
        font = ImageFont.load_default()

    # create watermark layer
    txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)

    text_w, text_h = draw.textsize(text, font=font)

    def _pos_coords(pos: str, tw: int, th: int) -> Tuple[int, int]:
        pos = pos.lower()
        if pos == "center":
            return ((w - tw) // 2, (h - th) // 2)
        if pos == "top_left":
            return (margin, margin)
        if pos == "top_right":
            return (w - tw - margin, margin)
        if pos == "bottom_left":
            return (margin, h - th - margin)
        # default bottom_right
        return (w - tw - margin, h - th - margin)

    if tile:
        # tile watermark across the image spaced by margin
        x = margin
        y = margin
        step_x = text_w + margin
        step_y = text_h + margin
        while y < h:
            while x < w:
                draw.text((x, y), text, font=font, fill=(255, 255, 255, int(255 * opacity)))
                x += step_x
            x = margin
            y += step_y
    else:
        x, y = _pos_coords(position, text_w, text_h)
        draw.text((x, y), text, font=font, fill=(255, 255, 255, int(255 * opacity)))

    # composite watermark onto original
    combined = Image.alpha_composite(img, txt_layer)
    _save_image(combined, out_path)


def add_image_watermark(
    in_path: str,
    watermark_path: str,
    out_path: str,
    scale: float = 0.18,
    opacity: float = 0.25,
    position: str = "bottom_right",
    margin: int = 20,
    tile: bool = False,
):
    """
    Add an image watermark (PNG/JPG) onto the input image.

    - scale: watermark size relative to shorter side of image (e.g., 0.18)
    - opacity: 0..1
    - position: where to place single watermark
    - tile: if True, tile watermark across image
    """
    base = _open_image(in_path)
    w, h = base.size

    wm = Image.open(watermark_path).convert("RGBA")
    # compute target size keeping aspect ratio
    short_side = min(w, h)
    target_w = int(short_side * scale)
    if wm.width == 0:
        raise ValueError("Watermark image has zero width.")
    target_h = int(wm.height * (target_w / wm.width))
    wm_resized = wm.resize((target_w, target_h), Image.LANCZOS)

    # apply opacity to the watermark
    if opacity < 1.0:
        alpha = wm_resized.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
        wm_resized.putalpha(alpha)

    # create layer
    layer = Image.new("RGBA", base.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(layer)

    def _pos_coords(pos: str, tw: int, th: int) -> Tuple[int, int]:
        pos = pos.lower()
        if pos == "center":
            return ((w - tw) // 2, (h - th) // 2)
        if pos == "top_left":
            return (margin, margin)
        if pos == "top_right":
            return (w - tw - margin, margin)
        if pos == "bottom_left":
            return (margin, h - th - margin)
        # default bottom_right
        return (w - tw - margin, h - th - margin)

    if tile:
        # tile watermark across the image
        step_x = wm_resized.width + margin
        step_y = wm_resized.height + margin
        y = margin
        while y < h:
            x = margin
            while x < w:
                layer.paste(wm_resized, (x, y), wm_resized)
                x += step_x
            y += step_y
    else:
        x, y = _pos_coords(position, wm_resized.width, wm_resized.height)
        layer.paste(wm_resized, (x, y), wm_resized)

    combined = Image.alpha_composite(base, layer)
    _save_image(combined, out_path)


def edit_image(in_path: str, out_path: str, resize: Optional[Tuple[int, int]] = None, crop_box: Optional[Tuple[int, int, int, int]] = None):
    """
    Simple image edit: supports resize or crop or both.
    - resize: (width, height)
    - crop_box: (left, top, right, bottom)
    """
    img = Image.open(in_path)
    if crop_box:
        img = img.crop(crop_box)
    if resize:
        img = img.resize((int(resize[0]), int(resize[1])), Image.LANCZOS)
    _save_image(img, out_path)


def _pillow_to_cv2_rgba(pil_img: Image.Image) -> np.ndarray:
    arr = np.array(pil_img)
    # PIL uses RGBA order; convert to BGRA for OpenCV
    if arr.shape[2] == 4:
        arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA)
    else:
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    return arr


def detect_watermark_template(
    image_path: str,
    template_path: str,
    scales: Optional[List[float]] = None,
    threshold: float = 0.7,
    method=cv2.TM_CCOEFF_NORMED,
) -> Dict[str, Any]:
    """
    Try to locate `template_path` inside `image_path` using multi-scale template matching.

    Returns a dict:
      {
        "best": {
           "scale": <float>,
           "score": <float>,
           "top_left": [x,y],
           "bottom_right": [x,y]
        },
        "matches": [
           {"scale":..., "score":..., "top_left":[x,y], "bottom_right":[x,y]},
           ...
        ],
        "template_size": [w,h],
        "image_size": [w,h]
      }

    `scales` is a list of scale multipliers applied to the template (1.0 means original template size).
    """
    if scales is None:
        scales = [0.6, 0.8, 1.0, 1.2, 1.4]

    # load images as grayscale for template matching
    img_cv = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    tpl_cv_full = cv2.imdecode(np.fromfile(template_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)

    if img_cv is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    if tpl_cv_full is None:
        raise FileNotFoundError(f"Could not read template: {template_path}")

    img_gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    # template to gray (if has alpha channel ignore alpha for matching)
    if tpl_cv_full.ndim == 3 and tpl_cv_full.shape[2] == 4:
        tpl_bgr = cv2.cvtColor(tpl_cv_full, cv2.COLOR_BGRA2BGR)
        tpl_gray_full = cv2.cvtColor(tpl_bgr, cv2.COLOR_BGR2GRAY)
    else:
        tpl_gray_full = cv2.cvtColor(tpl_cv_full, cv2.COLOR_BGR2GRAY) if tpl_cv_full.ndim == 3 else tpl_cv_full

    ih, iw = img_gray.shape[:2]

    matches = []
    best = {"score": -1.0}

    for scale in scales:
        # compute new size for template
        th, tw = tpl_gray_full.shape[:2]
        new_w = int(tw * scale)
        new_h = int(th * scale)
        if new_w < 8 or new_h < 8:
            # too small to match reliably
            continue
        if new_w > iw or new_h > ih:
            # template larger than image at this scale; skip
            continue

        tpl_resized = cv2.resize(tpl_gray_full, (new_w, new_h), interpolation=cv2.INTER_AREA)
        # match
        try:
            res = cv2.matchTemplate(img_gray, tpl_resized, method)
        except Exception as e:
            continue

        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        # For TM_CCOEFF_NORMED higher is better; for some other methods lower is better.
        score = max_val if method in (cv2.TM_CCOEFF, cv2.TM_CCOEFF_NORMED, cv2.TM_CCORR, cv2.TM_CCORR_NORMED) else (1.0 - min_val)

        top_left = (int(max_loc[0]), int(max_loc[1]))
        bottom_right = (top_left[0] + new_w, top_left[1] + new_h)

        entry = {
            "scale": float(scale),
            "score": float(score),
            "top_left": [int(top_left[0]), int(top_left[1])],
            "bottom_right": [int(bottom_right[0]), int(bottom_right[1])],
            "template_size": [int(new_w), int(new_h)],
        }
        matches.append(entry)

        if score > best.get("score", -1):
            best = entry

    # sort matches by descending score
    matches = sorted(matches, key=lambda x: x["score"], reverse=True)

    # filter by threshold for convenience
    good = [m for m in matches if m["score"] >= threshold]

    result = {
        "best": best if best.get("score", -1) >= 0 else None,
        "matches": matches,
        "good_matches": good,
        "template_size_original": [int(tpl_gray_full.shape[1]), int(tpl_gray_full.shape[0])],
        "image_size": [int(iw), int(ih)],
    }
    return result


if __name__ == "__main__":
    # quick local test (not executed by main.py) - example usage:
    print("watermarks_utils module loaded. UPLOAD_DIR =", UPLOAD_DIR)
