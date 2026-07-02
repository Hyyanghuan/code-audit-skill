export const STEP_STATUS_LABEL = {
  pending: '等待',
  running: '执行中',
  success: '成功',
  failure: '发现问题',
  error: '错误',
  skipped: '已跳过',
}

export const STEP_STATUS_CLASS = {
  pending: 'neutral',
  running: 'pending',
  success: 'success',
  failure: 'fail',
  error: 'fail',
  skipped: 'neutral',
}

const DONE = new Set(['success', 'failure', 'error', 'skipped'])

/** 根据 pipeline 步骤计算进度与预估剩余时间（前端兜底） */
export function computePipelineProgress(steps = [], jobCreatedAt) {
  const total = steps.length
  if (!total) {
    return { percent: 0, etaSeconds: null, completed: 0, total: 0, currentLabel: '' }
  }

  let completed = 0
  let totalDurationMs = 0
  let durationCount = 0
  let runningStep = null
  const now = Date.now()

  steps.forEach((s) => {
    if (s.status === 'running') runningStep = s
    if (DONE.has(s.status)) {
      completed += 1
      if (s.started_at && s.finished_at) {
        const ms = new Date(s.finished_at) - new Date(s.started_at)
        if (ms > 0) {
          totalDurationMs += ms
          durationCount += 1
        }
      }
    }
  })

  let percent = Math.round((completed / total) * 100)
  if (runningStep) percent = Math.min(99, Math.round(((completed + 0.5) / total) * 100))
  if (completed >= total) percent = 100

  let etaSeconds = null
  const remaining = total - completed - (runningStep ? 1 : 0)
  if (durationCount > 0 && (remaining > 0 || runningStep)) {
    const avgMs = totalDurationMs / durationCount
    let etaMs = avgMs * Math.max(0, remaining)
    if (runningStep?.started_at) {
      const runningMs = now - new Date(runningStep.started_at).getTime()
      etaMs += Math.max(0, avgMs - runningMs)
    }
    etaSeconds = Math.max(0, Math.round(etaMs / 1000))
  } else if (jobCreatedAt && completed < total) {
    const elapsed = (now - new Date(jobCreatedAt).getTime()) / 1000
    const frac = Math.max(completed / total, 0.05)
    etaSeconds = Math.max(0, Math.round(elapsed / frac - elapsed))
  }

  const currentLabel = runningStep?.label
    || steps.find((s) => s.status === 'running')?.label
    || ''

  return { percent, etaSeconds, completed, total, currentLabel }
}

export function formatEta(seconds) {
  if (seconds == null || seconds < 0) return '计算中…'
  if (seconds < 60) return `约 ${seconds} 秒`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m < 60) return `约 ${m} 分 ${s} 秒`
  const h = Math.floor(m / 60)
  return `约 ${h} 时 ${m % 60} 分`
}

export function pipelineAsDocItems(steps = []) {
  return steps.map((step) => ({
    kind: 'step',
    id: step.id,
    name: step.label || step.id,
    status: step.status,
    findings: step.findings || 0,
    message: step.message || '',
    phase: step.phase || '',
    finished_at: step.finished_at,
  }))
}

export function mergeDocList(steps = [], files = []) {
  return [
    ...pipelineAsDocItems(steps),
    ...files.map((f) => ({ kind: 'file', ...f })),
  ]
}
