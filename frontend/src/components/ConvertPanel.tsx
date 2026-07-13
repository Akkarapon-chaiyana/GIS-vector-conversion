import { useState } from 'react'
import type { FormatInfo } from '../api'

const EPSG_PRESETS = [
  { value: '', label: 'Keep source CRS' },
  { value: '4326', label: 'EPSG:4326 — WGS84 (lat/lon)' },
  { value: '3857', label: 'EPSG:3857 — Web Mercator' },
  { value: '32647', label: 'EPSG:32647 — UTM zone 47N (Thailand)' },
  { value: '32648', label: 'EPSG:32648 — UTM zone 48N' },
  { value: 'custom', label: 'Custom EPSG…' },
]

export default function ConvertPanel({
  formats,
  fileCount,
  busy,
  onConvert,
}: {
  formats: FormatInfo[]
  fileCount: number
  busy: boolean
  onConvert: (targetFormat: string, targetEpsg: number | null) => void
}) {
  const [format, setFormat] = useState('geopackage')
  const [epsgChoice, setEpsgChoice] = useState('')
  const [customEpsg, setCustomEpsg] = useState('')

  const epsgValue = epsgChoice === 'custom' ? customEpsg : epsgChoice
  const epsg = epsgValue ? parseInt(epsgValue, 10) : null
  const epsgInvalid = epsgChoice === 'custom' && (!customEpsg || Number.isNaN(epsg))

  return (
    <div className="convert-panel">
      <div className="convert-panel__field">
        <label htmlFor="fmt">Convert to</label>
        <select id="fmt" value={format} onChange={(e) => setFormat(e.target.value)}>
          {formats.map((f) => (
            <option key={f.key} value={f.key}>
              {f.label}
            </option>
          ))}
        </select>
      </div>
      <div className="convert-panel__field">
        <label htmlFor="epsg">Coordinate system</label>
        <select id="epsg" value={epsgChoice} onChange={(e) => setEpsgChoice(e.target.value)}>
          {EPSG_PRESETS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </div>
      {epsgChoice === 'custom' && (
        <div className="convert-panel__field">
          <label htmlFor="custom-epsg">EPSG code</label>
          <input
            id="custom-epsg"
            type="number"
            placeholder="e.g. 25832"
            value={customEpsg}
            onChange={(e) => setCustomEpsg(e.target.value)}
          />
        </div>
      )}
      <button
        className="btn btn--primary convert-panel__go"
        disabled={busy || fileCount === 0 || epsgInvalid}
        onClick={() => onConvert(format, epsg)}
      >
        {busy
          ? 'Converting…'
          : fileCount > 1
            ? `Convert all ${fileCount} files`
            : 'Convert'}
      </button>
    </div>
  )
}
