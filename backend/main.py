import os
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import shutil
from pathlib import Path
from watermark_utils import add_text_watermark, add_image_watermark, detect_watermark_template, edit_image, UPLOAD_DIR


app = FastAPI()


# serve frontend static
FRONTEND_DIR = Path(__file__).parent.parent / 'frontend'
app.mount('/static', StaticFiles(directory=str(FRONTEND_DIR)), name='static')


@app.post('/upload/')
async def upload_image(file: UploadFile = File(...)):
path = UPLOAD_DIR / file.filename
with open(path, 'wb') as f:
shutil.copyfileobj(file.file, f)
return {'filename': file.filename}


@app.post('/add-watermark/')
async def add_watermark(filename: str = Form(...), text: str = Form('SAMPLE')):
inp = UPLOAD_DIR / filename
out_name = f"wm_{filename}"
out = UPLOAD_DIR / out_name
add_text_watermark(str(inp), str(out), text=text, opacity=0.25, fontsize=48)
return {'watermarked': out_name}


@app.post('/edit/')
async def edit(filename: str = Form(...), op: str = Form(...), w: int | None = Form(None), h: int | None = Form(None), x: int | None = Form(None), y: int | None = Form(None), crop_w: int | None = Form(None), crop_h: int | None = Form(None)):
inp = UPLOAD_DIR / filename
out_name = f"edit_{filename}"
out = UPLOAD_DIR / out_name
resize = None
crop = None
if op == 'resize' and w and h:
resize = (w, h)
if op == 'crop' and x is not None and y is not None and crop_w and crop_h:
crop = (x, y, x + crop_w, y + crop_h)
edit_image(str(inp), str(out), resize=resize, crop_box=crop)
return {'edited': out_name}


@app.post('/check/')
async def check(filename: str = Form(...), template_filename: str = Form(...)):
img = UPLOAD_DIR / filename
tpl = UPLOAD_DIR / template_filename
result = detect_watermark_template(str(img), str(tpl), scales=[0.6,0.8,1.0,1.2,1.4], threshold=0.7)
return JSONResponse(content=result)


@app.get('/uploads/{fname}')
def serve_upload(fname: str):
fp = UPLOAD_DIR / fname
if fp.exists():
return FileResponse(fp)
return JSONResponse(status_code=404, content={'error': 'file not found'})


# run: uvicorn backend.main:app --reload