import { useEffect, useMemo, useState } from 'react'
import api, { downloadFile } from '../api'
import PanelToolbar from './PanelToolbar'
import { buildIssuesMarkdown, downloadTextFile } from '../utils/exportMarkdown'

const ISSUE_COLUMNS = [
  { key: 'id', label: 'BUG-ID', width: '90px' },
  { key: 'source', label: '来源模块', width: '110px' },
  { key: 'module_label', label: '错误功能', width: '140px' },
  { key: 'function_description', label: '功能描述', width: '180px' },
  { key: 'severity', label: '严重级别', width: '80px' },
  { key: 'file_path', label: '文件路径', width: '160px' },
  { key: 'line_number', label: '行号', width: '60px' },
  { key: 'message', label: '错误原因', width: '260px' },
  { key: 'code_snippet', label: '错误详情/代码', width: '240px' },
  { key: 'category', label: '分类', width: '100px' },
  { key: 'fix_suggestion', label: '修复建议', width: '220px' },
]

const ISSUES_PER_PAGE = 20

function severityBadge(severity) {
  const cls = ['high', 'critical'].includes(severity) ? 'fail' : severity === 'medium' ? 'pending' : 'neutral'
  return <span className={`badge sm ${cls}`}>{severity || '-'}</span>
}

function IssueCell({ issue, col }) {
  const val = issue[col.key]
  if (col.key === 'severity') return severityBadge(val)
  if (col.key === 'code_snippet' && val) {
    return <pre className="issue-code-inline" title={val}>{val}</pre>
  }
  if (col.key === 'message' && val) {
    return <span className="issue-message" title={val}>{val}</span>
  }
  if (col.key === 'file_path' && val) {
    return <code title={val}>{val}</code>
  }
  if (col.key === 'line_number' && val) {
    return val
  }
  const text = val || '-'
  return typeof text === 'string' ? <span title={text}>{text}</span> : text
}

export default function IssuesTablePanel({
  job,
  findings,
  running,
  issuePage,
  onIssuePageChange,
}) {
  const [fullscreen, setFullscreen] = useState(false)

  const issueTotal = findings?.issues?.length || 0
  const issueTotalPages = Math.max(1, Math.ceil(issueTotal / ISSUES_PER_PAGE))
  const paginatedIssues = useMemo(() => {
    const all = findings?.issues || []
    const start = (issuePage - 1) * ISSUES_PER_PAGE
    return all.slice(start, start + ISSUES_PER_PAGE)
  }, [findings?.issues, issuePage])

  useEffect(() => {
    if (!fullscreen) return undefined
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [fullscreen])

  const downloadMd = async () => {
    if (!job) return
    try {
      const { data: docs } = await api.get(`/audits/${job.id}/documents`)
      const hasBugsMd = Array.isArray(docs) && docs.some((d) => d.name === 'audit-bugs.md')
      if (hasBugsMd) {
        await downloadFile(job.id, 'audit-bugs.md', 'md')
        return
      }
    } catch {
      /* fallback to generated md */
    }
    const md = buildIssuesMarkdown(job, findings, ISSUE_COLUMNS)
    downloadTextFile(`issues-${job.id}.md`, md)
  }

  return (
    <div className={`card table-card issues-table-panel ${fullscreen ? 'panel-fullscreen' : ''}`}>
      <PanelToolbar
        title="问题列表"
        subtitle={issueTotal ? `共 ${issueTotal} 条` : undefined}
        fullscreen={fullscreen}
        onToggleFullscreen={() => setFullscreen((v) => !v)}
        onDownload={downloadMd}
        downloadLabel="下载 MD"
      />
      {job?.error_message && (
        <div className="issues-banner error">{job.error_message}</div>
      )}
      {findings?.module_stats?.length > 0 && (
        <div className="issues-module-stats">
          {findings.module_stats
            .filter((m) => m.findings > 0 || ['failure', 'error'].includes(m.status))
            .map((m) => (
              <span key={m.module} className="badge sm pending">
                {m.module}: {m.status} ({m.findings})
              </span>
            ))}
        </div>
      )}
      <div className="issues-table-scroll table-scroll-wrap table-scroll-wide">
        <table className="table table-fixed-head table-issues">
          <thead>
            <tr>
              {ISSUE_COLUMNS.map((col) => (
                <th key={col.key} style={{ minWidth: col.width }}>{col.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {!issueTotal ? (
              <tr>
                <td colSpan={ISSUE_COLUMNS.length} className="hint">
                  {running ? '审计进行中，问题将在扫描完成后展示…' : '暂无结构化问题记录'}
                </td>
              </tr>
            ) : paginatedIssues.map((issue, idx) => (
              <tr key={`${issue.id}-${idx}`}>
                {ISSUE_COLUMNS.map((col) => (
                  <td key={col.key} className="cell-wrap">
                    <IssueCell issue={issue} col={col} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="issues-table-footer">
        <span className="hint">
          共 {issueTotal} 条
          {issueTotalPages > 1 && ` · 第 ${issuePage} / ${issueTotalPages} 页（每页 ${ISSUES_PER_PAGE} 条）`}
        </span>
        {issueTotalPages > 1 && (
          <div className="pagination issues-pagination">
            <button type="button" className="btn sm secondary" disabled={issuePage <= 1} onClick={() => onIssuePageChange(1)}>首页</button>
            <button type="button" className="btn sm secondary" disabled={issuePage <= 1} onClick={() => onIssuePageChange(Math.max(1, issuePage - 1))}>上一页</button>
            <button type="button" className="btn sm secondary" disabled={issuePage >= issueTotalPages} onClick={() => onIssuePageChange(Math.min(issueTotalPages, issuePage + 1))}>下一页</button>
            <button type="button" className="btn sm secondary" disabled={issuePage >= issueTotalPages} onClick={() => onIssuePageChange(issueTotalPages)}>末页</button>
          </div>
        )}
      </div>
    </div>
  )
}

export { ISSUE_COLUMNS, ISSUES_PER_PAGE }
