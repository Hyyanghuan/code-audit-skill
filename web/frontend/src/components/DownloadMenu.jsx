import { useEffect, useRef, useState } from 'react'
import { downloadFile } from '../api'

const FORMATS = [
  { id: 'md', label: 'Markdown (.md)' },
  { id: 'csv', label: 'CSV (.csv)' },
  { id: 'xlsx', label: 'Excel (.xlsx)' },
]

export default function DownloadMenu({ jobId, filename, disabled }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const onDoc = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('click', onDoc)
    return () => document.removeEventListener('click', onDoc)
  }, [])

  if (!filename || disabled) return null

  return (
    <div className="download-menu" ref={ref}>
      <button type="button" className="btn sm" onClick={() => setOpen((v) => !v)}>
        下载 ▾
      </button>
      {open && (
        <div className="download-dropdown">
          <p className="hint dropdown-title">选择下载格式</p>
          {FORMATS.map((f) => (
            <button
              key={f.id}
              type="button"
              className="dropdown-item"
              onClick={() => {
                downloadFile(jobId, filename, f.id)
                setOpen(false)
              }}
            >
              {f.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
