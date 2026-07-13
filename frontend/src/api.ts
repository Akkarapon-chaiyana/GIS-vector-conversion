export interface ColumnInfo {
  name: string
  dtype: string
}

export interface CrsInfo {
  epsg: number | null
  name: string
}

export interface UploadResult {
  filename: string
  error?: string
  file_id?: string
  format?: string
  format_label?: string
  geometry_types?: string[]
  feature_count?: number
  crs?: CrsInfo | null
  columns?: ColumnInfo[]
  bbox?: number[] | null
  bbox4326?: number[] | null
  warnings?: string[]
}

export interface ConvertResult {
  file_id: string
  output_id?: string
  output_filename?: string
  warnings?: string[]
  error?: string
}

export interface FormatInfo {
  key: string
  label: string
  extensions: string[]
}

export interface PreviewResult {
  sampled: boolean
  no_crs: boolean
  geojson: GeoJSON.FeatureCollection
}

export async function fetchFormats(): Promise<FormatInfo[]> {
  const res = await fetch('/api/formats')
  if (!res.ok) throw new Error(`Failed to load formats (${res.status})`)
  return res.json()
}

export async function uploadFiles(files: File[]): Promise<UploadResult[]> {
  const form = new FormData()
  for (const f of files) form.append('files', f)
  const res = await fetch('/api/upload', { method: 'POST', body: form })
  if (!res.ok) throw new Error(`Upload failed (${res.status})`)
  return res.json()
}

export async function convertFiles(
  requests: { file_id: string; target_format: string; target_epsg?: number | null }[],
): Promise<ConvertResult[]> {
  const res = await fetch('/api/convert', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requests),
  })
  if (!res.ok) throw new Error(`Convert failed (${res.status})`)
  return res.json()
}

export async function fetchPreview(fileId: string): Promise<PreviewResult> {
  const res = await fetch(`/api/files/${fileId}/preview`)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `Preview failed (${res.status})`)
  }
  return res.json()
}

export function downloadUrl(outputId: string): string {
  return `/api/download/${outputId}`
}
