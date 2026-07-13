import { useEffect, useState } from 'react'
import type { FormatInfo, UploadResult } from './api'
import { convertFiles, fetchFormats, uploadFiles } from './api'
import ConvertPanel from './components/ConvertPanel'
import DropZone from './components/DropZone'
import FileCard, { type ConvertState } from './components/FileCard'

export default function App() {
  const [formats, setFormats] = useState<FormatInfo[]>([])
  const [files, setFiles] = useState<UploadResult[]>([])
  const [uploading, setUploading] = useState(false)
  const [converting, setConverting] = useState(false)
  const [convertStates, setConvertStates] = useState<Record<string, ConvertState>>({})
  const [globalError, setGlobalError] = useState<string | null>(null)

  useEffect(() => {
    fetchFormats()
      .then(setFormats)
      .catch(() =>
        setGlobalError('Cannot reach the backend on port 8000 — is the server running?'),
      )
  }, [])

  async function handleFiles(selected: File[]) {
    setUploading(true)
    setGlobalError(null)
    try {
      const results = await uploadFiles(selected)
      setFiles((prev) => [...prev, ...results])
    } catch (err) {
      setGlobalError((err as Error).message)
    } finally {
      setUploading(false)
    }
  }

  async function handleConvert(targetFormat: string, targetEpsg: number | null) {
    const ids = files.map((f) => f.file_id).filter((id): id is string => !!id)
    if (!ids.length) return
    setConverting(true)
    setConvertStates(Object.fromEntries(ids.map((id) => [id, { status: 'converting' }])))
    try {
      const results = await convertFiles(
        ids.map((id) => ({ file_id: id, target_format: targetFormat, target_epsg: targetEpsg })),
      )
      setConvertStates(
        Object.fromEntries(results.map((r) => [r.file_id, { status: 'done', result: r }])),
      )
    } catch (err) {
      setGlobalError((err as Error).message)
      setConvertStates({})
    } finally {
      setConverting(false)
    }
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  return (
    <div className="app">
      <header className="app__header">
        <h1>Vector Format Converter</h1>
        <p>Convert between Shapefile, GeoPackage, GeoParquet, GeoJSON, FlatGeobuf, KML and CSV — with optional reprojection.</p>
      </header>

      {globalError && <div className="msg msg--error">{globalError}</div>}

      <DropZone onFiles={handleFiles} busy={uploading} />

      {files.length > 0 && (
        <>
          <ConvertPanel
            formats={formats}
            fileCount={files.filter((f) => f.file_id).length}
            busy={converting}
            onConvert={handleConvert}
          />
          <div className="cards">
            {files.map((f, i) => (
              <FileCard
                key={f.file_id ?? `err-${i}`}
                file={f}
                convertState={
                  (f.file_id && convertStates[f.file_id]) || { status: 'idle' }
                }
                onRemove={() => removeFile(i)}
              />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
