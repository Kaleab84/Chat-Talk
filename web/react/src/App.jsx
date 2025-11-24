import { useCallback, useEffect, useRef, useState } from 'react';
import Dropzone from './components/Dropzone.jsx';
import UploadList from './components/UploadList.jsx';
import { getGreeting } from './utils/displayName.js';

const CONCURRENCY_LIMIT = 3;

const createUploadId = () => {
  const cryptoRef = typeof globalThis !== 'undefined' ? globalThis.crypto : null;
  if (cryptoRef && typeof cryptoRef.randomUUID === 'function') {
    return cryptoRef.randomUUID();
  }
  return `upload-${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const formatIngestionDetail = (payload) => {
  const info = payload?.ingestion || {};
  const sections = info.sections_processed ?? '-';
  const chunks = info.chunks_processed ?? '-';
  return `sections: ${sections}, chunks: ${chunks}`;
};

const extractErrorDetail = (payload, status) => {
  if (!payload) {
    return status ? `Upload failed (HTTP ${status})` : 'Upload failed (network error)';
  }
  return (
    payload.error ||
    payload.detail ||
    payload?.ingestion?.error ||
    (status ? `Upload failed (HTTP ${status})` : 'Upload failed')
  );
};

const uploadWithProgress = (file, { onProgress }) =>
  new Promise((resolve) => {
    const form = new FormData();
    form.append('file', file);
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/files/upload');
    xhr.upload.addEventListener('progress', (event) => {
      if (!event.lengthComputable) return;
      const pct = Math.round((event.loaded / event.total) * 100);
      onProgress?.(pct);
    });
    xhr.onreadystatechange = () => {
      if (xhr.readyState !== 4) return;
      let parsed = null;
      try {
        parsed = JSON.parse(xhr.responseText || '{}');
      } catch (error) {
        console.error('Unable to parse upload response', error);
      }
      const success = xhr.status >= 200 && xhr.status < 300;
      resolve({ ok: success, payload: parsed, status: xhr.status || 0 });
    };
    xhr.onerror = () => resolve({ ok: false, payload: null, status: xhr.status || 0 });
    xhr.send(form);
  });

const runWithConcurrency = async (tasks, limit) => {
  if (!tasks.length) return;
  if (limit <= 0) {
    await Promise.all(tasks.map((task) => task()));
    return;
  }
  const executing = new Set();
  for (const task of tasks) {
    const promise = Promise.resolve().then(task);
    executing.add(promise);
    const clean = () => executing.delete(promise);
    promise.then(clean).catch(clean);
    if (executing.size >= limit) {
      await Promise.race(executing);
    }
  }
  await Promise.allSettled(Array.from(executing));
};

const prependUploadEntry = (setFn, entry) => {
  setFn((prev) => [entry, ...prev]);
};

const updateUploadEntry = (setFn, id, patch) => {
  setFn((prev) => prev.map((item) => (item.id === id ? { ...item, ...patch } : item)));
};

export default function App() {
  const [greeting, setGreeting] = useState(() => getGreeting());
  const [singleUploads, setSingleUploads] = useState([]);
  const [bulkUploads, setBulkUploads] = useState([]);
  const [bulkSelection, setBulkSelection] = useState([]);
  const [isBulkUploading, setIsBulkUploading] = useState(false);
  const bulkInputRef = useRef(null);

  useEffect(() => {
    setGreeting(getGreeting());
  }, []);

  const performUpload = useCallback(
    (kind, file) => {
      const setters = kind === 'single' ? setSingleUploads : setBulkUploads;
      const id = createUploadId();
      const entry = {
        id,
        name: file.name,
        progress: 0,
        status: 'Queued',
        detail: '',
        isSuccess: false,
        isError: false,
      };
      prependUploadEntry(setters, entry);
      updateUploadEntry(setters, id, { status: 'Uploading', detail: 'Initializing upload' });

      return uploadWithProgress(file, {
        onProgress: (progress) => updateUploadEntry(setters, id, { progress, status: 'Uploading' }),
      }).then((result) => {
        if (result.ok) {
          updateUploadEntry(setters, id, {
            status: 'Ingested',
            detail: formatIngestionDetail(result.payload),
            progress: 100,
            isSuccess: true,
            isError: false,
          });
        } else {
          updateUploadEntry(setters, id, {
            status: 'Failed',
            detail: extractErrorDetail(result.payload, result.status),
            isError: true,
          });
        }
      });
    },
    []
  );

  const handleSingleFile = useCallback(
    (file) => {
      if (!file) return;
      performUpload('single', file);
    },
    [performUpload]
  );

  const startBulkUpload = async () => {
    if (!bulkSelection.length) return;
    setIsBulkUploading(true);
    const tasks = bulkSelection.map((file) => () => performUpload('bulk', file));
    await runWithConcurrency(tasks, CONCURRENCY_LIMIT);
    setIsBulkUploading(false);
    setBulkSelection([]);
    if (bulkInputRef.current) {
      bulkInputRef.current.value = '';
    }
  };

  return (
    <div className='react-app'>
      <header className='container header react-header'>
        <div className='brand'>CFC Software Support</div>
        <div className='greet'>{greeting ? `Hi, ${greeting}!` : 'Welcome back'}</div>
      </header>

      <main className='container dashboard-main'>
        <section className='panel active'>
          <div className='panel-body'>
            <h2>Upload &amp; Ingest</h2>
            <p>Drop a file below. Uploading automatically starts ingestion.</p>
            <Dropzone onFileSelected={handleSingleFile} />
            <UploadList items={singleUploads} emptyMessage='No uploads yet.' />
          </div>
        </section>

        <section className='panel active'>
          <div className='panel-body'>
            <h2>Bulk Uploads</h2>
            <p>Select multiple files. We keep three uploads running at a time.</p>
            <div className='controls'>
              <input
                ref={bulkInputRef}
                type='file'
                multiple
                onChange={(event) =>
                  setBulkSelection(event.target.files ? Array.from(event.target.files) : [])
                }
              />
              <button
                type='button'
                className='btn'
                disabled={!bulkSelection.length || isBulkUploading}
                onClick={startBulkUpload}
              >
                {isBulkUploading ? 'Uploading...' : 'Start Upload'}
              </button>
            </div>
            <div className='meta'>
              {bulkSelection.length
                ? `${bulkSelection.length} file${bulkSelection.length > 1 ? 's' : ''} selected`
                : 'No files selected yet'}
            </div>
            <UploadList items={bulkUploads} emptyMessage='No bulk uploads yet.' />
          </div>
        </section>
      </main>

      <footer className='container footer'>
        <a className='btn' href='/ui/login.html' aria-label='Back to Login'>
          Back to Login
        </a>
      </footer>
    </div>
  );
}
