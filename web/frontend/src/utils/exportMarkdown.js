export function downloadTextFile(filename, content, mime = 'text/markdown;charset=utf-8') {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function buildIssuesMarkdown(job, findings, columns) {
  const issues = findings?.issues || []
  const lines = [
    '# 审计问题列表',
    '',
    `- **任务 ID**: \`${job?.id || '-'}\``,
    `- **仓库**: ${job?.repo_full_name || '-'}`,
    `- **分支**: ${job?.branch || '-'}`,
    `- **状态**: ${job?.status || '-'}`,
    `- **问题数**: ${issues.length}`,
    `- **导出时间**: ${new Date().toISOString()}`,
    '',
  ]
  if (job?.error_message) {
    lines.push('## 任务错误', '', job.error_message, '')
  }
  issues.forEach((issue, index) => {
    lines.push(`## ${issue.id || `ISSUE-${index + 1}`}`)
    columns.forEach((col) => {
      const val = issue[col.key]
      if (val) {
        lines.push(`- **${col.label}**: ${String(val).replace(/\n/g, '\n  ')}`)
      }
    })
    lines.push('')
  })
  return lines.join('\n')
}
