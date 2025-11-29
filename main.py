# main.py
import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Try to import the user's watermark utilities module (plural/singular name tolerance)
try:
    import watermarks_utils as wm_utils  # expected: watermarks_utils.py
except Exception:
    try:
        import watermark_utils as wm_utils  # fallback in case of different name
    except Exception:
        wm_utils = None

# Setup app
app = FastAPI(title="Watermark Robustness Backend")

# Allow local frontend to call APIs during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = Path(__file__).parent
# If the utils module defines UPLOAD_DIR, use it; otherwise create a local uploads dir
if wm_utils and hasattr(wm_utils, "UPLOAD_DIR"):
    UPLOAD_DIR = Path(wm_utils.UPLOAD_DIR)
else:
    UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Serve frontend static files (index.html, script.js, styles.css are in the same directory)
app.mount("/", StaticFiles(directory=str(BASE_DIR), html=True), name="frontend")


def _secure_filename(name: str) -> str:
    """Return basename to avoid directory traversal."""
    return Path(name).name


@app.post("/upload/")
async def upload_image(file: UploadFile = File(...)):
    """
    Save uploaded file to uploads/ and return the saved filename.
    """
    try:
        safe_name = _secure_filename(file.filename)
        dest = UPLOAD_DIR / safe_name
        # Ensure start of file
        file.file.seek(0)
        with open(dest, "wb") as out:
            shutil.copyfileobj(file.file, out)
        return {"filename": safe_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@app.post("/add-watermark/")
async def add_watermark(
    filename: str = Form(...),
    text: str = Form("SAMPLE"),
    opacity: float = Form(0.25),
    fontsize: int = Form(48),
    scale: Optional[float] = Form(None),
    watermark: Optional[UploadFile] = File(None),
):
    """
    Add either a text watermark (default) or an image watermark (if `watermark` is provided).
    Returns the new filename on success.
    """
    if not wm_utils:
        raise HTTPException(status_code=500, detail="Watermark utilities not available on server.")

    safe_name = _secure_filename(filename)
    inp = UPLOAD_DIR / safe_name
    if not inp.exists():
        raise HTTPException(status_code=404, detail="Input file not found on server.")

    out_name = f"wm_{safe_name}"
    out = UPLOAD_DIR / out_name

    try:
        if watermark:
            # save watermark file temporarily
            wm_name = _secure_filename(watermark.filename or "wm_temp.png")
            wm_path = UPLOAD_DIR / wm_name
            watermark.file.seek(0)
            with open(wm_path, "wb") as wf:
                shutil.copyfileobj(watermark.file, wf)
            # call image watermark function if present
            if hasattr(wm_utils, "add_image_watermark"):
                wm_utils.add_image_watermark(str(inp), str(wm_path), str(out), scale=(scale or 0.18), opacity=opacity)
            else:
                raise HTTPException(status_code=500, detail="add_image_watermark not implemented in utilities.")
            # optional: remove temp watermark file (keep for debug if desired)
            try:
                wm_path.unlink(missing_ok=True)
            except Exception:
                pass
        else:
            if hasattr(wm_utils, "add_text_watermark"):
                wm_utils.add_text_watermark(str(inp), str(out), text=text, opacity=opacity, fontsize=fontsize)
            else:
                raise HTTPException(status_code=500, detail="add_text_watermark not implemented in utilities.")
        return {"watermarked": out_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add watermark: {e}")


@app.post("/edit/")
async def edit(
    filename: str = Form(...),
    op: str = Form(...),
    w: Optional[int] = Form(None),
    h: Optional[int] = Form(None),
    x: Optional[int] = Form(None),
    y: Optional[int] = Form(None),
    crop_w: Optional[int] = Form(None),
    crop_h: Optional[int] = Form(None),
):
    """
    Apply simple edits: resize or crop. Returns edited filename.
    """
    if not wm_utils:
        raise HTTPException(status_code=500, detail="Image utilities not available on server.")

    safe_name = _secure_filename(filename)
    inp = UPLOAD_DIR / safe_name
    if not inp.exists():
        raise HTTPException(status_code=404, detail="Input file not found.")

    out_name = f"edit_{safe_name}"
    out = UPLOAD_DIR / out_name

    resize = None
    crop_box = None

    if op == "resize":
        if not w or not h:
            raise HTTPException(status_code=400, detail="Width and height are required for resize.")
        resize = (int(w), int(h))
    elif op == "crop":
        if x is None or y is None or crop_w is None or crop_h is None:
            raise HTTPException(status_code=400, detail="x, y, crop_w, crop_h required for crop.")
        crop_box = (int(x), int(y), int(x) + int(crop_w), int(y) + int(crop_h))
    else:
        raise HTTPException(status_code=400, detail="Unknown op. Supported: resize, crop.")

    try:
        if hasattr(wm_utils, "edit_image"):
            wm_utils.edit_image(str(inp), str(out), resize=resize, crop_box=crop_box)
        else:
            raise HTTPException(status_code=500, detail="edit_image not implemented in utilities.")
        return {"edited": out_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Edit failed: {e}")


@app.post("/check/")
async def check(filename: str = Form(...), template_filename: str = Form(...)):
    """
    Attempt to detect watermark template inside filename using utilities' detection function.
    Returns JSON detection result (whatever the utility returns).
    """
    if not wm_utils:
        raise HTTPException(status_code=500, detail="Detection utilities not available on server.")

    safe_name = _secure_filename(filename)
    tpl_name = _secure_filename(template_filename)
    img = UPLOAD_DIR / safe_name
    tpl = UPLOAD_DIR / tpl_name
    if not img.exists():
        raise HTTPException(status_code=404, detail="Target image not found.")
    if not tpl.exists():
        raise HTTPException(status_code=404, detail="Template file not found.")

    if not hasattr(wm_utils, "detect_watermark_template"):
        raise HTTPException(status_code=500, detail="detect_watermark_template not implemented in utilities.")

    try:
        # detection function expected to return a JSON-serializable dict
        result = wm_utils.detect_watermark_template(str(img), str(tpl), scales=[0.6, 0.8, 1.0, 1.2, 1.4], threshold=0.7)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {e}")


@app.get("/uploads/{fname}")
def serve_upload(fname: str):
    """Serve an uploaded file back to the frontend (used by <img src="/uploads/<name>">)."""
    safe_name = _secure_filename(fname)
    fp = UPLOAD_DIR / safe_name
    if not fp.exists():
        return JSONResponse(status_code=404, content={"error": "file not found"})
    return FileResponse(fp)


# Run with:
# uvicorn main:app --reload --host 0.0.0.0 --port 8000
