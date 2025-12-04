// React SPA for Chat-Talk UI
// Uses existing backend endpoints: /ask, /search, /files/upload, /api/videos/upload

// ---- Theme ----
const COLORS = {
  sand: '#D0A97C',
  green: '#379D63',
  blue: '#4065AE',
  text: '#111827',
  subtle: '#6B7280',
  border: '#E5E7EB',
  background: '#F3F4F6',
  white: '#FFFFFF',
};

// ---- User Context ----
const UserContext = React.createContext(null);

function useUser() {
  return React.useContext(UserContext);
}

function UserProvider({ children }) {
  const [user, setUser] = React.useState(() => {
    try {
      const raw = window.localStorage.getItem('cfc-user');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });

  const updateUser = React.useCallback((value) => {
    setUser(value);
    try {
      if (value) {
        window.localStorage.setItem('cfc-user', JSON.stringify(value));
      } else {
        window.localStorage.removeItem('cfc-user');
      }
    } catch {
      // ignore
    }
  }, []);

  return (
    <UserContext.Provider value={{ user, setUser: updateUser }}>
      {children}
    </UserContext.Provider>
  );
}

// ---- Simple in-app router (no external dependency) ----
const RouterContext = React.createContext(null);

function RouterProvider({ children }) {
  const [route, setRoute] = React.useState('login'); // 'login' | 'docs' | 'admin' | 'chat' | 'transition'
  const [nextRoute, setNextRoute] = React.useState(null);
  const [visualState, setVisualState] = React.useState('idle'); // idle | fade-out | fade-in

  const performNavigation = React.useCallback((next, options = {}) => {
    if (next === 'transition') {
      setNextRoute(options.to || null);
    } else {
      setNextRoute(null);
    }
    setRoute(next);
    requestAnimationFrame(() => setVisualState('fade-in'));
    setTimeout(() => setVisualState('idle'), 280);
  }, []);

  const navigate = React.useCallback((next, options = {}) => {
    if (options.withFade) {
      setVisualState('fade-out');
      setTimeout(() => performNavigation(next, options), 220);
    } else {
      performNavigation(next, options);
    }
  }, [performNavigation]);

  return (
    <RouterContext.Provider value={{ route, navigate, nextRoute, visualState }}>
      {children}
    </RouterContext.Provider>
  );
}

function useRouter() {
  return React.useContext(RouterContext);
}

// ---- Layout with logo and greeting ----
function Layout({ children }) {
  const { user } = useUser();
  const { route, navigate, visualState } = useRouter();

  const showBackToLogin = route !== 'login' && route !== 'transition';
  const [greetingName, setGreetingName] = React.useState('');
  const [hasAnimatedGreeting, setHasAnimatedGreeting] = React.useState(false);

  React.useEffect(() => {
    if (!user?.name) {
      setGreetingName('');
      setHasAnimatedGreeting(false);
      return;
    }
    const target = (user.name.split(' ')[0] || '').toString();

    // Only animate once when transitioning from login -> transition
    if (route === 'transition' && !hasAnimatedGreeting) {
      let idx = 0;
      setGreetingName('');
      const interval = setInterval(() => {
        idx += 1;
        setGreetingName(target.slice(0, idx));
        if (idx >= target.length) {
          clearInterval(interval);
          setHasAnimatedGreeting(true);
        }
      }, 140);
      return () => clearInterval(interval);
    }

    // For other route changes, just show full name without animating
    setGreetingName(target);
  }, [user?.name, route, hasAnimatedGreeting]);

  return (
    <div className="app-root">
      <header className="app-header">
        <div className="app-header-left">
          <img
            src="/ui/logo-cfc.png"
            alt="CFC Tech"
            className="app-logo"
          />
          <div className="app-header-brand">
            <div className="app-title">Support Assistant</div>
            <div className="app-subtitle">Conversational help for CFC Technologies</div>
          </div>
        </div>
        <div className="app-header-right">
          {user?.name ? (
            <span className="app-greeting">
              {greetingName ? `Hi, ${greetingName}!` : 'Hi,'}
            </span>
          ) : (
            <span className="app-greeting muted">Hi there!</span>
          )}
        </div>
      </header>

      <main className={`app-main page-fader ${visualState}`}>
        {children}
      </main>

      <footer className="app-footer">
        {showBackToLogin && (
          <button
            type="button"
            className="link-button"
            onClick={() => navigate('login')}
          >
            Return to login
          </button>
        )}
      </footer>
    </div>
  );
}

// ---- Shared UI primitives ----
function Card({ children, className = '' }) {
  return <div className={`card ${className}`}>{children}</div>;
}

function PrimaryButton({ children, ...props }) {
  return (
    <button className="btn-primary" {...props}>
      {children}
    </button>
  );
}

function SecondaryButton({ children, ...props }) {
  return (
    <button className="btn-secondary" {...props}>
      {children}
    </button>
  );
}

function TextInput({ label, error, ...props }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <input className={`field-input ${error ? 'field-error' : ''}`} {...props} />
      {error && <span className="field-error-text">{error}</span>}
    </label>
  );
}

// ---- Login Page ----
function LoginPage() {
  const [name, setName] = React.useState('');
  const [email, setEmail] = React.useState('');
  const [emailError, setEmailError] = React.useState('');
  const { setUser } = useUser();
  const { navigate } = useRouter();

  const validateEmail = (value) => {
    const trimmed = value.trim();
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(trimmed);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmedEmail = email.trim();
    if (!validateEmail(trimmedEmail)) {
      setEmailError('Please enter a valid email address.');
      return;
    }
    setEmailError('');

    const rawName = name.trim();
    let displayName = 'Guest';
    if (rawName) {
      const parts = rawName.split(/\s+/);
      const first = parts[0];
      const capFirst =
        first.charAt(0).toUpperCase() + first.slice(1).toLowerCase();
      const rest = parts.slice(1).join(' ');
      displayName = rest ? `${capFirst} ${rest}` : capFirst;
    }

    const nextUser = {
      name: displayName,
      email: trimmedEmail,
    };
    setUser(nextUser);

    const lower = trimmedEmail.toLowerCase();
    let target = 'chat';
    if (lower === 'admin@cfctech.com') target = 'admin';
    else if (lower === 'dev@cfctech.com') target = 'docs';

    navigate('transition', { to: target, withFade: true });
  };

  return (
    <Layout>
      <div className="page login-page">
        <div className="login-hero">
          <h1>Welcome to CFC AI</h1>
          <p>
            A focused assistant for Concept5 and CFC knowledge.
            <br />
            Ask clear questions and get concise, guided answers in seconds.
          </p>
          <div className="login-badges">
            <span className="badge badge-sand">Built for your workflows</span>
            <span className="badge badge-green">Instant answers</span>
            <span className="badge badge-blue">Guided help</span>
          </div>
        </div>

        <Card className="login-card">
          <form onSubmit={handleSubmit} className="login-form">
            <h2>Sign in</h2>
            <TextInput
              label="Name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Adam Smith"
              autoComplete="name"
            />
            <TextInput
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@cfctech.com"
              autoComplete="email"
              error={emailError}
            />
            <PrimaryButton type="submit">Continue</PrimaryButton>
          </form>
        </Card>
      </div>
    </Layout>
  );
}

// ---- Developer / Docs Page ----
function DocsPage() {
  return (
    <Layout>
      <div className="page docs-page">
        <div className="page-header-row">
          <div>
            <h1>Developer Workspace</h1>
            <p>
              Explore and test the HTTP API alongside a focused view
              of your documentation.
            </p>
          </div>
        </div>

        <div className="docs-grid">
          <Card className="docs-card">
            <h2>Interactive API Docs</h2>
            <p className="muted">
              This is the same OpenAPI/Swagger documentation exposed at{' '}
              <code>/docs</code>, wrapped in a scrollable surface.
            </p>
            <div className="docs-iframe-wrapper">
              <iframe
                src="/docs"
                title="API docs"
                className="docs-iframe"
              />
            </div>
          </Card>

          <Card className="docs-card notes-card">
            <h2>Implementation notes</h2>
            <ul className="notes-list">
              <li>Search and chat endpoints backed by your RAG pipeline.</li>
              <li>Video ingestion with Whisper and Pinecone indexing.</li>
              <li>Admin uploads immediately trigger ingestion workflows.</li>
            </ul>
          </Card>
        </div>
      </div>
    </Layout>
  );
}

// ---- Admin Page (upload + bulk upload, text vs video) ----
const VIDEO_EXTENSIONS = ['.mp4', '.mov', '.m4v', '.mkv', '.webm'];

function isVideoFile(file) {
  if (!file) return false;
  if (file.type && file.type.startsWith('video/')) return true;
  const name = file.name || '';
  const lower = name.toLowerCase();
  return VIDEO_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

function fileSlug(file) {
  const name = (file?.name || '').toLowerCase();
  return name.replace(/\.[^.]+$/, '').replace(/\s+/g, '-');
}

async function uploadSingleFile(file, onProgress) {
  if (!file) return { error: 'No file selected' };

  if (isVideoFile(file)) {
    // Video upload to /api/videos/upload
    const form = new FormData();
    form.append('slug', fileSlug(file));
    form.append('file', file);
    form.append('model', 'small');

    const res = await fetch('/api/videos/upload', {
      method: 'POST',
      body: form,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || 'Video upload failed');
    }
    if (onProgress) onProgress(100);
    return res.json();
  }

  // Document upload to /files/upload
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append('file', file);
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/files/upload');
    xhr.upload.addEventListener('progress', (e) => {
      if (onProgress && e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        onProgress(pct);
      }
    });
    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        try {
          const data = JSON.parse(xhr.responseText || '{}');
          if (xhr.status >= 200 && xhr.status < 300) {
            if (onProgress) onProgress(100);
            resolve(data);
          } else {
            reject(new Error(data.error || data.detail || 'Upload failed'));
          }
        } catch (err) {
          reject(err);
        }
      }
    };
    xhr.send(form);
  });
}

function AdminPage() {
  const [singleFile, setSingleFile] = React.useState(null);
  const [singleStatus, setSingleStatus] = React.useState(null);
  const [singleProgress, setSingleProgress] = React.useState(0);

  const [bulkFiles, setBulkFiles] = React.useState([]);
  const [bulkItems, setBulkItems] = React.useState([]);
  const [bulkBusy, setBulkBusy] = React.useState(false);

  const handleSingleChange = (e) => {
    const file = e.target.files?.[0] || null;
    setSingleFile(file);
    setSingleStatus(null);
    setSingleProgress(0);
  };

  const handleSingleUpload = async () => {
    if (!singleFile) return;
    setSingleStatus({ state: 'uploading', message: 'Uploading…' });
    try {
      const data = await uploadSingleFile(singleFile, setSingleProgress);
      const isVideo = isVideoFile(singleFile);
      setSingleStatus({
        state: 'done',
        message: isVideo
          ? 'Video uploaded and transcribed.'
          : 'Document uploaded and ingested.',
        data,
      });
    } catch (err) {
      setSingleStatus({
        state: 'error',
        message: err.message || String(err),
      });
    }
  };

  const handleBulkChange = (e) => {
    const files = Array.from(e.target.files || []);
    setBulkFiles(files);
    setBulkItems(
      files.map((f) => ({
        id: `${f.name}-${Math.random().toString(36).slice(2)}`,
        file: f,
        progress: 0,
        status: 'ready',
        detail: '',
      })),
    );
  };

  const handleBulkUpload = async () => {
    if (!bulkFiles.length) return;
    setBulkBusy(true);
    const updated = [...bulkItems];

    const updateItem = (idx, patch) => {
      updated[idx] = { ...updated[idx], ...patch };
      setBulkItems([...updated]);
    };

    for (let i = 0; i < bulkFiles.length; i += 1) {
      const file = bulkFiles[i];
      updateItem(i, { status: 'uploading', detail: '' });
      try {
        const data = await uploadSingleFile(file, (pct) =>
          updateItem(i, { progress: pct }),
        );
        const isVideo = isVideoFile(file);
        updateItem(i, {
          status: 'done',
          progress: 100,
          detail: isVideo
            ? 'Video uploaded and transcribed.'
            : 'Document uploaded and ingested.',
          data,
        });
      } catch (err) {
        updateItem(i, {
          status: 'error',
          detail: err.message || String(err),
        });
      }
    }

    setBulkBusy(false);
  };

  return (
    <Layout>
      <div className="page admin-page">
        <div className="page-header-row">
          <div>
            <h1>Admin Console</h1>
            <p>
              Upload CFC documents and videos for ingestion. Files are routed to
              the correct pipeline automatically.
            </p>
          </div>
        </div>

        <div className="admin-grid">
          <Card className="admin-card">
            <h2>Upload</h2>
            <p className="muted">
              Upload a single document or video. We&apos;ll detect the file type
              and ingest it appropriately.
            </p>
            <div className="file-picker">
              <input
                type="file"
                onChange={handleSingleChange}
                className="file-input"
              />
              {singleFile && (
                <div className="file-chip">
                  <span>{singleFile.name}</span>
                  <span className="file-chip-kind">
                    {isVideoFile(singleFile) ? 'Video' : 'Document'}
                  </span>
                </div>
              )}
            </div>
            {singleProgress > 0 && (
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${singleProgress}%` }}
                />
              </div>
            )}
            <div className="admin-actions">
              <PrimaryButton type="button" onClick={handleSingleUpload}>
                Upload &amp; ingest
              </PrimaryButton>
            </div>
            {singleStatus && (
              <div
                className={`status-pill status-${singleStatus.state || 'info'}`}
              >
                {singleStatus.message}
              </div>
            )}
          </Card>

          <Card className="admin-card">
            <h2>Bulk Upload</h2>
            <p className="muted">
              Select a collection of documents and videos. Each file is queued,
              uploaded, and ingested with progress tracking.
            </p>
            <div className="file-picker">
              <input
                type="file"
                multiple
                onChange={handleBulkChange}
                className="file-input"
              />
            </div>
            <div className="admin-actions">
              <PrimaryButton
                type="button"
                onClick={handleBulkUpload}
                disabled={bulkBusy || !bulkFiles.length}
              >
                {bulkBusy ? 'Uploading…' : 'Start bulk upload'}
              </PrimaryButton>
            </div>
            <div className="bulk-list">
              {bulkItems.map((item) => (
                <div key={item.id} className="bulk-item">
                  <div className="bulk-row">
                    <span className="bulk-name">{item.file.name}</span>
                    <span className={`bulk-status bulk-${item.status}`}>
                      {item.status === 'ready' && 'Ready'}
                      {item.status === 'uploading' && 'Uploading…'}
                      {item.status === 'done' && 'Ingested'}
                      {item.status === 'error' && 'Error'}
                    </span>
                  </div>
                  <div className="progress-bar small">
                    <div
                      className="progress-fill"
                      style={{ width: `${item.progress || 0}%` }}
                    />
                  </div>
                  {item.detail && (
                    <div className="bulk-detail">{item.detail}</div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </Layout>
  );
}

// ---- Chat Page ----
function formatTimecode(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return null;
  const total = Math.max(0, Math.floor(seconds));
  const hrs = Math.floor(total / 3600);
  const mins = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  const base = [hrs, mins, secs]
    .filter((v, idx) => v > 0 || idx > 0)
    .map((v) => String(v).padStart(2, '0'));
  return base.join(':');
}

function useModal() {
  const [content, setContent] = React.useState(null);
  const open = (c) => setContent(c);
  const close = () => setContent(null);

  const modal = content ? (
    <div className="modal-backdrop" onClick={close}>
      <div
        className="modal-body"
        onClick={(e) => e.stopPropagation()}
      >
        <button className="modal-close" type="button" onClick={close}>
          ×
        </button>
        {content}
      </div>
    </div>
  ) : null;

  return { open, close, modal };
}

function ChatMessage({ message, onImageClick, onVideoClick }) {
  const isUser = message.role === 'user';

  if (message.typing) {
    return (
      <div className="chat-message bot">
        <div className="chat-bubble typing-bubble">
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="typing-dot" />
        </div>
      </div>
    );
  }

  return (
    <div className={`chat-message ${isUser ? 'user' : 'bot'}`}>
      <div className="chat-bubble">
        {message.segments && message.segments.length ? (
          message.segments.map((seg, idx) => {
            if (seg.type === 'text') {
              return (
                <p key={idx} className="chat-text">
                  {seg.text}
                </p>
              );
            }
            if (seg.type === 'image') {
              return (
                <img
                  key={idx}
                  src={seg.url}
                  alt={seg.alt || 'Image'}
                  className="chat-image"
                  onClick={() => onImageClick && onImageClick(seg.url)}
                />
              );
            }
            if (seg.type === 'video') {
              return (
                <VideoBubble
                  key={idx}
                  segment={seg}
                  onVideoClick={onVideoClick}
                />
              );
            }
            return null;
          })
        ) : (
          <p className="chat-text">{message.text}</p>
        )}
      </div>
    </div>
  );
}

function VideoBubble({ segment, onVideoClick }) {
  const videoRef = React.useRef(null);

  const handleSeek = (sec) => {
    if (videoRef.current) {
      videoRef.current.currentTime = sec;
      videoRef.current.play();
    }
  };

  const timestamps = segment.timestamps || [];

  return (
    <div className="video-bubble">
      <video
        ref={videoRef}
        className="chat-video"
        controls
        onClick={() =>
          onVideoClick &&
          onVideoClick({
            url: segment.url,
            timestamps,
          })
        }
      >
        <source src={segment.url} type="video/mp4" />
      </video>
      {timestamps.length > 0 && (
        <div className="video-timestamps">
          {timestamps.map((ts, idx) => (
            <button
              key={idx}
              type="button"
              className="timestamp-chip"
              onClick={() => handleSeek(ts.seconds)}
            >
              {ts.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function buildVideoSegmentsFromAnswer(data) {
  const url =
    data.answer_video_url ||
    (Array.isArray(data.video_context) &&
      data.video_context[0]?.video_url);
  if (!url) return [];

  const timestamps = [];
  const start = data.answer_start_seconds ?? data.video_context?.[0]?.start_seconds;
  const end = data.answer_end_seconds ?? data.video_context?.[0]?.end_seconds;

  if (start != null && end != null && end > start) {
    const span = end - start;
    const step = span / 3;
    const points = [start, start + step, start + 2 * step, end];
    points.slice(0, 4).forEach((sec) => {
      const label = formatTimecode(sec);
      if (label) {
        timestamps.push({ seconds: sec, label });
      }
    });
  } else if (Array.isArray(data.video_context)) {
    data.video_context.slice(0, 4).forEach((clip) => {
      const sec = clip.start_seconds ?? 0;
      const label =
        clip.timestamp || formatTimecode(sec) || 'Clip';
      timestamps.push({ seconds: sec, label });
    });
  }

  return [
    {
      type: 'video',
      url,
      timestamps,
    },
  ];
}

function ChatPage() {
  const [messages, setMessages] = React.useState([]);
  const [input, setInput] = React.useState('');
  const [sending, setSending] = React.useState(false);
  const [attachedImages, setAttachedImages] = React.useState([]);

  const { open: openModal, modal } = useModal();

  const handleImageChange = (e) => {
    const files = Array.from(e.target.files || []);
    const previews = files.map((file) => ({
      file,
      url: URL.createObjectURL(file),
      id: `${file.name}-${Math.random().toString(36).slice(2)}`,
    }));
    setAttachedImages((prev) => [...prev, ...previews]);
  };

  const appendMessage = (msg) => {
    setMessages((prev) => [...prev, msg]);
  };

  const simulateStreaming = (fullText, baseMessageId, extraSegments = []) => {
    const chars = Array.from(fullText);
    let idx = 0;
    const speed = 18;

    const interval = setInterval(() => {
      idx += 3;
      const current = chars.slice(0, idx).join('');
      setMessages((prev) =>
        prev.map((m) =>
          m.id === baseMessageId
            ? {
                ...m,
                typing: false,
                text: current,
                segments: [{ type: 'text', text: current }, ...extraSegments],
              }
            : m,
        ),
      );
      if (idx >= chars.length) {
        clearInterval(interval);
      }
    }, speed);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const q = input.trim();
    if (!q || sending) return;

    const imageSegments = attachedImages.map((img) => ({
      type: 'image',
      url: img.url,
      alt: 'Attached image',
    }));

    const userMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      text: q,
      segments: [{ type: 'text', text: q }, ...imageSegments],
    };
    appendMessage(userMessage);

    const imagesForBackend = attachedImages.map((img) => img.url);

    setInput('');
    setAttachedImages([]);
    setSending(true);

    const botId = `b-${Date.now()}`;
    appendMessage({
      id: botId,
      role: 'assistant',
      text: '',
      segments: [],
      typing: true,
    });

    try {
      const res = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: q + (imagesForBackend.length ? ` (images: ${imagesForBackend.join(', ')})` : ''),
          top_k: 4,
        }),
      });
      const data = await res.json();
      if (!data.success) {
        throw new Error(data.detail || 'Error from assistant');
      }

      const answer = data.answer || 'No answer available.';
      const videoSegments = buildVideoSegmentsFromAnswer(data);
      simulateStreaming(answer, botId, videoSegments);
    } catch (err) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === botId
            ? {
                ...m,
                typing: false,
                text: err.message || String(err),
                segments: [{ type: 'text', text: err.message || String(err) }],
              }
            : m,
        ),
      );
    } finally {
      setSending(false);
    }
  };

  const handleImageClick = (url) => {
    openModal(
      <img src={url} alt="Preview" className="modal-image" />,
    );
  };

  const handleVideoClick = ({ url, timestamps }) => {
    openModal(
      <div className="modal-video-wrapper">
        <video src={url} className="modal-video" controls autoPlay />
        {timestamps && timestamps.length > 0 && (
          <div className="video-timestamps">
            {timestamps.map((ts, idx) => (
              <span key={idx} className="timestamp-chip static">
                {ts.label}
              </span>
            ))}
          </div>
        )}
      </div>,
    );
  };

  return (
    <Layout>
      <div className="page chat-page">
        <div className="page-header-row">
          <div>
            <h1>Chat with CFC AI</h1>
            <p>
              Ask questions about your software and get quick, informed answers.
            </p>
          </div>
        </div>

        <Card className="chat-card">
          <div className="chat-thread" id="chatThread">
            {messages.map((m) => (
              <ChatMessage
                key={m.id}
                message={m}
                onImageClick={handleImageClick}
                onVideoClick={handleVideoClick}
              />
            ))}
          </div>
          <form className="chat-composer" onSubmit={handleSubmit}>
            <div className="composer-row">
              <input
                type="text"
                className="composer-input"
                placeholder="Ask anything about CFC software…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
              />
              <label className="btn-primary composer-button" title="Attach images">
                <span>Attach</span>
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleImageChange}
                />
              </label>
              <button
                type="submit"
                className="btn-primary composer-button"
                disabled={sending}
              >
                {sending ? 'Sending…' : 'Send'}
              </button>
            </div>
            {attachedImages.length > 0 && (
              <div className="attached-images">
                {attachedImages.map((img) => (
                  <img
                    key={img.id}
                    src={img.url}
                    alt="Attachment"
                    className="attached-thumb"
                    onClick={() => handleImageClick(img.url)}
                  />
                ))}
              </div>
            )}
          </form>
        </Card>
      </div>
      {modal}
    </Layout>
  );
}

// ---- App & routing ----
function App() {
  return (
    <UserProvider>
      <RouterProvider>
        <AppRoutes />
      </RouterProvider>
    </UserProvider>
  );
}

function AppRoutes() {
  const { route } = useRouter();

  if (route === 'transition') return <TransitionPage />;
  if (route === 'docs') return <DocsPage />;
  if (route === 'admin') return <AdminPage />;
  if (route === 'chat') return <ChatPage />;

  return <LoginPage />;
}

function TransitionPage() {
  const { user } = useUser();
  const { nextRoute, navigate } = useRouter();

  React.useEffect(() => {
    const id = setTimeout(() => {
      navigate(nextRoute || 'login', { withFade: true });
    }, 1800);
    return () => clearTimeout(id);
  }, [nextRoute, navigate]);

  const firstName = (user?.name || 'there').split(' ')[0];

  return (
    <Layout>
      <div className="page transition-screen">
        <div className="transition-inner standalone">
          <h1 className="transition-title">Welcome, {firstName}!</h1>
          <p className="muted">
            We&apos;re getting everything ready for you.
            <br />
            This will only take a moment.
          </p>
          <div className="transition-pill">Preparing your workspace</div>
          <div className="transition-loader">
            <div className="dot" />
            <div className="dot" />
            <div className="dot" />
          </div>
        </div>
      </div>
    </Layout>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);


