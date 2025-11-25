import { useRef, useState } from 'react';

const icon = String.fromCodePoint(0x1f4e4); // inbox tray

export default function Dropzone({ onFileSelected }) {
  const inputRef = useRef(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFiles = (files) => {
    if (!files?.length) return;
    onFileSelected?.(files[0]);
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  return (
    <div
      className={`dropzone ${isDragOver ? 'dragover' : ''}`}
      role="button"
      tabIndex={0}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          inputRef.current?.click();
        }
      }}
      onDragOver={(event) => {
        event.preventDefault();
        setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setIsDragOver(false);
        handleFiles(event.dataTransfer?.files ? Array.from(event.dataTransfer.files) : []);
      }}
    >
      <div className="dz-inner">
        <div className="dz-icon" aria-hidden="true">{icon}</div>
        <div>Drag & drop file, or <span className="link">browse</span></div>
      </div>
      <input
        ref={inputRef}
        type="file"
        hidden
        onChange={(event) => handleFiles(event.target.files ? Array.from(event.target.files) : [])}
      />
    </div>
  );
}
