import { useState } from 'react'
import type { ConvertResult, UploadResult } from '../api'
import { downloadUrl } from '../api'
import MapPreview from './MapPreview'

export type ConvertState =
  | { status: 'idle' }
  | { status: 'converting' }
  | { status: 'done'; result: ConvertResult }

export default function FileCard({
  file,
  convertState,
  onRemove,
}: {
  file: UploadResult
  convertState: ConvertState
  onRemove: () => void
}) {
  const [showColumns, setShowColumns] = useState(false)
  const [showMap, setShowMap] = useState(false)

  if (file.error) {
    return (
      <div className="card card--error">
        <div className="card__header">
          <span className="card__name">{file.filename}</span>
          <button className="card__remove" onClick={onRemove} title="Remove">
            ✕
          </button>
        </div>
        <div className="msg msg--error">{file.error}</div>
      </div>
    )
  }

  const crsLabel = file.crs
    ? file.crs.epsg
      ? `EPSG:${file.crs.epsg} (${file.crs.name})`
      : file.crs.name
    : 'Unknown'

  return (
    <div className="card">
      <div className="card__header">
        <span className="card__name">{file.filename}</span>
        <span className="chip">{file.format_label}</span>
        <button className="card__remove" onClick={onRemove} title="Remove">
          ✕
        </button>
      </div>

      <div className="card__meta">
        <div>
          <span className="meta__label">Geometry</span>
          {file.geometry_types?.join(', ') || '—'}
        </div>
        <div>
          <span className="meta__label">Features</span>
          {file.feature_count?.toLocaleString()}
        </div>
        <div>
          <span className="meta__label">CRS</span>
          <span className={file.crs ? '' : 'text-warn'}>{crsLabel}</span>
        </div>
      </div>

      {file.warnings?.map((w, i) => (
        <div key={i} className="msg msg--warn">
          {w}
        </div>
      ))}

      <div className="card__actions">
        <button className="btn btn--ghost" onClick={() => setShowColumns((v) => !v)}>
          {showColumns ? 'Hide' : 'Show'} attributes ({file.columns?.length ?? 0})
        </button>
        <button className="btn btn--ghost" onClick={() => setShowMap((v) => !v)}>
          {showMap ? 'Hide' : 'Show'} map
        </button>
      </div>

      {showColumns && (
        <table className="columns-table">
          <thead>
            <tr>
              <th>Column</th>
              <th>Type</th>
            </tr>
          </thead>
          <tbody>
            {file.columns?.map((c) => (
              <tr key={c.name}>
                <td className={c.name.length > 10 ? 'text-warn' : ''}>{c.name}</td>
                <td>{c.dtype}</td>
              </tr>
            ))}
            {!file.columns?.length && (
              <tr>
                <td colSpan={2}>No attribute columns</td>
              </tr>
            )}
          </tbody>
        </table>
      )}

      {showMap && file.file_id && <MapPreview fileId={file.file_id} />}

      {convertState.status === 'converting' && (
        <div className="msg msg--info">Converting…</div>
      )}
      {convertState.status === 'done' && convertState.result.error && (
        <div className="msg msg--error">{convertState.result.error}</div>
      )}
      {convertState.status === 'done' && convertState.result.output_id && (
        <div className="card__result">
          {convertState.result.warnings?.map((w, i) => (
            <div key={i} className="msg msg--warn">
              {w}
            </div>
          ))}
          <a
            className="btn btn--primary"
            href={downloadUrl(convertState.result.output_id)}
            download
          >
            ⬇ Download {convertState.result.output_filename}
          </a>
        </div>
      )}
    </div>
  )
}
