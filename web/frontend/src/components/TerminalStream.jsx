import { useEffect, useRef, useState } from 'react'
import api from '../api'
import ProgressBar from './ProgressBar'

export default function TerminalStream({ jobId, running, title = '审计流程日志' }) {
  const [content, setContent] = useState('')
  const [progress, setProgress] = useState(null)
  const bodyRef = useRef(null)
  const stickRef = useRef(true)

  useEffect(() => {
    setContent('')
    setProgress(null)
  }, [jobId])

  useEffect(() => {
    let mounted = true
    const load = async () => {
      try {
        const { data } = await api.get(`/audits/${jobId}/logs/scan`)
        if (!mounted) return
        setContent(data.content || '')
        setProgress(data.progress || null)
      } catch {
        /* ignore */
      }
    }
    load()
    const ms = running ? 1500 : 4000
    const t = setInterval(load, ms)
    return () => {
      mounted = false
      clearInterval(t)
    }
  }, [jobId, running])

  useEffect(() => {
    const el = bodyRef.current
    if (!el || !stickRef.current) return
    el.scrollTop = el.scrollHeight
  }, [content])

  const onScroll = () => {
    const el = bodyRef.current
    if (!el) return
    stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 48
  }

  return (
    <div className="terminal-panel card">
      <div className="terminal-header">
        <span className="terminal-dots">
          <i /><i /><i />
        </span>
        <span className="terminal-title">{title}</span>
        {running && <span className="terminal-status">实时更新</span>}
      </div>
      <ProgressBar progress={progress} running={running} />
      <pre ref={bodyRef} className="terminal-body" onScroll={onScroll}>
        {content || (running ? '等待审计流程日志…' : '暂无审计流程日志')}
      </pre>
    </div>
  )
}
