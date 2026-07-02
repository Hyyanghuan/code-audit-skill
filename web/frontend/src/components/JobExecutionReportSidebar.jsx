import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'
import ReportContentPanel, { REPORT_TABS, getReportContent } from './ReportContentPanel'
import { TabLabel } from './Icons'

const SIDEBAR_TABS = REPORT_TABS.slice(0, 4)

export default function JobExecutionReportSidebar({ jobId, repoName }) {
  const [tab, setTab] = useState('bugs')
  const [bundle, setBundle] = useState(null)
  const [loading, setLoading] = useState(true)
  const [fullscreen, setFullscreen] = useState(false)

  useEffect(() => {
    setLoading(true)
    api.get(`/audits/${jobId}/execution-report`)
      .catch(() => api.get(`/audits/${jobId}/bugs-bundle`))
      .then(({ data }) => setBundle(data))
      .catch(() => setBundle(null))
      .finally(() => setLoading(false))
  }, [jobId])

  const content = getReportContent(bundle, tab)

  if (fullscreen) {
    return (
      <ReportContentPanel
        jobId={jobId}
        bundle={bundle}
        tab={tab}
        onTabChange={setTab}
        title="审计执行报告"
        subtitle={repoName}
        fullscreen
        onToggleFullscreen={() => setFullscreen(false)}
        tabs={REPORT_TABS}
      />
    )
  }

  return (
    <div className="card job-bugs-sidebar">
      <div className="job-bugs-sidebar-header">
        <h4>执行报告</h4>
        <code className="job-id-tag" title={jobId}>{jobId}</code>
      </div>
      {repoName && <p className="hint job-bugs-repo">{repoName}</p>}
      <div className="view-tabs view-tabs-compact view-tabs-wrap">
        {SIDEBAR_TABS.map((t) => (
          <button key={t.id} type="button" className={tab === t.id ? 'tab active' : 'tab'} onClick={() => setTab(t.id)}>
            <TabLabel icon={t.icon}>{t.label}</TabLabel>
          </button>
        ))}
      </div>
      <div className="job-bugs-body">
        {loading ? (
          <p className="hint">加载中…</p>
        ) : content ? (
          <pre className="job-bugs-pre">{content}</pre>
        ) : (
          <p className="hint">暂无内容</p>
        )}
      </div>
      <div className="job-bugs-actions">
        <button type="button" className="btn sm secondary" onClick={() => setFullscreen(true)}>全屏</button>
        <Link to={`/reports?job=${jobId}`} className="hint job-bugs-link">完整报告 →</Link>
      </div>
    </div>
  )
}
