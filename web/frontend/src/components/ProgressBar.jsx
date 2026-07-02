import { formatEta } from '../utils/pipeline'

export default function ProgressBar({ progress, running }) {
  if (!running || !progress) return null
  const pct = progress.percent ?? 0
  const eta = formatEta(progress.eta_seconds)
  const label = progress.current_label || '执行中'

  return (
    <div className="scan-progress">
      <div className="scan-progress-meta">
        <span className="scan-progress-pct">进度 {pct}%</span>
        <span className="scan-progress-sep">|</span>
        <span className="scan-progress-eta">预估剩余 {eta}</span>
        <span className="scan-progress-sep">|</span>
        <span className="scan-progress-step">正在执行：{label}</span>
        <span className="scan-progress-count">
          ({progress.completed}/{progress.total} 步)
        </span>
      </div>
      <div className="scan-progress-track">
        <div className="scan-progress-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}
