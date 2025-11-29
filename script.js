// script.js
// Advanced frontend logic for Watermark Robustness Lab
// Expects backend endpoints: /upload/, /add-watermark/, /edit/, /check/, and uploaded files served at /uploads/<filename>

(() => {
    // Elements
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const preview = document.getElementById('preview');
    const canvasHolder = document.getElementById('canvasHolder');
    const fileNameEl = document.getElementById('fileName');
    const fileSizeEl = document.getElementById('fileSize');
    const wmTypeEl = document.getElementById('wmType');
    const textOptions = document.getElementById('textOptions');
    const imageOptions = document.getElementById('imageOptions');
    const wmTextEl = document.getElementById('wmText');
    const wmOpacityEl = document.getElementById('wmOpacity');
    const wmFontSizeEl = document.getElementById('wmFontSize');
    const wmImageFileEl = document.getElementById('wmImageFile');
    const wmScaleEl = document.getElementById('wmScale');
    const addWmBtn = document.getElementById('addWm');
    const clearPreviewBtn = document.getElementById('clearPreview');
    const editOpEl = document.getElementById('editOp');
    const resizeInputs = document.getElementById('resizeInputs');
    const cropInputs = document.getElementById('cropInputs');
    const applyEditBtn = document.getElementById('applyEdit');
    const autoExperimentBtn = document.getElementById('autoExperiment');
    const tplInput = document.getElementById('tplInput');
    const checkBtn = document.getElementById('checkBtn');
    const detectionResult = document.getElementById('detectionResult');
    const statTests = document.getElementById('statTests');
    const statFound = document.getElementById('statFound');
    const statScore = document.getElementById('statScore');
    const downloadImgBtn = document.getElementById('downloadImg');
    const downloadZipBtn = document.getElementById('downloadZip');
    const runBatchBtn = document.getElementById('runBatch');
    const openGuideBtn = document.getElementById('openGuide');
  
    // State
    let localFile = null;         // File object selected by user
    let lastUploaded = null;      // filename on server after upload
    let lastWatermarked = null;   // filename on server after watermarking
    let lastEdited = null;        // filename on server after editing
  
    // --------- Helpers ----------
    function setPreviewFromURL(url) {
      preview.innerHTML = `<img src="${url}" alt="preview" />`;
      canvasHolder.innerHTML = `<img id="workImg" src="${url}" style="max-width:100%; border-radius:8px" />`;
    }
  
    function setCanvasEmpty() {
      canvasHolder.innerHTML = 'No image loaded';
      preview.innerHTML = '';
    }
  
    function humanFileSize(bytes) {
      if (!bytes) return '-';
      const units = ['B', 'KB', 'MB', 'GB'];
      let i = 0;
      let v = bytes;
      while (v >= 1024 && i < units.length - 1) {
        v /= 1024;
        i++;
      }
      return `${v.toFixed(1)} ${units[i]}`;
    }
  
    async function safeJson(res) {
      try {
        return await res.json();
      } catch (e) {
        return { error: `Invalid JSON response (status ${res.status})` };
      }
    }
  
    // --------- Drag & Drop ----------
    ['dragenter', 'dragover'].forEach(ev => {
      dropZone.addEventListener(ev, e => {
        e.preventDefault();
        dropZone.classList.add('hover');
      });
    });
    ['dragleave', 'drop'].forEach(ev => {
      dropZone.addEventListener(ev, e => {
        e.preventDefault();
        dropZone.classList.remove('hover');
      });
    });
  
    dropZone.addEventListener('drop', async (e) => {
      const f = e.dataTransfer.files && e.dataTransfer.files[0];
      if (!f) return;
      handleLocalFile(f);
    });
  
    fileInput.addEventListener('change', (e) => {
      const f = e.target.files && e.target.files[0];
      if (!f) return;
      handleLocalFile(f);
    });
  
    function handleLocalFile(file) {
      localFile = file;
      fileNameEl.innerText = file.name;
      fileSizeEl.innerText = humanFileSize(file.size);
      const url = URL.createObjectURL(file);
      setPreviewFromURL(url);
      lastUploaded = null;
      lastWatermarked = null;
      lastEdited = null;
    }
  
    // --------- Upload ----------
    async function uploadToServer(file) {
      if (!file) throw new Error('No file provided for upload');
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch('/upload/', { method: 'POST', body: fd });
      if (!res.ok) throw new Error(`Upload failed (status ${res.status})`);
      const j = await safeJson(res);
      return j.filename;
    }
  
    // --------- Add Watermark ----------
    addWmBtn.addEventListener('click', async () => {
      try {
        let serverFile = lastUploaded;
        if (!serverFile) {
          if (!localFile) return alert('Please upload or drop an image first.');
          serverFile = await uploadToServer(localFile);
          lastUploaded = serverFile;
        }
  
        const type = wmTypeEl.value;
        const fd = new FormData();
        fd.append('filename', serverFile);
  
        if (type === 'text') {
          fd.append('text', wmTextEl.value || 'SAMPLE');
          fd.append('opacity', wmOpacityEl.value || '0.25');
          fd.append('fontsize', wmFontSizeEl.value || '48');
          // Backend earlier expects only filename & text — adapt if backend supports extra fields
        } else {
          // If backend accepts watermark image, attach it. If not, frontend still sends it; backend may ignore.
          const wfile = wmImageFileEl.files[0];
          if (!wfile) return alert('Choose a watermark image file in Image mode.');
          fd.append('watermark', wfile);
          fd.append('scale', wmScaleEl.value || '0.18');
          fd.append('opacity', wmOpacityEl.value || '0.5');
        }
  
        const res = await fetch('/add-watermark/', { method: 'POST', body: fd });
        const j = await safeJson(res);
        if (j.error) throw new Error(j.error);
        // Expecting { watermarked: "<filename>" } or similar
        const serverWm = j.watermarked || j.filename || j.watermarked_filename || null;
        // fallback if response returns filename directly
        const finalName = serverWm || j.filename || (j.watermarked ? j.watermarked : null);
        if (!finalName && typeof j === 'string') {
          lastWatermarked = j;
        } else {
          lastWatermarked = finalName || j.watermarked || null;
        }
  
        if (!lastWatermarked) {
          // If backend returned something different, try to find any plausible key
          const keys = Object.keys(j);
          if (keys.length === 1 && typeof j[keys[0]] === 'string') {
            lastWatermarked = j[keys[0]];
          }
        }
  
        if (!lastWatermarked) {
          // As a fallback, assume server overwrote original — use serverFile
          lastWatermarked = serverFile;
        }
  
        canvasHolder.innerHTML = `<img src="/uploads/${lastWatermarked}" style="max-width:100%; border-radius:8px" />`;
        alert('Watermark added (server file: ' + lastWatermarked + ')');
      } catch (err) {
        console.error(err);
        alert('Error adding watermark: ' + (err.message || err));
      }
    });
  
    // --------- Edit image ----------
    editOpEl.addEventListener('change', () => {
      const v = editOpEl.value;
      resizeInputs.style.display = v === 'resize' ? 'block' : 'none';
      cropInputs.style.display = v === 'crop' ? 'block' : 'none';
    });
  
    applyEditBtn.addEventListener('click', async () => {
      try {
        const filename = lastWatermarked || lastUploaded;
        if (!filename) return alert('Upload or watermark an image first.');
  
        const op = editOpEl.value;
        const fd = new FormData();
        fd.append('filename', filename);
        fd.append('op', op);
  
        if (op === 'resize') {
          const w = document.getElementById('resizeW').value;
          const h = document.getElementById('resizeH').value;
          if (!w || !h) return alert('Enter both width and height for resize.');
          fd.append('w', parseInt(w));
          fd.append('h', parseInt(h));
        } else {
          // crop
          const x = document.getElementById('cropX').value || 0;
          const y = document.getElementById('cropY').value || 0;
          const cw = document.getElementById('cropW').value || 100;
          const ch = document.getElementById('cropH').value || 100;
          fd.append('x', parseInt(x));
          fd.append('y', parseInt(y));
          fd.append('crop_w', parseInt(cw));
          fd.append('crop_h', parseInt(ch));
        }
  
        const res = await fetch('/edit/', { method: 'POST', body: fd });
        const j = await safeJson(res);
        if (j.error) throw new Error(j.error);
        const edited = j.edited || j.filename || Object.values(j).find(v => typeof v === 'string') || null;
        lastEdited = edited || null;
        const resultFile = lastEdited || filename;
        canvasHolder.innerHTML = `<img src="/uploads/${resultFile}" style="max-width:100%; border-radius:8px" />`;
        alert('Edit applied: ' + (resultFile));
      } catch (err) {
        console.error(err);
        alert('Error applying edit: ' + (err.message || err));
      }
    });
  
    // --------- Quick demo experiment ----------
    autoExperimentBtn.addEventListener('click', async () => {
      try {
        if (!localFile && !lastUploaded) return alert('Load and upload an image first for quick demo.');
        // Simple quick flow: ensure upload -> add text watermark -> resize edit -> check
        if (!lastUploaded) {
          lastUploaded = await uploadToServer(localFile);
        }
        // Add watermark with default text
        const fd1 = new FormData();
        fd1.append('filename', lastUploaded);
        fd1.append('text', wmTextEl.value || 'SAMPLE');
        fd1.append('opacity', wmOpacityEl.value || '0.25');
        fd1.append('fontsize', wmFontSizeEl.value || '48');
        const res1 = await fetch('/add-watermark/', { method: 'POST', body: fd1 });
        const j1 = await safeJson(res1);
        lastWatermarked = j1.watermarked || j1.filename || lastUploaded;
        // Apply resize to 75% of original if possible
        const tempImg = document.createElement('img');
        tempImg.src = `/uploads/${lastWatermarked}`;
        await new Promise(r => (tempImg.onload = r));
        const newW = Math.round(tempImg.naturalWidth * 0.75);
        const newH = Math.round(tempImg.naturalHeight * 0.75);
        const fd2 = new FormData();
        fd2.append('filename', lastWatermarked);
        fd2.append('op', 'resize');
        fd2.append('w', newW);
        fd2.append('h', newH);
        const res2 = await fetch('/edit/', { method: 'POST', body: fd2 });
        const j2 = await safeJson(res2);
        lastEdited = j2.edited || j2.filename || lastWatermarked;
        canvasHolder.innerHTML = `<img src="/uploads/${lastEdited}" style="max-width:100%; border-radius:8px" />`;
        alert('Quick demo finished: watermark added + resized. Use Detection panel to check.');
      } catch (err) {
        console.error(err);
        alert('Quick experiment failed: ' + (err.message || err));
      }
    });
  
    // --------- Check detection ----------
    checkBtn.addEventListener('click', async () => {
      try {
        const tpl = tplInput.value.trim();
        const target = lastEdited || lastWatermarked || lastUploaded;
        if (!tpl) return alert('Enter template filename (server-side watermark image).');
        if (!target) return alert('No image on server to check. Upload/watermark/edit first.');
  
        const fd = new FormData();
        fd.append('filename', target);
        fd.append('template_filename', tpl);
        const res = await fetch('/check/', { method: 'POST', body: fd });
        const j = await safeJson(res);
        detectionResult.innerText = JSON.stringify(j, null, 2);
  
        // update stats
        statTests.innerText = parseInt(statTests.innerText || '0') + 1;
        if (j.found) statFound.innerText = parseInt(statFound.innerText || '0') + 1;
        statScore.innerText = (typeof j.max_val === 'number') ? j.max_val.toFixed(3) : (j.max_val || '-');
      } catch (err) {
        console.error(err);
        alert('Error checking watermark: ' + (err.message || err));
      }
    });
  
    // --------- Download current image ----------
    downloadImgBtn.addEventListener('click', () => {
      const img = canvasHolder.querySelector('img');
      if (!img) return alert('No image to download.');
      const a = document.createElement('a');
      a.href = img.src;
      a.download = (lastEdited || lastWatermarked || lastUploaded) || 'image.png';
      document.body.appendChild(a);
      a.click();
      a.remove();
    });
  
    // --------- Download project (placeholder) ----------
    downloadZipBtn.addEventListener('click', () => {
      alert('If you want a ZIP of the whole project, ask me and I will prepare it for you.');
    });
  
    // --------- Run batch (demo) ----------
    runBatchBtn.addEventListener('click', async () => {
      alert('Batch runner is a demo: this frontend can be extended to run multiple transforms automatically. For now use Quick Test or manual steps.');
    });
  
    // --------- Small UI helpers ----------
    wmTypeEl.addEventListener('change', (e) => {
      if (e.target.value === 'text') {
        textOptions.style.display = 'block';
        imageOptions.style.display = 'none';
      } else {
        textOptions.style.display = 'none';
        imageOptions.style.display = 'block';
      }
    });
  
    clearPreviewBtn.addEventListener('click', () => {
      localFile = null;
      lastUploaded = null;
      lastWatermarked = null;
      lastEdited = null;
      fileNameEl.innerText = '-';
      fileSizeEl.innerText = '-';
      setCanvasEmpty();
    });
  
    openGuideBtn.addEventListener('click', () => {
      const msg = `How it works:
  1) Upload an image (drag & drop or browse).
  2) Add a watermark (text or image). Frontend will upload file to /upload/ then call /add-watermark/.
  3) Edit (resize / crop) using /edit/.
  4) Use Detection panel to call /check/ with the watermark template filename.
  Note: This UI assumes a FastAPI backend is running at the same host.`;
      alert(msg);
    });
  
    // Initialize
    setCanvasEmpty();
  })();
  