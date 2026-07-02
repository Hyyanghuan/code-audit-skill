import { useEffect, useMemo, useState } from 'react'
import api from '../api'

export default function TelegramSendPanel({ jobId, completed, onMessage }) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [sendSummary, setSendSummary] = useState(true)
  const [files, setFiles] = useState([])

  useEffect(() => {
    if (!open || !jobId || !completed) return
    setLoading(true)
    api.get(`/audits/${jobId}/telegram/send-options`)
      .then(({ data }) => {
        setSendSummary(!!data.send_summary_default)
        setFiles(data.files || [])
      })
      .catch((err) => onMessage?.(err.response?.data?.detail || '加载发送选项失败'))
      .finally(() => setLoading(false))
  }, [open, jobId, completed, onMessage])

  const selectedNames = useMemo(
    () => files.filter((f) => f.selected && f.available).map((f) => f.filename),
    [files],
  )

  const toggleFile = (filename) => {
    setFiles((prev) => prev.map((f) => (
      f.filename === filename ? { ...f, selected: !f.selected } : f
    )))
  }

  const selectAllAvailable = (checked) => {
    setFiles((prev) => prev.map((f) => (
      f.available ? { ...f, selected: checked } : f
    )))
  }

  const send = async () => {
    if (!selectedNames.length && !sendSummary) {
      onMessage?.('请至少选择摘要或一个文件')
      return
    }
    setSending(true)
    try {
      const { data } = await api.post(`/audits/${jobId}/telegram/send`, {
        send_summary: sendSummary,
        filenames: selectedNames,
      })
      onMessage?.(`发送成功 ${data.sent}/${data.total}`)
      setOpen(false)
    } catch (err) {
      onMessage?.(err.response?.data?.detail || '发送失败')
    } finally {
      setSending(false)
    }
  }

  if (!completed) return null

  return (
    <div className="tg-send-wrap">
      <button type="button" className="btn sm" onClick={() => setOpen((v) => !v)} disabled={sending}>
        {open ? '收起 TG 发送' : '发送 TG 报告'}
      </button>
      {open && (
        <div className="card tg-send-panel">
          <h4>选择发送到 Telegram 群的内容</h4>
          <p className="hint">默认勾选来自「系统配置 → Telegram → 一键发送报告文件」；可在此任务中临时调整。</p>
          {loading ? (
            <p className="hint">加载中…</p>
          ) : (
            <>
              <label className="tg-send-summary">
                <input
                  type="checkbox"
                  checked={sendSummary}
                  onChange={(e) => setSendSummary(e.target.checked)}
                />
                发送文字摘要
              </label>
              <div className="tg-send-actions">
                <button type="button" className="btn xs secondary" onClick={() => selectAllAvailable(true)}>全选可用</button>
                <button type="button" className="btn xs secondary" onClick={() => selectAllAvailable(false)}>全不选</button>
              </div>
              <ul className="tg-send-file-list">
                {files.map((f) => (
                  <li key={f.filename} className={!f.available ? 'unavailable' : ''}>
                    <label>
                      <input
                        type="checkbox"
                        checked={!!f.selected}
                        disabled={!f.available}
                        onChange={() => toggleFile(f.filename)}
                      />
                      <span>{f.label}</span>
                      <code>{f.filename}</code>
                      {!f.available && <span className="hint">（本任务无此文件）</span>}
                    </label>
                  </li>
                ))}
              </ul>
              <button type="button" className="btn sm" onClick={send} disabled={sending}>
                {sending ? '发送中…' : `发送到 TG（${selectedNames.length} 个文件）`}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}
