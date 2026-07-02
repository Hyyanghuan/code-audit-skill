import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api'

function statusBadge(status) {
  if (status === 'completed') return <span className="badge success">已完成</span>
  if (status === 'failed') return <span className="badge fail">失败</span>
  if (status === 'cancelled') return <span className="badge neutral">已取消</span>
  if (status === 'running') return <span className="badge pending">运行中</span>
  if (status === 'queued') return <span className="badge pending">排队中</span>
  return <span className="badge neutral">{status}</span>
}

const PRESET_LABELS = {
  full: '全部模块', minimal: '最小门禁', security: '安全专项',
  python: 'Python 聚焦', 'ci-fast': 'CI 快速', custom: '自定义',
}

function formatDuration(job) {
  const start = new Date(job.created_at)
  const end = job.finished_at
    ? new Date(job.finished_at)
    : (job.status === 'running' || job.status === 'queued' ? new Date() : null)
  if (!end || Number.isNaN(start.getTime())) return '-'
  const sec = Math.max(0, Math.floor((end - start) / 1000))
  if (sec < 60) return `${sec} 秒`
  const m = Math.floor(sec / 60)
  const s = sec % 60
  if (m < 60) return `${m} 分 ${s} 秒`
  const h = Math.floor(m / 60)
  return `${h} 时 ${m % 60} 分`
}

const PER_PAGE = 20

export default function Dashboard() {
  const nav = useNavigate()
  const [jobs, setJobs] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [branches, setBranches] = useState([])
  const [branchFilter, setBranchFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [retentionHours, setRetentionHours] = useState(72)
  const [rerunning, setRerunning] = useState(null)
  const [deleting, setDeleting] = useState(null)
  const [cancelling, setCancelling] = useState(null)
  const [msg, setMsg] = useState('')

  const load = useCallback(() => {
    const params = { page, per_page: PER_PAGE }
    if (branchFilter) params.branch = branchFilter
    api.get('/audits', { params })
      .then(({ data }) => {
        setJobs(data.items || [])
        setTotal(data.total || 0)
        setBranches(data.branches || [])
      })
      .finally(() => setLoading(false))
  }, [page, branchFilter])

  useEffect(() => {
    setLoading(true)
    load()
  }, [load])

  useEffect(() => {
    api.get('/health').then(({ data }) => {
      if (data.retention_hours) setRetentionHours(data.retention_hours)
    }).catch(() => {})
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [load])

  const totalPages = Math.max(1, Math.ceil(total / PER_PAGE))

  const rerunJob = async (job) => {
    const token = localStorage.getItem('githubToken')?.trim()
    if (!token) {
      setMsg('请先在「新建审计」页填写 GitHub Token，或重新登录后填写')
      return
    }
    setRerunning(job.id)
    setMsg('')
    try {
      const { data } = await api.post(`/audits/${job.id}/rerun`, { token })
      nav(`/jobs/${data.id}`)
    } catch (err) {
      setMsg(err.response?.data?.detail || '重新审计失败')
    } finally {
      setRerunning(null)
    }
  }

  const cancelJob = async (job) => {
    if (job.status !== 'running' && job.status !== 'queued') return
    if (!window.confirm(`确定取消 ${job.repo_full_name} @ ${job.branch} 的审计？`)) return
    setCancelling(job.id)
    setMsg('')
    try {
      await api.post(`/audits/${job.id}/cancel`)
      load()
    } catch (err) {
      setMsg(err.response?.data?.detail || '取消失败')
    } finally {
      setCancelling(null)
    }
  }

  const deleteJob = async (job) => {
    if (job.status === 'running' || job.status === 'queued') {
      setMsg('运行中的任务请先取消，再删除')
      return
    }
    if (!window.confirm(`确定删除 ${job.repo_full_name} @ ${job.branch} 的审计记录？`)) return
    setDeleting(job.id)
    setMsg('')
    try {
      await api.delete(`/audits/${job.id}`)
      if (jobs.length === 1 && page > 1) setPage((p) => p - 1)
      else load()
    } catch (err) {
      setMsg(err.response?.data?.detail || '删除失败')
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="dashboard-page">
      <div className="dashboard-header">
        <h2>审计任务</h2>
        <Link to="/audit/new" className="btn">新建审计</Link>
      </div>
      <p className="hint">
        文档临时保存 {retentionHours} 小时。每页 {PER_PAGE} 条，按创建时间倒序。
      </p>
      {msg && <p className="error">{msg}</p>}

      <div className="card filters-bar">
        <label htmlFor="branch-filter">分支筛选</label>
        <select
          id="branch-filter"
          value={branchFilter}
          onChange={(e) => { setBranchFilter(e.target.value); setPage(1) }}
        >
          <option value="">全部分支</option>
          {branches.map((b) => (
            <option key={b} value={b}>{b}</option>
          ))}
        </select>
        <span className="hint">共 {total} 条记录</span>
      </div>

      <div className="card table-card dashboard-table-card">
        {loading ? (
          <p>加载中…</p>
        ) : jobs.length === 0 ? (
          <p>暂无任务，<Link to="/audit/new">创建第一个审计</Link></p>
        ) : (
          <div className="table-scroll-wrap dashboard-table-wrap">
            <table className="table table-fixed-head table-dashboard">
              <thead>
                <tr>
                  <th className="col-id">任务 ID</th>
                  <th className="col-repo">仓库</th>
                  <th className="col-branch">分支</th>
                  <th className="col-preset">预设</th>
                  <th className="col-status">状态</th>
                  <th className="col-num">问题数</th>
                  <th className="col-time">创建时间</th>
                  <th className="col-dur">执行时长</th>
                  <th className="col-actions">操作</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.id}>
                    <td className="cell-id"><code title={j.id}>{j.id}</code></td>
                    <td className="cell-repo">{j.repo_full_name}</td>
                    <td className="cell-branch">{j.branch}</td>
                    <td className="cell-preset">{PRESET_LABELS[j.preset] || j.preset}</td>
                    <td className="cell-status">{statusBadge(j.status)}</td>
                    <td className="cell-num">{j.total_findings ?? '-'}</td>
                    <td className="cell-time">{new Date(j.created_at).toLocaleString()}</td>
                    <td className="cell-dur">{formatDuration(j)}</td>
                    <td className="cell-actions">
                      <div className="actions actions-wrap">
                        <Link to={`/jobs/${j.id}`} className="btn sm secondary">查看</Link>
                        {(j.status === 'running' || j.status === 'queued') && (
                          <button
                            type="button"
                            className="btn sm danger"
                            disabled={cancelling === j.id}
                            onClick={() => cancelJob(j)}
                          >
                            {cancelling === j.id ? '取消中…' : '取消'}
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn sm"
                          disabled={rerunning === j.id || j.status === 'running' || j.status === 'queued'}
                          onClick={() => rerunJob(j)}
                        >
                          {rerunning === j.id ? '启动中…' : '重审'}
                        </button>
                        <button
                          type="button"
                          className="btn sm danger"
                          disabled={deleting === j.id || j.status === 'running' || j.status === 'queued'}
                          onClick={() => deleteJob(j)}
                        >
                          {deleting === j.id ? '删除中…' : '删除'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button type="button" className="btn sm secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>上一页</button>
          <span className="hint">第 {page} / {totalPages} 页</span>
          <button type="button" className="btn sm secondary" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>下一页</button>
        </div>
      )}
    </div>
  )
}
