const STATUS_ICON = {
  pending: '○',
  running: '◉',
  success: '✓',
  failure: '✗',
  error: '!',
  skipped: '−',
}

const STATUS_CLASS = {
  pending: 'neutral',
  running: 'pending',
  success: 'success',
  failure: 'fail',
  error: 'fail',
  skipped: 'neutral',
}

export default function PipelineSidebar({ pipeline, selectedStep, onSelectStep }) {
  const currentLabel = pipeline?.current_step
    ? pipeline.steps?.find((s) => s.id === pipeline.current_step)?.label
    : null

  return (
    <div className="pipeline-sidebar card">
      <div className="pipeline-sidebar-header">
        <h3>审计流程</h3>
        {currentLabel && (
          <p className="hint pipeline-running">正在执行：{currentLabel}</p>
        )}
        {!pipeline?.steps?.length && (
          <p className="hint">等待流水线初始化…</p>
        )}
      </div>
      {pipeline?.steps?.length > 0 && (
        <div className="pipeline-sidebar-body">
          <ul className="pipeline-list">
            {(() => {
              let lastPhase = ''
              return pipeline.steps.map((step) => {
                const showPhase = step.phase && step.phase !== lastPhase
                if (showPhase) lastPhase = step.phase
                return (
                  <li key={step.id}>
                    {showPhase && <div className="pipeline-phase">{step.phase}</div>}
                    <button
                      type="button"
                      className={`pipeline-step ${selectedStep === step.id ? 'active' : ''}`}
                      onClick={() => onSelectStep(step.id)}
                    >
                      <span className={`pipeline-icon ${STATUS_CLASS[step.status] || 'neutral'}`}>
                        {STATUS_ICON[step.status] || '?'}
                      </span>
                      <span className="pipeline-label">{step.label}</span>
                      {step.findings > 0 && (
                        <span className="pipeline-findings">{step.findings}</span>
                      )}
                    </button>
                  </li>
                )
              })
            })()}
          </ul>
        </div>
      )}
    </div>
  )
}
