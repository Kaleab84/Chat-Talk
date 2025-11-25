export default function AttachmentPreview({ attachments = [], onRemove }) {
  if (!attachments.length) return null;
  return (
    <div className='attachment-strip'>
      {attachments.map((att) => (
        <div key={att.id} className='attachment-chip'>
          <img src={att.previewUrl} alt={att.name || 'attachment'} />
          <div className='attachment-meta'>
            <div className='attachment-name'>{att.name || 'Attachment'}</div>
            <button type='button' onClick={() => onRemove?.(att.id)} aria-label={`Remove ${att.name || 'attachment'}`}>
              ×
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
