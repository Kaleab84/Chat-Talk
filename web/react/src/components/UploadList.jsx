const formatProgress = (value) => {
  if (typeof value !== 'number' || Number.isNaN(value)) return 0;
  return Math.min(100, Math.max(0, value));
};

export default function UploadList({ items = [], emptyMessage = 'No uploads yet.' }) {
  if (!items.length) {
    return <p className="meta">{emptyMessage}</p>;
  }

  return (
    <div className="results react-items">
      {items.map((item) => (
        <div key={item.id} className="item">
          <div className="row">
            <div className="name">{item.name}</div>
            <div
              className={`meta ${item.isSuccess ? 'ok' : item.isError ? 'err' : ''}`}
              data-status
            >
              {item.status}
            </div>
          </div>
          <div className="bar">
            <div className="fill" data-fill style={{ width: `${formatProgress(item.progress)}%` }} />
          </div>
          {item.detail ? (
            <div className={`meta ${item.isError ? 'err' : ''}`} data-detail>
              {item.detail}
            </div>
          ) : null}
          {Array.isArray(item.extra)
            ? item.extra.map((line, idx) => (
                <div key={idx} className="meta">
                  {line}
                </div>
              ))
            : null}
        </div>
      ))}
    </div>
  );
}
