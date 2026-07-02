import { useEffect, useState, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api'

const PRESET_LABELS = {
  full: '全部模块', minimal: '最小门禁', security: '安全专项',
  python: 'Python 聚焦', 'ci-fast': 'CI 快速', custom: '自定义',
}

export default function AuditNew() {
  const nav = useNavigate()
  const [githubToken, setGithubToken] = useState(localStorage.getItem('githubToken') || '')
  const [repos, setRepos] = useState([])
  const [branches, setBranches] = useState([])
  const [loadingBranches, setLoadingBranches] = useState(false)
  const [selectedRepo, setSelectedRepo] = useState('')
  const [branch, setBranch] = useState('main')
  const [auditConfig, setAuditConfig] = useState(null)
  const [loadingRepos, setLoadingRepos] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/settings/audit').then(({ data }) => setAuditConfig(data.values))
  }, [])

  const fetchBranches = useCallback(async (repoFullName, token, defaultBranch = 'main') => {
    if (!repoFullName || !token?.trim()) return
    setLoadingBranches(true)
    setError('')
    try {
      const { data } = await api.post('/github/branches', {
        token: token.trim(),
        repo_full_name: repoFullName,
      })
      const list = data.branches || []
      setBranches(list)
      if (list.length > 0) {
        setBranch((prev) => {
          if (list.some((b) => b.name === prev)) return prev
          if (list.some((b) => b.name === defaultBranch)) return defaultBranch
          return list[0].name
        })
      } else {
        setBranch(defaultBranch || 'main')
      }
    } catch (err) {
      setBranches([])
      setBranch(defaultBranch || 'main')
      setError(err.response?.data?.detail || '获取分支失败，可手动输入分支名')
    } finally {
      setLoadingBranches(false)
    }
  }, [])

  const fetchRepos = async () => {
    if (!githubToken.trim()) {
      setError('请先填写 GitHub Personal Access Token')
      return
    }
    setError('')
    setLoadingRepos(true)
    localStorage.setItem('githubToken', githubToken.trim())
    try {
      const { data } = await api.post('/github/repos', { token: githubToken.trim(), per_page: 50 })
      setRepos(data.repos)
      if (data.repos.length) {
        const pick = selectedRepo && data.repos.some((r) => r.full_name === selectedRepo)
          ? selectedRepo
          : data.repos[0].full_name
        const repoObj = data.repos.find((r) => r.full_name === pick) || data.repos[0]
        setSelectedRepo(pick)
        await fetchBranches(pick, githubToken, repoObj.default_branch || 'main')
      }
    } catch (err) {
      setError(err.response?.data?.detail || '获取仓库失败')
    } finally {
      setLoadingRepos(false)
    }
  }

  // 切换仓库时自动拉取分支
  useEffect(() => {
    if (!selectedRepo || !githubToken.trim() || repos.length === 0) return
    const repoObj = repos.find((r) => r.full_name === selectedRepo)
    fetchBranches(selectedRepo, githubToken, repoObj?.default_branch || 'main')
  }, [selectedRepo, githubToken, repos, fetchBranches])

  const onRepoChange = (fullName) => {
    setSelectedRepo(fullName)
    setBranches([])
  }

  const startAudit = async () => {
    if (!selectedRepo) {
      setError('请选择仓库')
      return
    }
    if (!branch.trim()) {
      setError('请选择或填写分支')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      const { data } = await api.post('/audits', {
        token: githubToken.trim(),
        repo_full_name: selectedRepo,
        branch: branch.trim(),
      })
      nav(`/jobs/${data.id}`)
    } catch (err) {
      setError(err.response?.data?.detail || '启动审计失败')
    } finally {
      setSubmitting(false)
    }
  }

  const enabledModules = auditConfig
    ? Object.entries(auditConfig).filter(([k, v]) => k.startsWith('enable_') && v).length
    : null

  return (
    <div>
      <h2>新建代码审计</h2>
      <p className="hint">
        选择仓库后<strong>自动获取分支列表</strong>；启动后在详情页查看每一步执行结果。
        参数见 <Link to="/settings">系统配置</Link>。
      </p>

      {auditConfig && (
        <div className="card config-summary">
          <h3>当前配置摘要</h3>
          <ul className="summary-list">
            <li>预设：{PRESET_LABELS[auditConfig.audit_preset] || auditConfig.audit_preset}</li>
            <li>已启用模块：{enabledModules} 个</li>
          </ul>
        </div>
      )}

      <div className="card">
        <h3>GitHub 连接</h3>
        {error && <div className="error">{error}</div>}
        <label>GitHub Personal Access Token</label>
        <input
          type="password"
          value={githubToken}
          onChange={(e) => setGithubToken(e.target.value)}
          onBlur={() => {
            if (githubToken.trim()) localStorage.setItem('githubToken', githubToken.trim())
          }}
        />
        <button className="btn secondary" onClick={fetchRepos} disabled={loadingRepos}>
          {loadingRepos ? '加载中…' : '获取仓库列表'}
        </button>
      </div>

      {repos.length > 0 && (
        <div className="card">
          <h3>选择仓库与分支</h3>
          <div className="grid-2">
            <div>
              <label>仓库</label>
              <select value={selectedRepo} onChange={(e) => onRepoChange(e.target.value)}>
                {repos.map((r) => (
                  <option key={r.id} value={r.full_name}>
                    {r.full_name} {r.private ? '(私有)' : ''}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label>
                分支
                {loadingBranches && <span className="hint"> （自动加载中…）</span>}
                {!loadingBranches && branches.length > 0 && (
                  <span className="hint"> （共 {branches.length} 个，已自动获取）</span>
                )}
              </label>
              {branches.length > 0 ? (
                <select value={branch} onChange={(e) => setBranch(e.target.value)}>
                  {branches.map((b) => (
                    <option key={b.name} value={b.name}>
                      {b.name}{b.protected ? ' 🔒' : ''} · {b.sha}
                    </option>
                  ))}
                </select>
              ) : (
                <>
                  <input
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    placeholder="main"
                  />
                  <button
                    type="button"
                    className="btn sm secondary"
                    style={{ marginTop: '0.5rem' }}
                    onClick={() => {
                      const repoObj = repos.find((r) => r.full_name === selectedRepo)
                      fetchBranches(selectedRepo, githubToken, repoObj?.default_branch || 'main')
                    }}
                    disabled={loadingBranches}
                  >
                    重新获取分支
                  </button>
                </>
              )}
            </div>
          </div>
          <button className="btn" onClick={startAudit} disabled={submitting || loadingBranches}>
            {submitting ? '启动中…' : '开始审计'}
          </button>
        </div>
      )}
    </div>
  )
}
