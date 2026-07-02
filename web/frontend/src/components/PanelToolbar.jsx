export default function PanelToolbar({
  title,
  subtitle,
  fullscreen,
  onToggleFullscreen,
  onDownload,
  downloadLabel = '下载 MD',
  extra,
}) {
  return (
    <div className="panel-toolbar">
      <div className="panel-toolbar-meta">
        {title && <span className="panel-toolbar-title">{title}</span>}
        {subtitle && <span className="hint panel-toolbar-subtitle">{subtitle}</span>}
      </div>
      <div className="panel-toolbar-actions">
        {extra}
        {onDownload && (
          <button type="button" className="btn sm secondary" onClick={onDownload}>
            {downloadLabel}
          </button>
        )}
        {onToggleFullscreen && (
          <button type="button" className="btn sm secondary" onClick={onToggleFullscreen}>
            {fullscreen ? '缩小恢复' : '全屏展示'}
          </button>
        )}
      </div>
    </div>
  )
}
