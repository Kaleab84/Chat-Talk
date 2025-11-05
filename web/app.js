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

const setProgress = (el, pct) => {
  const fill = el.querySelector('[data-fill]');
  if (fill) fill.style.width = `${pct}%`;
};

const setStatus = (el, text, ok=false) => {
  const st = el.querySelector('[data-status]');
  if (st) {
    st.textContent = text;
    st.className = `meta ${ok ? 'ok' : ''}`;
  }
};

const setDetail = (el, text, isError=false) => {
  const d = el.querySelector('[data-detail]');
  if (d) {
    d.textContent = text;
    d.className = `meta ${isError ? 'err' : ''}`;
  }
};

// Single upload (drag & drop)
const dz = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const uploads = document.getElementById('uploads');

const uploadFile = (file) => {
  const item = createItem(file.name);
  uploads.prepend(item);

  return new Promise((resolve) => {
    const form = new FormData();
    form.append('file', file);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/files/upload');
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        setProgress(item, pct);
        setStatus(item, `Uploading… ${pct}%`);
      }
    });
    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        try {
          const data = JSON.parse(xhr.responseText || '{}');
          if (xhr.status >= 200 && xhr.status < 300) {
            setProgress(item, 100);
            setStatus(item, 'Ingested', true);
            const info = data?.ingestion || {};
            setDetail(item, `sections: ${info.sections_processed ?? '-'}, chunks: ${info.chunks_processed ?? '-'}`);
            resolve(data);
          } else {
            setStatus(item, 'Failed');
            setDetail(item, data?.error || data?.ingestion?.error || 'Upload failed', true);
            resolve(null);
          }
        } catch (err) {
          setStatus(item, 'Failed');
          setDetail(item, 'Unexpected response', true);
          resolve(null);
        }
      }
    };
    xhr.send(form);
  });
};

dz.addEventListener('click', () => fileInput.click());
dz.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') fileInput.click(); });
dz.addEventListener('dragover', (e) => { e.preventDefault(); dz.classList.add('dragover'); });
dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
dz.addEventListener('drop', (e) => {
  e.preventDefault(); dz.classList.remove('dragover');
  const files = Array.from(e.dataTransfer.files || []);
  if (files.length) uploadFile(files[0]);
});
fileInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (file) uploadFile(file);
});

// Bulk upload
const bulkInput = document.getElementById('bulkInput');
const bulkStart = document.getElementById('bulkStart');
const bulkUploads = document.getElementById('bulkUploads');

const pLimit = (n) => {
  const queue = [];
  let activeCount = 0;
  const next = () => {
    activeCount--;
    if (queue.length) queue.shift()();
  };
  const run = async (fn, resolve) => {
    activeCount++;
    const result = (async () => fn())();
    resolve(result);
    try { await result; } finally { next(); }
  };
  const enqueue = (fn) => new Promise((resolve) => {
    const task = () => run(fn, resolve);
    activeCount < n ? task() : queue.push(task);
  });
  return (fn) => enqueue(fn);
};

const limit = pLimit(3);

const bulkUpload = async (files) => {
  if (!files.length) return;
  bulkStart.disabled = true;
  const items = files.map(f => {
    const el = createItem(f.name);
    bulkUploads.prepend(el);
    return { file: f, el };
  });
  await Promise.all(items.map(({ file, el }) => limit(() => new Promise((resolve) => {
    const form = new FormData(); form.append('file', file);
    const xhr = new XMLHttpRequest(); xhr.open('POST', '/files/upload');
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) setProgress(el, Math.round((e.loaded / e.total) * 100));
    });
    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        try {
          const data = JSON.parse(xhr.responseText || '{}');
          if (xhr.status >= 200 && xhr.status < 300) {
            setProgress(el, 100); setStatus(el, 'Ingested', true);
            const info = data?.ingestion || {};
            setDetail(el, `sections: ${info.sections_processed ?? '-'}, chunks: ${info.chunks_processed ?? '-'}`);
          } else {
            setStatus(el, 'Failed'); setDetail(el, data?.error || data?.ingestion?.error || 'Upload failed', true);
          }
        } catch {
          setStatus(el, 'Failed'); setDetail(el, 'Unexpected response', true);
        }
        resolve();
      }
    };
    xhr.send(form);
  }))));
  bulkStart.disabled = false;
};

bulkStart.addEventListener('click', () => {
  const files = Array.from(bulkInput.files || []);
  bulkUpload(files);
});

// Search
const searchForm = document.getElementById('searchForm');
const searchQuery = document.getElementById('searchQuery');
const searchResults = document.getElementById('searchResults');

searchForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  searchResults.innerHTML = '';
  const item = createItem(`Search: ${searchQuery.value}`);
  setStatus(item, 'Querying…');
  searchResults.prepend(item);
  try {
    const res = await fetch('/search', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: searchQuery.value, top_k: 5 })
    });
    const data = await res.json();
    setStatus(item, data.success ? 'Done' : 'Error', !!data.success);
    setDetail(item, data.success ? `${data.total_results} results` : (data.detail || 'Error'), !data.success);
    if (data.results?.length) {
      data.results.slice(0, 5).forEach(r => {
        const el = document.createElement('div'); el.className = 'meta';
        el.textContent = `• ${r.text?.slice(0, 120) || ''}${(r.text||'').length>120?'…':''}  (score: ${r.score?.toFixed?.(3) ?? r.score})`;
        item.appendChild(el);
      });
    }
  } catch (err) {
    setStatus(item, 'Error'); setDetail(item, String(err), true);
  }
});

// Ask (chat-style)
const askForm = document.getElementById('askForm');
const askQuestion = document.getElementById('askQuestion');
const askSend = document.getElementById('askSend');
const askThread = document.getElementById('askThread');

// Inject image attachment controls (avoid touching HTML with odd encodings)
let askImages = document.getElementById('askImages');
let askAttach = document.getElementById('askAttach');
let askAttachments = document.getElementById('askAttachments');
if (!askImages) {
  askImages = document.createElement('input');
  askImages.type = 'file';
  askImages.accept = 'image/*';
  askImages.multiple = true;
  askImages.id = 'askImages';
  askImages.hidden = true;
  askForm.appendChild(askImages);
}
if (!askAttach) {
  askAttach = document.createElement('button');
  askAttach.type = 'button';
  askAttach.className = 'btn';
  askAttach.id = 'askAttach';
  askAttach.title = 'Attach screenshots';
  askAttach.textContent = 'Attach';
  askForm.insertBefore(askAttach, askSend);
}
if (!askAttachments) {
  askAttachments = document.createElement('div');
  askAttachments.id = 'askAttachments';
  askAttachments.className = 'meta';
  askForm.parentElement.appendChild(askAttachments);
}

askAttach.addEventListener('click', () => askImages.click());
askImages.addEventListener('change', () => {
  const count = (askImages.files || []).length;
  askAttachments.textContent = count ? `${count} image${count>1?'s':''} attached` : '';
});

const appendMsg = (text, who = 'bot', extraClass = '') => {
  const div = document.createElement('div');
  div.className = `msg ${who} ${extraClass}`.trim();
  div.textContent = text;
  askThread.appendChild(div);
  askThread.scrollTop = askThread.scrollHeight;
  return div;
};

// Append a user message with inline image thumbnails
const appendMsgWithImages = (text, files) => {
  const container = document.createElement('div');
  container.className = 'msg user';

  if (text) {
    const p = document.createElement('div');
    p.textContent = text;
    container.appendChild(p);
  }

  const grid = document.createElement('div');
  grid.className = 'img-grid';
  (files || []).forEach((file) => {
    try {
      const url = URL.createObjectURL(file);
      const a = document.createElement('a');
      a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer';
      const img = document.createElement('img');
      img.alt = file.name || 'attachment';
      img.src = url;
      img.addEventListener('load', () => {
        // Small delay to ensure image is in use, then revoke
        setTimeout(() => URL.revokeObjectURL(url), 2000);
      });
      a.appendChild(img);
      grid.appendChild(a);
    } catch {}
  });
  if (grid.children.length) container.appendChild(grid);

  askThread.appendChild(container);
  askThread.scrollTop = askThread.scrollHeight;
  return container;
};

askForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = askQuestion.value.trim();
  if (!q) return;
  askQuestion.value = '';
  const files = Array.from(askImages.files || []);
  if (files.length) {
    appendMsgWithImages(q, files);
  } else {
    appendMsg(q, 'user');
  }
  const typing = appendMsg('Assistant is typing', 'bot', 'typing dots');
  askSend.disabled = true;
  try {
    let data;
    if (files.length) {
      const form = new FormData();
      form.append('question', q);
      form.append('top_k', '4');
      files.forEach(f => form.append('images', f));
      const res = await fetch('/ask-with-media', { method: 'POST', body: form });
      data = await res.json();
    } else {
      const res = await fetch('/ask', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, top_k: 4 })
      });
      data = await res.json();
    }
    typing.remove();
    if (data.success) {
      appendMsg(data.answer || 'No answer available', 'bot');
    } else {
      appendMsg(data.detail || 'Error', 'bot');
    }
  } catch (err) {
    typing.remove();
    appendMsg(String(err), 'bot');
  } finally {
    askSend.disabled = false;
    // Reset attachments
    askImages.value = '';
    askAttachments.textContent = '';
  }
});
