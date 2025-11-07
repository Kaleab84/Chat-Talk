// Tabs
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    const target = document.querySelector(btn.dataset.target);
    if (target) target.classList.add('active');
  });
});

// Helpers
const createItem = (name) => {
  const el = document.createElement('div');
  el.className = 'item';
  el.innerHTML = `
    <div class="row">
      <div class="name">${name}</div>
      <div class="meta" data-status>Ready</div>
    </div>
    <div class="bar"><div class="fill" data-fill></div></div>
    <div class="meta" data-detail></div>
  `;
  return el;
};

const setProgress = (el, pct) => { const fill = el.querySelector('[data-fill]'); if (fill) fill.style.width = `${pct}%`; };
const setStatus = (el, text, ok=false) => { const st = el.querySelector('[data-status]'); if (st) { st.textContent = text; st.className = `meta ${ok ? 'ok' : ''}`; } };
const setDetail = (el, text, isError=false) => { const d = el.querySelector('[data-detail]'); if (d) { d.textContent = text; d.className = `meta ${isError ? 'err' : ''}`; } };

// Single upload (drag & drop)
const dz = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const uploads = document.getElementById('uploads');

const uploadFile = (file) => {
  const item = createItem(file.name); uploads.prepend(item);
  return new Promise((resolve) => {
    const form = new FormData(); form.append('file', file);
    const xhr = new XMLHttpRequest(); xhr.open('POST', '/files/upload');
    xhr.upload.addEventListener('progress', (e) => { if (e.lengthComputable) setProgress(item, Math.round((e.loaded / e.total) * 100)); });
    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        try {
          const data = JSON.parse(xhr.responseText || '{}');
          if (xhr.status >= 200 && xhr.status < 300) {
            setProgress(item, 100); setStatus(item, 'Ingested', true);
            const info = data?.ingestion || {}; setDetail(item, `sections: ${info.sections_processed ?? '-'}, chunks: ${info.chunks_processed ?? '-'}`);
            resolve(data);
          } else { setStatus(item, 'Failed'); setDetail(item, data?.error || data?.ingestion?.error || 'Upload failed', true); resolve(null); }
        } catch { setStatus(item, 'Failed'); setDetail(item, 'Unexpected response', true); resolve(null); }
      }
    };
    xhr.send(form);
  });
};

dz.addEventListener('click', () => fileInput.click());
dz.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') fileInput.click(); });
dz.addEventListener('dragover', (e) => { e.preventDefault(); dz.classList.add('dragover'); });
dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
dz.addEventListener('drop', (e) => { e.preventDefault(); dz.classList.remove('dragover'); const files = Array.from(e.dataTransfer.files || []); if (files.length) uploadFile(files[0]); });
fileInput.addEventListener('change', (e) => { const file = e.target.files[0]; if (file) uploadFile(file); });

// Bulk upload
const bulkInput = document.getElementById('bulkInput');
const bulkStart = document.getElementById('bulkStart');
const bulkUploads = document.getElementById('bulkUploads');

const pLimit = (n) => { const queue = []; let activeCount = 0; const next = () => { activeCount--; if (queue.length) queue.shift()(); }; const run = async (fn, resolve) => { activeCount++; const result = (async () => fn())(); resolve(result); try { await result; } finally { next(); } }; const enqueue = (fn) => new Promise((resolve) => { const task = () => run(fn, resolve); activeCount < n ? task() : queue.push(task); }); return (fn) => enqueue(fn); };
const limit = pLimit(3);

const bulkUpload = async (files) => {
  if (!files.length) return; bulkStart.disabled = true;
  const items = files.map(f => { const el = createItem(f.name); bulkUploads.prepend(el); return { file: f, el }; });
  await Promise.all(items.map(({ file, el }) => limit(() => new Promise((resolve) => {
    const form = new FormData(); form.append('file', file);
    const xhr = new XMLHttpRequest(); xhr.open('POST', '/files/upload');
    xhr.upload.addEventListener('progress', (e) => { if (e.lengthComputable) setProgress(el, Math.round((e.loaded / e.total) * 100)); });
    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        try { const data = JSON.parse(xhr.responseText || '{}'); if (xhr.status >= 200 && xhr.status < 300) { setProgress(el, 100); setStatus(el, 'Ingested', true); const info = data?.ingestion || {}; setDetail(el, `sections: ${info.sections_processed ?? '-'}, chunks: ${info.chunks_processed ?? '-'}`); } else { setStatus(el, 'Failed'); setDetail(el, data?.error || data?.ingestion?.error || 'Upload failed', true); } } catch { setStatus(el, 'Failed'); setDetail(el, 'Unexpected response', true); }
        resolve();
      }
    };
    xhr.send(form);
  }))));
  bulkStart.disabled = false;
};

bulkStart.addEventListener('click', () => { const files = Array.from(bulkInput.files || []); bulkUpload(files); });

// Search
const searchForm = document.getElementById('searchForm');
const searchQuery = document.getElementById('searchQuery');
const searchResults = document.getElementById('searchResults');

searchForm.addEventListener('submit', async (e) => {
  e.preventDefault(); searchResults.innerHTML = '';
  const item = createItem(`Search: ${searchQuery.value}`); setStatus(item, 'Querying…'); searchResults.prepend(item);
  try {
    const res = await fetch('/search', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query: searchQuery.value, top_k: 5 }) });
    const data = await res.json(); setStatus(item, data.success ? 'Done' : 'Error', !!data.success); setDetail(item, data.success ? `${data.total_results} results` : (data.detail || 'Error'), !data.success);
    if (data.results?.length) {
      data.results.slice(0, 5).forEach(r => { const el = document.createElement('div'); el.className = 'meta'; el.textContent = `• ${r.text?.slice(0, 120) || ''}${(r.text||'').length>120?'…':''}  (score: ${r.score?.toFixed?.(3) ?? r.score})`; item.appendChild(el); });
    }
  } catch (err) { setStatus(item, 'Error'); setDetail(item, String(err), true); }
});

