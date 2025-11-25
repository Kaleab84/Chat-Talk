import { useEffect } from 'react';

export default function ImageModal({ image, onClose }) {
  useEffect(() => {
    if (!image) return undefined;
    const handler = (event) => {
      if (event.key === 'Escape') onClose?.();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [image, onClose]);

  return (
    <div
      className={`img-modal ${image ? 'active' : ''}`}
      onClick={() => onClose?.()}
      role='dialog'
      aria-label='Image preview'
      aria-modal='true'
    >
      {image ? (
        <img src={image.previewUrl} alt={image.name || 'attachment preview'} onClick={(event) => event.stopPropagation()} />
      ) : null}
    </div>
  );
}
