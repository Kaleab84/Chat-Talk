import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble.jsx';

export default function MessageList({ messages = [], onImageClick }) {
  const listRef = useRef(null);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages]);

  return (
    <div className='thread' ref={listRef} aria-live='polite' aria-relevant='additions'>
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} onImageClick={onImageClick} />
      ))}
    </div>
  );
}
