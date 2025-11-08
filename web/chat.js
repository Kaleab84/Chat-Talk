// Chat-only script
// Greeting header
(() => {
  try {
    const el = document.getElementById('greet');
    if (!el) return;
    const raw = (localStorage.getItem('displayName') || '').trim();
    if (raw) {
      const options = ['Hi', 'Hey', 'Hello'];
      const prefix = options[Math.floor(Math.random() * options.length)];
      const name = raw.charAt(0).toUpperCase() + raw.slice(1);
      el.textContent = `${prefix}, ${name}!`;
    }
  } catch {}
})();
// Minimal helpers
const appendMsg = (text, who = 'bot', extraClass = '') => {
  const askThread = document.getElementById('askThread');
  const div = document.createElement('div');
  div.className = `msg ${who} ${extraClass}`.trim();
  div.textContent = text;
  askThread.appendChild(div);
  askThread.scrollTop = askThread.scrollHeight;
  return div;
};

const appendMsgWithImages = (text, files) => {
  const askThread = document.getElementById('askThread');
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
      const previewUrl = URL.createObjectURL(file);
      const img = document.createElement('img');
      img.alt = file.name || 'attachment';
      img.src = previewUrl;
      // Open in lightbox on click
      img.addEventListener('click', (e) => {
        e.preventDefault();
        openImageLightbox(file);
      });
      grid.appendChild(img);
    } catch {}
  });
  if (grid.children.length) container.appendChild(grid);
  askThread.appendChild(container);
  askThread.scrollTop = askThread.scrollHeight;
  return container;
};

// Image lightbox
let __imgModal, __imgModalImg, __currentModalUrl;
const ensureImageModal = () => {
  if (__imgModal) return __imgModal;
  const modal = document.createElement('div');
  modal.className = 'img-modal';
  const innerImg = document.createElement('img');
  innerImg.alt = 'attachment preview';
  modal.appendChild(innerImg);
  modal.addEventListener('click', () => closeImageLightbox());
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeImageLightbox(); });
  document.body.appendChild(modal);
  __imgModal = modal; __imgModalImg = innerImg; return modal;
};

const openImageLightbox = (file) => {
  ensureImageModal();
  // Revoke prior modal URL if any
  try { if (__currentModalUrl) URL.revokeObjectURL(__currentModalUrl); } catch {}
  const url = URL.createObjectURL(file);
  __currentModalUrl = url;
  __imgModalImg.src = url;
  __imgModal.classList.add('active');
};

const closeImageLightbox = () => {
  if (!__imgModal) return;
  __imgModal.classList.remove('active');
  // Small delay to allow transition (if any) before revoking
  const url = __currentModalUrl; __currentModalUrl = null;
  setTimeout(() => { try { if (url) URL.revokeObjectURL(url); } catch {} }, 100);
};

// Wire controls
const askForm = document.getElementById('askForm');
const askQuestion = document.getElementById('askQuestion');
const askSend = document.getElementById('askSend');
const askThread = document.getElementById('askThread');

let askImages = document.getElementById('askImages');
let askAttach = document.getElementById('askAttach');
let askAttachments = document.getElementById('askAttachments');
if (!askImages) {
  askImages = document.createElement('input');
  askImages.type = 'file'; askImages.accept = 'image/*'; askImages.multiple = true; askImages.id = 'askImages'; askImages.hidden = true;
  askForm.appendChild(askImages);
}
if (!askAttach) {
  askAttach = document.createElement('button');
  askAttach.type = 'button'; askAttach.className = 'btn'; askAttach.id = 'askAttach'; askAttach.textContent = 'Attach';
  askForm.insertBefore(askAttach, askSend);
}
if (!askAttachments) {
  askAttachments = document.createElement('div'); askAttachments.id = 'askAttachments'; askAttachments.className = 'meta';
  askForm.parentElement.appendChild(askAttachments);
}

askAttach.addEventListener('click', () => askImages.click());
askImages.addEventListener('change', () => {
  const count = (askImages.files || []).length;
  askAttachments.textContent = count ? `${count} image${count>1?'s':''} attached` : '';
});

askForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = askQuestion.value.trim(); if (!q) return;
  askQuestion.value = '';
  const files = Array.from(askImages.files || []);
  files.length ? appendMsgWithImages(q, files) : appendMsg(q, 'user');
  const typing = appendMsg('Assistant is thinking', 'bot', 'typing dots');
  askSend.disabled = true;
  try {
    let data;
    if (files.length) {
      const form = new FormData(); form.append('question', q); form.append('top_k', '4'); files.forEach(f => form.append('images', f));
      const res = await fetch('/ask-with-media', { method: 'POST', body: form }); data = await res.json();
    } else {
      const res = await fetch('/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: q, top_k: 4 }) });
      data = await res.json();
    }
    typing.remove();
    appendMsg(data.success ? (data.answer || 'No answer available') : (data.detail || 'Error'), 'bot');
  } catch (err) {
    typing.remove(); appendMsg(String(err), 'bot');
  } finally {
    askSend.disabled = false; askImages.value = ''; askAttachments.textContent = '';
  }
});

