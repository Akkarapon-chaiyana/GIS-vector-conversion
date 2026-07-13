import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { fetchPreview } from '../api'

export default function MapPreview({ fileId }: { fileId: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const [status, setStatus] = useState<string>('Loading preview…')
  const [full, setFull] = useState(false)

  useEffect(() => {
    if (!containerRef.current) return
    const map = L.map(containerRef.current, { zoomControl: true })
    mapRef.current = map
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map)
    map.setView([0, 0], 2)

    let cancelled = false
    fetchPreview(fileId)
      .then((preview) => {
        if (cancelled) return
        const layer = L.geoJSON(preview.geojson, {
          style: { color: '#2563eb', weight: 2, fillOpacity: 0.15 },
          pointToLayer: (_f, latlng) =>
            L.circleMarker(latlng, {
              radius: 5,
              color: '#2563eb',
              fillColor: '#3b82f6',
              fillOpacity: 0.7,
            }),
        }).addTo(map)
        const bounds = layer.getBounds()
        if (bounds.isValid()) map.fitBounds(bounds.pad(0.1))
        setStatus(
          [
            preview.sampled ? 'Showing a 2,000-feature sample.' : '',
            preview.no_crs ? 'CRS unknown — coordinates shown as-is.' : '',
          ]
            .filter(Boolean)
            .join(' '),
        )
      })
      .catch((err) => {
        if (!cancelled) setStatus(`Preview failed: ${err.message}`)
      })

    return () => {
      cancelled = true
      mapRef.current = null
      map.remove()
    }
  }, [fileId])

  // Leaflet needs to re-measure its container when the size changes.
  useEffect(() => {
    mapRef.current?.invalidateSize()
    if (!full) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setFull(false)
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [full])

  return (
    <div className={`map-preview ${full ? 'map-preview--full' : ''}`}>
      <div className="map-preview__frame">
        <div ref={containerRef} className="map-preview__map" />
        <button
          className="map-preview__expand"
          onClick={() => setFull((v) => !v)}
          title={full ? 'Exit full screen (Esc)' : 'Full screen'}
        >
          {full ? '✕ Exit full screen' : '⛶ Full screen'}
        </button>
      </div>
      {status && <div className="map-preview__status">{status}</div>}
    </div>
  )
}
