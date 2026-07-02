import { useEffect, useState } from 'react'
import api from '../api'
import SettingsField from '../components/SettingsField'

function SettingsSection({ group, values, onChange, pathSuggestions = {}, toolSuggestions = {}, reportFiles = [] }) {
  return (
    <div className="card settings-group">
      <h3>{group.label}</h3>
      {group.doc && <div className="group-doc markdown-body"><pre className="group-doc-pre">{group.doc}</pre></div>}
      {group.fields.map((field) => (
        <SettingsField
          key={field.key}
          field={field}
          value={values[field.key]}
          onChange={onChange}
          pathSuggestions={toolSuggestions[field.key] || pathSuggestions[field.key] || []}
          reportFiles={reportFiles}
        />
      ))}
    </div>
  )
}

export default function Settings() {
  const [tab, setTab] = useState('audit')
  const [catalog, setCatalog] = useState({
    audit_groups: [], telegram_groups: [], telegram_report_files: [], presets: [], tool_path_suggestions: {},
  })
  const [auditValues, setAuditValues] = useState({})
  const [tgValues, setTgValues] = useState({})
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [cat, audit, tg] = await Promise.all([
        api.get('/settings/catalog'),
        api.get('/settings/audit'),
        api.get('/settings/telegram'),
      ])
      setCatalog(cat.data)
      setAuditValues(audit.data.values)
      setTgValues(tg.data.values)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const onAuditChange = (key, val) => {
    setAuditValues((prev) => {
      const next = { ...prev, [key]: val }
      if (key.startsWith('enable_') || ['super_linter_languages', 'gitleaks_config', 'custom_rules_path', 'ignore_paths_file'].includes(key)) {
        next.audit_preset = 'custom'
      }
      return next
    })
  }

  const onTgChange = (key, val) => setTgValues((prev) => ({ ...prev, [key]: val }))

  const saveAudit = async () => {
    setSaving(true)
    setMsg('')
    try {
      const { data } = await api.put('/settings/audit', { values: auditValues })
      setAuditValues(data.values)
      setMsg('审计配置已保存')
    } catch (err) {
      setMsg(err.response?.data?.detail || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const saveTelegram = async () => {
    setSaving(true)
    setMsg('')
    try {
      const { data } = await api.put('/settings/telegram', { values: tgValues })
      setTgValues(data.values)
      setMsg('Telegram 配置已保存')
    } catch (err) {
      setMsg(err.response?.data?.detail || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const applyPreset = async (presetId) => {
    if (presetId === 'custom') {
      onAuditChange('audit_preset', 'custom')
      return
    }
    setSaving(true)
    setMsg('')
    try {
      const { data } = await api.post('/settings/audit/apply-preset', { preset: presetId })
      setAuditValues(data.values)
      setMsg(`已应用预设「${(catalog.presets || []).find((p) => p.id === presetId)?.label || presetId}」`)
    } catch (err) {
      setMsg(err.response?.data?.detail || '应用预设失败')
    } finally {
      setSaving(false)
    }
  }

  const preset = auditValues.audit_preset
  const presetHint = preset && !['full', 'custom', ''].includes(preset)
    ? `当前预设「${(catalog.presets || []).find((p) => p.id === preset)?.label || preset}」会在执行时覆盖部分模块开关。`
    : null

  if (loading) return <p>加载中…</p>

  return (
    <div>
      <h2>系统配置</h2>
      <p className="hint">所有开关与参数均可在此修改并保存；新建审计任务将使用此处配置。</p>
      <div className="tabs">
        <button type="button" className={tab === 'audit' ? 'tab active' : 'tab'} onClick={() => setTab('audit')}>审计配置</button>
        <button type="button" className={tab === 'telegram' ? 'tab active' : 'tab'} onClick={() => setTab('telegram')}>Telegram 配置</button>
      </div>
      {msg && <p className="hint save-msg">{msg}</p>}
      {tab === 'audit' && (
        <>
          {presetHint && <p className="hint">{presetHint}</p>}
          <div className="card">
            <h3>快速应用预设</h3>
            <div className="preset-grid">
              {(catalog.presets || []).map((p) => (
                <button key={p.id} type="button" className={`preset-btn ${auditValues.audit_preset === p.id ? 'active' : ''}`}
                  onClick={() => applyPreset(p.id)} disabled={saving}>
                  <strong>{p.label}</strong>
                  {p.description && <span>{p.description}</span>}
                </button>
              ))}
            </div>
          </div>
          {(catalog.audit_groups || []).map((group) => (
            <SettingsSection key={group.id} group={group} values={auditValues} onChange={onAuditChange}
              toolSuggestions={catalog.tool_path_suggestions || {}} />
          ))}
          <button className="btn" onClick={saveAudit} disabled={saving}>{saving ? '保存中…' : '保存审计配置'}</button>
        </>
      )}
      {tab === 'telegram' && (
        <>
          {(catalog.telegram_groups || []).map((group) => (
            <SettingsSection
              key={group.id}
              group={group}
              values={tgValues}
              onChange={onTgChange}
              toolSuggestions={{}}
              reportFiles={catalog.telegram_report_files || []}
            />
          ))}
          <button className="btn" onClick={saveTelegram} disabled={saving}>{saving ? '保存中…' : '保存 Telegram 配置'}</button>
        </>
      )}
    </div>
  )
}
