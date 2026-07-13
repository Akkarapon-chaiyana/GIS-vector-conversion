import { useCallback, useRef, useState } from 'react'

const ACCEPT = '.zip,.shp,.gpkg,.parquet,.geoparquet,.geojson,.json,.fgb,.kml,.csv'

export default function DropZone({
  onFiles,
  busy,
}: {
  onFiles: (files: File[]) => void
  busy: boolean
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const files = Array.from(e.dataTransfer.files)
      if (files.length) onFiles(files)
    },
    [onFiles],
  )

  return (
    <div
      className={`dropzone ${dragOver ? 'dropzone--over' : ''} ${busy ? 'dropzone--busy' : ''}`}
      onDragOver={(e) => {
        e.preventDefault()
        setDragOver(true)
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPT}
        hidden
        onChange={(e) => {
          const files = Array.from(e.target.files ?? [])
          if (files.length) onFiles(files)
          e.target.value = ''
        }}
      />
      <div className="dropzone__icon">🗺️</div>
      <div className="dropzone__title">
        {busy ? 'Uploading…' : 'Drop GIS files here or click to browse'}
      </div>
      <div className="dropzone__hint">
        Shapefile (.zip) · GeoPackage · GeoParquet · GeoJSON · FlatGeobuf · KML · CSV
      </div>
    </div>
  )
}
