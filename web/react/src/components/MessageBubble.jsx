import AttachmentGrid from './AttachmentGrid.jsx';

export default function MessageBubble({ message, onImageClick }) {
  const role = message.role === 'user' ? 'user' : 'bot';
  const className = ['msg', role];
  if (message.isTyping) className.push('typing');
  if (message.isError) className.push('err');

  const textContent = message.isTyping ? (
    <span className='typing-text'>
      Assistant is thinking<span className='dots'></span>
    </span>
  ) : (
    message.text
  );

  return (
    <div className={className.join(' ')}>
      <p className='msg-text'>{textContent}</p>
      {role === 'user' && Array.isArray(message.attachments) && message.attachments.length ? (
        <AttachmentGrid attachments={message.attachments} onImageClick={onImageClick} />
      ) : null}
      {message.timestamp ? <div className='meta'>{message.timestamp}</div> : null}
    </div>
  );
}
