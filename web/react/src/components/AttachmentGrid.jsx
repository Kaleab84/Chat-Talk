export default function AttachmentGrid({ attachments = [], onImageClick }) {
  if (!attachments.length) return null;
  return (
    <div className='img-grid'>
      {attachments.map((att) => (
        <button
          type='button'
          key={att.id}
          className='img-grid-btn'
          onClick={() => onImageClick?.(att)}
        >
          <img src={att.previewUrl} alt={att.name || 'attachment'} />
        </button>
      ))}
    </div>
  );
}
