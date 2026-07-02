import { useEffect, useRef, useState } from 'react'
import api from '../api'
import { STEP_STATUS_LABEL } from '../utils/pipeline'

export default function StepLogTerminal({ jobId, stepId, stepLabel, stepStatus, running }) {
  const [content, setContent] = useState('')
  const bodyRef = useRef(null)

  useEffect(() => {
    setContent('')
  }, [jobId, stepId])

  useEffect(() => {
    if (!stepId) {
      setContent('请从左侧审计流程选择一个步骤')
      return undefined
    }

    let mounted = true
    const load = async () => {
      try {
        const { data } = await api.get(`/audits/${jobId}/pipeline/${stepId}`)
        if (!mounted) return
        setContent(data.log_content || data.message || '暂无该步骤日志')
      } catch {
        if (mounted) setContent('无法加载步骤日志')
      }
    }
    load()
    const ms = running && stepStatus === 'running' ? 1500 : 4000
    const t = setInterval(load, ms)
    return () => {
      mounted = false
      clearInterval(t)
    }
  }, [jobId, stepId, stepStatus, running])

  const title = stepLabel || '步骤详情'
  const statusHint = stepStatus ? STEP_STATUS_LABEL[stepStatus] || stepStatus : ''

  return (
    <div className="terminal-panel terminal-panel-main card">
      <div className="terminal-header">
        <span className="terminal-dots"><i /><i /><i /></span>
        <span className="terminal-title">{title}</span>
        {statusHint && <span className="terminal-status">{statusHint}</span>}
      </div>
      <pre ref={bodyRef} className="terminal-body">
        {content || (stepStatus === 'pending' ? '该步骤尚未开始…' : '加载中…')}
      </pre>
    </div>
  )
}
