import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import api from '../api'
import DocumentPanel from '../components/DocumentPanel'
import IssuesTablePanel from '../components/IssuesTablePanel'
import PipelineSidebar from '../components/PipelineSidebar'
import StepLogTerminal from '../components/StepLogTerminal'
import TelegramSendPanel from '../components/TelegramSendPanel'
import { TabLabel } from '../components/Icons'
import TerminalStream from '../components/TerminalStream'

export default function JobDetail() {
  const { jobId } = useParams()
  const nav = useNavigate()
  const [job, setJob] = useState(null)
  const [pipeline, setPipeline] = useState(null)
  const [findings, setFindings] = useState(null)
  const [selectedStep, setSelectedStep] = useState(null)
  const [view, setView] = useState('step')
  const [tgMsg, setTgMsg] = useState('')
  const [sending, setSending] = useState(false)
  const [rerunning, setRerunning] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [issuePage, setIssuePage] = useState(1)

  const steps = pipeline?.steps || []
  const issueTotal = findings?.issues?.length || 0

  const loadAll = () => {
    api.get(`/audits/${jobId}`).then(({ data }) => setJob(data)).catch(() => {})
    api.get(`/audits/${jobId}/pipeline`).then(({ data }) => setPipeline(data)).catch(() => {})
    api.get(`/audits/${jobId}/findings`).then(({ data }) => setFindings(data)).catch(() => {})
  }

  useEffect(() => {
    loadAll()
    const t = setInterval(loadAll, 2000)
    return () => clearInterval(t)
  }, [jobId])

  useEffect(() => {
    setIssuePage(1)
  }, [jobId])

  useEffect(() => {
    const issueTotalPages = Math.max(1, Math.ceil(issueTotal / 20))
    if (issuePage > issueTotalPages) {
      setIssuePage(issueTotalPages)
    }
  }, [issuePage, issueTotal])

  useEffect(() => {
    if (steps.length && !selectedStep) {
      const running = steps.find((s) => s.status === 'running')
      const failed = steps.find((s) => ['failure', 'error'].includes(s.status))
      setSelectedStep(running?.id || failed?.id || steps[0].id)
    }
  }, [steps, selectedStep])

  const selectStep = (stepId) => {
    setSelectedStep(stepId)
    setView('step')
  }

  const sendAll = async () => {
    setSending(true)
    try {
      const { data: opts } = await api.get(`/audits/${jobId}/telegram/send-options`)
      const filenames = (opts.files || [])
        .filter((f) => f.selected && f.available)
        .map((f) => f.filename)
      const { data } = await api.post(`/audits/${jobId}/telegram/send`, {
        send_summary: opts.send_summary_default !== false,
        filenames,
      })
      setTgMsg(`发送成功 ${data.sent}/${data.total}`)
    } catch (err) {
      setTgMsg(err.response?.data?.detail || '发送失败')
    } finally {
      setSending(false)
    }
  }

  const cancelAudit = async () => {
    if (!window.confirm('确定取消当前审计任务？')) return
    setCancelling(true)
    setTgMsg('')
    try {
      await api.post(`/audits/${jobId}/cancel`)
      loadAll()
    } catch (err) {
      setTgMsg(err.response?.data?.detail || '取消失败')
    } finally {
      setCancelling(false)
    }
  }

  const rerun = async () => {
    const token = localStorage.getItem('githubToken')?.trim()
    if (!token) {
      setTgMsg('请先在「新建审计」页填写 GitHub Token')
      return
    }
    setRerunning(true)
    try {
      const { data } = await api.post(`/audits/${jobId}/rerun`, { token })
      nav(`/jobs/${data.id}`)
    } catch (err) {
      setTgMsg(err.response?.data?.detail || '重新审计失败')
    } finally {
      setRerunning(false)
    }
  }

  const selectedStepInfo = useMemo(
    () => steps.find((s) => s.id === selectedStep),
    [steps, selectedStep],
  )

  if (!job) return <p>加载中…</p>

  const running = job.status === 'running' || job.status === 'queued'
  const completed = job.status === 'completed'
  const displayIssueCount = issueTotal || findings?.total_findings || job.total_findings || 0

  return (
    <div className="job-detail-page">
      <Link to="/" className="hint">← 返回任务列表</Link>
      <h2>{job.repo_full_name}</h2>

      <div className="card job-header">
        <p>
          任务 ID <code className="job-id-inline">{job.id}</code>
          · 分支 <strong>{job.branch}</strong>
          · 状态 <strong>{job.status}</strong>
          {job.audit_status && <> · 审计 <strong>{job.audit_status}</strong></>}
          {displayIssueCount > 0 && <> · 问题 <strong>{displayIssueCount}</strong></>}
          {running && <span className="badge pending"> 实时刷新</span>}
        </p>
        {job.error_message && <div className="error">{job.error_message}</div>}
        <div className="actions">
          {running && (
            <button type="button" className="btn sm danger" disabled={cancelling} onClick={cancelAudit}>
              {cancelling ? '取消中…' : '取消审计'}
            </button>
          )}
          <button type="button" className="btn sm secondary" disabled={rerunning || running} onClick={rerun}>
            {rerunning ? '启动中…' : '重新审计'}
          </button>
          {completed && (
            <button type="button" className="btn sm" onClick={sendAll} disabled={sending}>一键发送 TG</button>
          )}
          <Link to={`/reports?job=${jobId}`} className="btn sm secondary">审计执行报告</Link>
        </div>
        {completed && (
          <TelegramSendPanel jobId={jobId} completed={completed} onMessage={setTgMsg} />
        )}
        {tgMsg && <span className="hint"> {tgMsg}</span>}
      </div>

      <div className="job-layout job-layout-sticky job-layout-terminal">
        <div className="job-sidebar-wrap">
          <PipelineSidebar
            pipeline={pipeline}
            selectedStep={selectedStep}
            onSelectStep={selectStep}
          />
        </div>

        <div className="job-main">
          <div className="job-main-sticky">
            <div className="view-tabs">
              <button type="button" className={view === 'step' ? 'tab active' : 'tab'} onClick={() => setView('step')}>
                <TabLabel icon="step">步骤详情</TabLabel>
              </button>
              <button type="button" className={view === 'issues' ? 'tab active' : 'tab'} onClick={() => setView('issues')}>
                <TabLabel icon="issues">问题列表 {displayIssueCount ? `(${displayIssueCount})` : ''}</TabLabel>
              </button>
              <button type="button" className={view === 'docs' ? 'tab active' : 'tab'} onClick={() => setView('docs')}>
                <TabLabel icon="docs">审计文档</TabLabel>
              </button>
            </div>
          </div>

          <div className="job-main-scroll">
            {view === 'step' && (
              <StepLogTerminal
                jobId={jobId}
                stepId={selectedStep}
                stepLabel={selectedStepInfo?.label}
                stepStatus={selectedStepInfo?.status}
                running={running}
              />
            )}
            {view === 'issues' && (
              <IssuesTablePanel
                job={job}
                findings={findings}
                running={running}
                issuePage={issuePage}
                onIssuePageChange={setIssuePage}
              />
            )}
            {view === 'docs' && (
              <DocumentPanel jobId={jobId} completed={completed || !!findings?.issues?.length} />
            )}
          </div>
        </div>

        <div className="job-terminal-wrap">
          <TerminalStream jobId={jobId} running={running} title="审计流程日志" />
        </div>
      </div>
    </div>
  )
}
