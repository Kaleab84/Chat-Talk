import { useCallback, useEffect, useRef, useState } from 'react';
import { getGreeting } from './utils/displayName.js';
import MessageList from './components/MessageList.jsx';
import AttachmentPreview from './components/AttachmentPreview.jsx';
import ImageModal from './components/ImageModal.jsx';

const createId = () => {
  const cryptoRef = typeof globalThis !== 'undefined' ? globalThis.crypto : null;
  if (cryptoRef?.randomUUID) return cryptoRef.randomUUID();
  return `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const createTimestamp = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

export default function ChatApp() {
  const [greeting, setGreeting] = useState(() => getGreeting());
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [pendingAttachments, setPendingAttachments] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [modalImage, setModalImage] = useState(null);
  const fileInputRef = useRef(null);
  const streamingTimersRef = useRef(new Map());

  useEffect(() => {
    setGreeting(getGreeting());
  }, []);

  useEffect(() => {
    return () => {
      streamingTimersRef.current.forEach((timerId) => clearTimeout(timerId));
      streamingTimersRef.current.clear();
    };
  }, []);

  const addAttachments = useCallback((files) => {
    if (!files?.length) return;
    const enriched = files.map((file) => ({
      id: createId(),
      name: file.name || 'attachment',
      previewUrl: URL.createObjectURL(file),
      file,
    }));
    setPendingAttachments((prev) => [...prev, ...enriched]);
  }, []);

  const handleFileChange = (event) => {
    const files = Array.from(event.target.files || []);
    addAttachments(files);
    event.target.value = '';
  };

  const removeAttachment = (id) => {
    setPendingAttachments((prev) => {
      const target = prev.find((att) => att.id === id);
      if (target?.previewUrl) {
        try {
          URL.revokeObjectURL(target.previewUrl);
        } catch {}
      }
      return prev.filter((att) => att.id !== id);
    });
  };

  const clearAttachments = () => {
    setPendingAttachments([]);
  };

  const stopStreamingForMessage = useCallback((messageId) => {
    const timerId = streamingTimersRef.current.get(messageId);
    if (timerId) {
      clearTimeout(timerId);
      streamingTimersRef.current.delete(messageId);
    }
  }, []);

  const streamAssistantText = useCallback(
    (messageId, content, extraMeta = {}) => {
      const safeContent =
        typeof content === 'string' ? content : content != null ? String(content) : '';
      const chars = Array.from(safeContent);
      const streamingTimestamp = extraMeta.timestamp ?? createTimestamp();

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === messageId
            ? {
                ...msg,
                ...extraMeta,
                text: '',
                isTyping: false,
                isStreaming: true,
                timestamp: streamingTimestamp,
              }
            : msg
        )
      );

      if (!chars.length) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === messageId ? { ...msg, text: '', isStreaming: false } : msg
          )
        );
        return;
      }

      const chunkSize = (() => {
        if (chars.length < 80) return 1;
        if (chars.length < 200) return 2;
        if (chars.length < 400) return 3;
        if (chars.length < 800) return 5;
        return 8;
      })();
      const baseDelay = chars.length > 400 ? 10 : 19;
      let index = 0;

      const emitNextChunk = () => {
        const nextIndex = Math.min(chars.length, index + chunkSize);
        const chunk = chars.slice(index, nextIndex).join('');
        index = nextIndex;
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === messageId ? { ...msg, text: `${msg.text || ''}${chunk}` } : msg
          )
        );

        if (index >= chars.length) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === messageId ? { ...msg, isStreaming: false } : msg
            )
          );
          stopStreamingForMessage(messageId);
          return;
        }

        const delay = baseDelay + Math.random() * baseDelay;
        const timerId = setTimeout(emitNextChunk, delay);
        streamingTimersRef.current.set(messageId, timerId);
      };

      stopStreamingForMessage(messageId);
      const timerId = setTimeout(emitNextChunk, 40);
      streamingTimersRef.current.set(messageId, timerId);
    },
    [stopStreamingForMessage]
  );

  const sendQuestion = async () => {
    const trimmed = question.trim();
    const attachmentsSnapshot = pendingAttachments;
    if (!trimmed && !attachmentsSnapshot.length) return;

    const userMessage = {
      id: createId(),
      role: 'user',
      text: trimmed,
      attachments: attachmentsSnapshot.map((att) => ({ id: att.id, name: att.name, previewUrl: att.previewUrl })),
      timestamp: createTimestamp(),
    };
    const typingId = createId();
    setMessages((prev) => [
      ...prev,
      userMessage,
      {
        id: typingId,
        role: 'assistant',
        text: 'Assistant is thinking…',
        isTyping: true,
      },
    ]);
    setQuestion('');
    setIsSending(true);
    setPendingAttachments([]);

    try {
      let data;
      if (attachmentsSnapshot.length) {
        const formData = new FormData();
        formData.append('question', trimmed);
        formData.append('top_k', '4');
        attachmentsSnapshot.forEach((att) => formData.append('images', att.file));
        const res = await fetch('/ask-with-media', { method: 'POST', body: formData });
        data = await res.json();
      } else {
        const res = await fetch('/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: trimmed, top_k: 4 }),
        });
        data = await res.json();
      }

      const answer = data?.success ? data.answer || 'No answer provided yet.' : data?.detail || 'Request failed.';
      if (data?.success) {
        streamAssistantText(typingId, answer, { isError: false });
      } else {
        stopStreamingForMessage(typingId);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === typingId
              ? {
                  ...msg,
                  text: answer,
                  isTyping: false,
                  isError: true,
                  timestamp: createTimestamp(),
                }
              : msg
          )
        );
      }
    } catch (error) {
      stopStreamingForMessage(typingId);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === typingId
            ? {
                ...msg,
                text: String(error),
                isTyping: false,
                isError: true,
                timestamp: createTimestamp(),
              }
            : msg
        )
      );
    } finally {
      setIsSending(false);
      clearAttachments();
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    sendQuestion();
  };

  const openImageModal = (attachment) => setModalImage(attachment);
  const closeImageModal = () => setModalImage(null);

  return (
    <div className='react-app'>
      <header className='container header react-header'>
        <div className='brand'>CFC Software Support</div>
        <div className='greet'>{greeting ? `Hi, ${greeting}!` : 'Welcome back'}</div>
      </header>

      <main className='container chat-container'>
        <section className='panel active chat-panel'>
          <div className='panel-body chat-panel-body'>
            <h2>Chat with AI Assistant</h2>
            <MessageList messages={messages} onImageClick={openImageModal} />
            <AttachmentPreview attachments={pendingAttachments} onRemove={removeAttachment} />
            <form className='chat-input react-chat-input' onSubmit={handleSubmit}>
              <input
                type='text'
                placeholder='Ask anything about CFC software…'
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                disabled={isSending}
              />
              <input
                ref={fileInputRef}
                type='file'
                accept='image/*'
                multiple
                hidden
                onChange={handleFileChange}
              />
              <button
                type='button'
                className='btn icon'
                onClick={() => fileInputRef.current?.click()}
                aria-label='Attach images'
                disabled={isSending}
              >
                <svg viewBox='0 0 24 24' aria-hidden='true' focusable='false'>
                  <path d='M21 8.5l-9.19 9.19a5 5 0 01-7.07 0h0a5 5 0 010-7.07L13.5 1.75a3.5 3.5 0 114.95 4.95L8.3 16.86a2 2 0 01-2.83 0h0a2 2 0 010-2.83L15.2 4.31' fill='none' strokeLinecap='round' strokeLinejoin='round' />
                </svg>
              </button>
              <button className='btn icon' type='submit' disabled={isSending} aria-label='Send message'>
                <svg viewBox='0 0 24 24' aria-hidden='true' focusable='false'>
                  <path d='M3 11.5l18-8-8 18-2.5-6.5L3 11.5z' fill='none' strokeLinecap='round' strokeLinejoin='round' />
                </svg>
              </button>
            </form>
            <div className='meta'>
              {pendingAttachments.length
                ? `${pendingAttachments.length} image${pendingAttachments.length > 1 ? 's' : ''} ready to send`
                : 'Images are optional. Upload screenshots for richer answers.'}
            </div>
          </div>
        </section>
      </main>

      <footer className='container footer'>
        <a className='btn' href='/ui/login.html' aria-label='Back to Login'>
          Back to Login
        </a>
      </footer>
      <ImageModal image={modalImage} onClose={closeImageModal} />
    </div>
  );
}
