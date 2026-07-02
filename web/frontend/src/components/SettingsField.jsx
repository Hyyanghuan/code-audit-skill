export default function SettingsField({ field, value, onChange, disabled, pathSuggestions = [] }) {
  const id = `field-${field.key}`

  if (field.type === 'boolean') {
    return (
      <div className="field-row">
        <label htmlFor={id} className="field-label">{field.label}</label>
        {field.description && <p className="field-desc">{field.description}</p>}
        <label className="switch">
          <input
            id={id}
            type="checkbox"
            checked={!!value}
            disabled={disabled}
            onChange={(e) => onChange(field.key, e.target.checked)}
          />
          <span className="switch-ui" />
          <span className="switch-text">{value ? '开启' : '关闭'}</span>
        </label>
        {field.hint && <p className="hint field-hint">{field.hint}</p>}
      </div>
    )
  }

  if (field.type === 'select') {
    const opts = field.options || []
    return (
      <div className="field-row">
        <label htmlFor={id}>{field.label}</label>
        {field.description && <p className="field-desc">{field.description}</p>}
        <select
          id={id}
          value={opts.some((o) => o.value === value) ? value : (field.allow_custom ? '__custom__' : value ?? '')}
          disabled={disabled}
          onChange={(e) => {
            const v = e.target.value
            onChange(field.key, v === '__custom__' ? '' : v)
          }}
        >
          {opts.map((opt) => (
            <option key={opt.value || 'empty'} value={opt.value}>{opt.label}</option>
          ))}
          {field.allow_custom && <option value="__custom__">自定义输入…</option>}
        </select>
        {(field.allow_custom && (!opts.some((o) => o.value === value) || value === '' || value === '__custom__')) && (
          <input
            type="text"
            value={value ?? ''}
            placeholder={field.placeholder || ''}
            disabled={disabled}
            onChange={(e) => onChange(field.key, e.target.value)}
          />
        )}
        {field.hint && <p className="hint field-hint">{field.hint}</p>}
      </div>
    )
  }

  if (field.type === 'path') {
    return (
      <div className="field-row">
        <label htmlFor={id}>{field.label}</label>
        {field.description && <p className="field-desc">{field.description}</p>}
        {pathSuggestions.length > 0 && (
          <select
            value=""
            disabled={disabled}
            onChange={(e) => e.target.value && onChange(field.key, e.target.value)}
            className="path-quick-select"
          >
            <option value="">快速选择内置路径…</option>
            {pathSuggestions.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        )}
        <input
          id={id}
          type="text"
          value={value ?? ''}
          placeholder={field.placeholder || ''}
          disabled={disabled}
          onChange={(e) => onChange(field.key, e.target.value)}
        />
        {field.hint && <p className="hint field-hint">{field.hint}</p>}
      </div>
    )
  }

  if (field.type === 'number') {
    return (
      <div className="field-row">
        <label htmlFor={id}>{field.label}</label>
        {field.description && <p className="field-desc">{field.description}</p>}
        <input
          id={id}
          type="number"
          min={field.min}
          max={field.max}
          value={value ?? field.default ?? ''}
          disabled={disabled}
          onChange={(e) => onChange(field.key, Number(e.target.value))}
        />
        {field.hint && <p className="hint field-hint">{field.hint}</p>}
      </div>
    )
  }

  return (
    <div className="field-row">
      <label htmlFor={id}>{field.label}</label>
      {field.description && <p className="field-desc">{field.description}</p>}
      <input
        id={id}
        type={field.type === 'password' ? 'password' : 'text'}
        value={value ?? ''}
        placeholder={field.placeholder || ''}
        disabled={disabled}
        onChange={(e) => onChange(field.key, e.target.value)}
      />
      {field.hint && <p className="hint field-hint">{field.hint}</p>}
    </div>
  )
}
