import { useEffect, useState } from 'react'
import api from '../api'
import DownloadMenu from './DownloadMenu'
import PanelToolbar from './PanelToolbar'

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function DocumentPanel({ jobId, completed }) {
  const [docs, setDocs] = useState([])
  const [selected, setSelected] = useState(null)
  const [preview, setPreview] = useState('')
  const [loadingList, setLoadingList] = useState(true)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [error, setError] = useState('')
  const [fullscreen, setFullscreen] = useState(false)

  useEffect(() => {
    setSelected(null)
    setLoadingList(true)
    setError('')
    api.get(`/audits/${jobId}/documents`)
      .then(({ data }) => {
        const list = Array.isArray(data) ? data : []
        setDocs(list)
        if (list.length) {
          const preferred = list.find((d) => d.name === 'audit-bugs.md')
            || list.find((d) => d.previewable)
            || list[0]
          setSelected(preferred?.name || null)
        }
      })
      .catch(() => setError('无法加载文档列表'))
      .finally(() => setLoadingList(false))
  }, [jobId, completed])

  useEffect(() => {
    if (!selected) {
      setPreview('')
      return undefined
    }
    const doc = docs.find((d) => d.name === selected)
    if (!doc?.previewable) {
      setPreview('该文件不支持在线预览，请使用「下载」按钮。')
      return undefined
    }
    let mounted = true
    setLoadingPreview(true)
    api.get(`/audits/${jobId}/documents/${encodeURIComponent(selected)}/preview`)
      .then(({ data }) => {
        if (mounted) setPreview(data.content || '')
      })
      .catch(() => {
        if (mounted) setPreview('预览加载失败')
      })
      .finally(() => {
        if (mounted) setLoadingPreview(false)
      })
    return () => { mounted = false }
  }, [jobId, selected, docs])

  useEffect(() => {
    if (!fullscreen) return undefined
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [fullscreen])

  if (loadingList) {
    return <div className="card doc-panel"><p className="hint">加载文档列表…</p></div>
  }

  if (!docs.length) {
    return (
      <div className="card doc-panel">
        <p className="hint">
          {completed ? '暂无审计产物文档。' : '审计进行中，文档将在任务完成后生成（如 audit-bugs.md、audit-summary.json）。'}
        </p>
      </div>
    )
  }

  const current = docs.find((d) => d.name === selected)

  return (
    <div className={`card doc-panel ${fullscreen ? 'panel-fullscreen' : ''}`}>
      <PanelToolbar
        title="审计文档"
        subtitle={selected || undefined}
        fullscreen={fullscreen}
        onToggleFullscreen={() => setFullscreen((v) => !v)}
        extra={<DownloadMenu jobId={jobId} filename={selected} disabled={!selected} />}
      />
      {error && <div className="error">{error}</div>}
      <div className="doc-split doc-split-fill">
        <div className="doc-list-panel">
          <h4 className="section-title">产物文件</h4>
          {docs.map((doc) => (
            <button
              key={doc.name}
              type="button"
              className={selected === doc.name ? 'doc-item active' : 'doc-item'}
              onClick={() => setSelected(doc.name)}
            >
              <span className="doc-item-name">{doc.name}</span>
              <span className="hint">{formatSize(doc.size)}</span>
            </button>
          ))}
        </div>
        <div className="preview-panel card">
          <div className="preview-panel-header">
            <div>
              <h3>{selected || '选择文件'}</h3>
              {current && (
                <p className="hint preview-subtitle">
                  {formatSize(current.size)}
                  {current.previewable ? ' · 可预览' : ' · 仅下载'}
                </p>
              )}
            </div>
          </div>
          <div className="preview-panel-body">
            {loadingPreview ? (
              <p className="hint">加载预览…</p>
            ) : (
              <pre className="doc-preview-pre">{preview || '请选择左侧文件'}</pre>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
