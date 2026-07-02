import { useEffect } from 'react'
import api, { downloadFile } from '../api'
import PanelToolbar from './PanelToolbar'
import { downloadTextFile } from '../utils/exportMarkdown'

export const REPORT_TABS = [
  {
    id: 'bugs',
    label: 'Bug 报告',
    field: 'audit_bugs_md',
    fallbackJson: 'audit_bugs_json',
    downloadName: 'audit-bugs-{jobId}.md',
    artifact: 'audit-bugs.md',
  },
  {
    id: 'bug_log',
    label: 'Bug 生成日志',
    field: 'generate_bug_report_log',
    downloadName: 'generate-bug-report-{jobId}.log',
    mime: 'text/plain;charset=utf-8',
  },
  {
    id: 'test_cases',
    label: '验收测试用例',
    field: 'test_cases_md',
    fallbackJson: 'test_cases_json',
    downloadName: 'test-cases-{jobId}.md',
    artifact: 'test-cases.md',
  },
  {
    id: 'functional_cases',
    label: '功能测试用例',
    field: 'functional_test_cases_md',
    fallbackJson: 'functional_test_cases_json',
    downloadName: 'test-cases-functional-{jobId}.md',
    artifact: 'test-cases-functional.md',
  },
  {
    id: 'api_cases',
    label: '接口测试用例',
    field: 'api_test_cases_md',
    fallbackJson: 'api_test_cases_json',
    downloadName: 'test-cases-api-{jobId}.md',
    artifact: 'test-cases-api.md',
  },
  {
    id: 'test_results',
    label: '验收执行结果',
    field: 'test_results_md',
    altField: 'test_cases_execution_log',
    downloadName: 'test-results-{jobId}.md',
    artifact: 'test-cases-execution.log',
    artifactMime: 'text/plain;charset=utf-8',
  },
  {
    id: 'functional_results',
    label: '功能执行结果',
    field: 'functional_test_results_md',
    downloadName: 'functional-results-{jobId}.md',
    artifact: 'test-cases-functional-report.json',
  },
  {
    id: 'api_results',
    label: '接口执行结果',
    field: 'api_test_results_md',
    downloadName: 'api-results-{jobId}.md',
    artifact: 'test-cases-api-report.json',
  },
  {
    id: 'features',
    label: '功能清单',
    field: 'features_md',
    downloadName: 'features-checklist-{jobId}.md',
    artifact: 'manual-audit-checklist.md',
  },
  {
    id: 'modules',
    label: '模块实现结果',
    field: 'modules_result_md',
    downloadName: 'module-results-{jobId}.md',
  },
]

export function getReportContent(bundle, tabId) {
  const tab = REPORT_TABS.find((t) => t.id === tabId)
  if (!tab || !bundle) return ''
  let content = bundle[tab.field]?.trim() || ''
  if (!content && tab.altField) {
    content = bundle[tab.altField]?.trim() || ''
  }
  if (!content && tab.fallbackJson && bundle[tab.fallbackJson]) {
    content = JSON.stringify(bundle[tab.fallbackJson], null, 2)
  }
  return content
}

export default function ReportContentPanel({
  jobId,
  bundle,
  tab,
  onTabChange,
  title,
  subtitle,
  fullscreen,
  onToggleFullscreen,
  tabs = REPORT_TABS,
}) {
  useEffect(() => {
    if (!fullscreen) return undefined
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [fullscreen])

  const tabDef = tabs.find((t) => t.id === tab)
  const content = getReportContent(bundle, tab)

  const downloadCurrent = async () => {
    if (!jobId || !tabDef) return
    if (tabDef.artifact) {
      try {
        const { data: docs } = await api.get(`/audits/${jobId}/documents`)
        if (Array.isArray(docs) && docs.some((d) => d.name === tabDef.artifact)) {
          const fmt = tabDef.artifactMime ? 'md' : 'md'
          await downloadFile(jobId, tabDef.artifact, fmt)
          return
        }
      } catch {
        /* fallback to generated content */
      }
    }
    const name = tabDef.downloadName.replace('{jobId}', jobId)
    downloadTextFile(name, content || '(空)', tabDef.mime || 'text/markdown;charset=utf-8')
  }

  return (
    <div className={`card bugs-content-panel ${fullscreen ? 'panel-fullscreen' : ''}`}>
      <PanelToolbar
        title={title}
        subtitle={subtitle}
        fullscreen={fullscreen}
        onToggleFullscreen={onToggleFullscreen}
        onDownload={jobId && content ? downloadCurrent : undefined}
        downloadLabel="下载 MD"
      />
      <div className="view-tabs view-tabs-wrap">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            className={tab === t.id ? 'tab active' : 'tab'}
            onClick={() => onTabChange(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="bugs-content-body">
        {!jobId ? (
          <p className="hint">请从左侧选择任务</p>
        ) : !content ? (
          <p className="hint">暂无该部分内容（可能未启用对应模块或审计未完成）</p>
        ) : (
          <pre className="doc-preview-pre bugs-preview-pre">{content}</pre>
        )}
      </div>
    </div>
  )
}
