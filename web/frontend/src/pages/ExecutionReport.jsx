import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../api'
import ReportContentPanel, { REPORT_TABS } from '../components/ReportContentPanel'

const PER_PAGE = 30

export default function ExecutionReport() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState(searchParams.get('job') || '')
  const [bundle, setBundle] = useState(null)
  const [tab, setTab] = useState('bugs')
  const [fullscreen, setFullscreen] = useState(false)
  const [loading, setLoading] = useState(true)

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE))

  useEffect(() => {
    setLoading(true)
    api.get('/audits/execution-reports', { params: { page, per_page: PER_PAGE } })
      .then(({ data }) => {
        setItems(data.items || [])
        setTotal(data.total || 0)
        const fromUrl = searchParams.get('job')
        if (fromUrl) setSelectedId(fromUrl)
        else if (!selectedId && data.items?.length) setSelectedId(data.items[0].job_id)
      })
      .catch(() => {
        return api.get('/audits/bugs-archive', { params: { page, per_page: PER_PAGE } })
          .then(({ data }) => {
            setItems(data.items || [])
            setTotal(data.total || 0)
          })
      })
      .finally(() => setLoading(false))
  }, [page])

  useEffect(() => {
    const fromUrl = searchParams.get('job')
    if (fromUrl) setSelectedId(fromUrl)
  }, [searchParams])

  useEffect(() => {
    if (!selectedId) {
      setBundle(null)
      return undefined
    }
    let mounted = true
    const load = () => api.get(`/audits/${selectedId}/execution-report`)
      .catch(() => api.get(`/audits/${selectedId}/bugs-bundle`))
    load().then(({ data }) => { if (mounted) setBundle(data) })
      .catch(() => { if (mounted) setBundle(null) })
    return () => { mounted = false }
  }, [selectedId])

  const selectJob = (jobId) => {
    setSelectedId(jobId)
    setSearchParams({ job: jobId })
  }

  return (
    <div className="bugs-archive-page">
      <h2>审计执行报告</h2>
      <p className="hint">查看 Bug 报告、验收/功能/接口测试用例及执行结果、功能清单与模块实现结果</p>

      <div className={`bugs-archive-layout ${fullscreen ? 'bugs-archive-layout-fs' : ''}`}>
        <div className="card bugs-job-list">
          <h4 className="section-title">任务列表</h4>
          {loading ? (
            <p className="hint">加载中…</p>
          ) : items.length === 0 ? (
            <p className="hint">暂无审计执行报告</p>
          ) : (
            <div className="bugs-job-scroll">
              {items.map((item) => (
                <button
                  key={item.job_id}
                  type="button"
                  className={selectedId === item.job_id ? 'bugs-job-item active' : 'bugs-job-item'}
                  onClick={() => selectJob(item.job_id)}
                >
                  <code className="bugs-job-id">{item.job_id}</code>
                  <span className="bugs-job-repo">{item.repo_full_name}</span>
                  <span className="hint bugs-job-meta">
                    {item.branch}
                    · {item.bug_count || item.total_findings || 0} 问题
                    {item.test_case_count ? ` · ${item.test_case_count} 用例` : ''}
                    {item.functional_case_count ? ` · 功能 ${item.functional_case_count}` : ''}
                    {item.api_case_count ? ` · 接口 ${item.api_case_count}` : ''}
                  </span>
                </button>
              ))}
            </div>
          )}
          {totalPages > 1 && (
            <div className="pagination bugs-list-pagination">
              <button type="button" className="btn sm secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>上一页</button>
              <span className="hint">{page}/{totalPages}</span>
              <button type="button" className="btn sm secondary" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>下一页</button>
            </div>
          )}
        </div>

        <ReportContentPanel
          jobId={selectedId}
          bundle={bundle}
          tab={tab}
          onTabChange={setTab}
          title={selectedId ? `任务 ${selectedId}` : '选择任务'}
          subtitle={bundle ? `${bundle.repo_full_name} @ ${bundle.branch}` : undefined}
          fullscreen={fullscreen}
          onToggleFullscreen={() => setFullscreen((v) => !v)}
          tabs={REPORT_TABS}
        />
      </div>
      {selectedId && (
        <p className="hint" style={{ marginTop: '0.75rem' }}>
          <Link to={`/jobs/${selectedId}`}>打开任务详情 →</Link>
        </p>
      )}
    </div>
  )
}
