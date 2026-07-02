const defaults = {
  size: 18,
  strokeWidth: 1.75,
  className: '',
}

function Svg({ children, size, strokeWidth, className }) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  )
}

export function NavIcon({ name, size = defaults.size, className = 'nav-icon' }) {
  const p = { size, strokeWidth: defaults.strokeWidth, className }

  switch (name) {
    case 'dashboard':
      return (
        <Svg {...p}>
          <rect x="3" y="3" width="7" height="7" rx="1.5" />
          <rect x="14" y="3" width="7" height="7" rx="1.5" />
          <rect x="3" y="14" width="7" height="7" rx="1.5" />
          <rect x="14" y="14" width="7" height="7" rx="1.5" />
        </Svg>
      )
    case 'report':
      return (
        <Svg {...p}>
          <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
          <rect x="9" y="3" width="6" height="4" rx="1" />
          <path d="M9 12h6M9 16h6" />
        </Svg>
      )
    case 'plus':
      return (
        <Svg {...p}>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 8v8M8 12h8" />
        </Svg>
      )
    case 'settings':
      return (
        <Svg {...p}>
          <circle cx="12" cy="12" r="3" />
          <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
        </Svg>
      )
    case 'user':
      return (
        <Svg {...p}>
          <circle cx="12" cy="8" r="4" />
          <path d="M4 20c1.5-4 6.5-4 8-4s6.5 0 8 4" />
        </Svg>
      )
    case 'logout':
      return (
        <Svg {...p}>
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          <path d="M16 17l5-5-5-5M21 12H9" />
        </Svg>
      )
    case 'step':
      return (
        <Svg {...p}>
          <polyline points="4 17 10 11 14 15 20 9" />
          <path d="M20 9h-4V5" />
        </Svg>
      )
    case 'issues':
      return (
        <Svg {...p}>
          <path d="M12 9v4M12 17h.01" />
          <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        </Svg>
      )
    case 'docs':
      return (
        <Svg {...p}>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <path d="M14 2v6h6M8 13h8M8 17h8" />
        </Svg>
      )
    case 'audit':
      return (
        <Svg {...p}>
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="M9 12l2 2 4-4" />
        </Svg>
      )
    case 'telegram':
      return (
        <Svg {...p}>
          <path d="m22 2-7 20-4-9-9-4z" />
          <path d="M22 2 11 13" />
        </Svg>
      )
    case 'bug':
      return (
        <Svg {...p}>
          <path d="M8 2v2M16 2v2M9 9h6M9 13h6" />
          <path d="M12 22c4 0 7-2 7-5H5c0 3 3 5 7 5z" />
          <path d="M5 11a7 7 0 0 1 14 0" />
        </Svg>
      )
    case 'log':
      return (
        <Svg {...p}>
          <path d="M4 6h16M4 12h10M4 18h14" />
        </Svg>
      )
    case 'test':
      return (
        <Svg {...p}>
          <path d="M9 11l3 3L22 4" />
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
        </Svg>
      )
    case 'function':
      return (
        <Svg {...p}>
          <path d="M4 7h6M4 12h10M4 17h8" />
          <circle cx="18" cy="7" r="2" />
          <circle cx="20" cy="17" r="2" />
        </Svg>
      )
    case 'api':
      return (
        <Svg {...p}>
          <path d="M8 9h8M8 15h5" />
          <rect x="3" y="4" width="18" height="16" rx="2" />
        </Svg>
      )
    case 'features':
      return (
        <Svg {...p}>
          <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
        </Svg>
      )
    case 'modules':
      return (
        <Svg {...p}>
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <path d="M14 17h7" />
        </Svg>
      )
    case 'result':
      return (
        <Svg {...p}>
          <circle cx="12" cy="12" r="9" />
          <path d="M8 12l3 3 5-6" />
        </Svg>
      )
    default:
      return null
  }
}

export function TabLabel({ icon, children }) {
  return (
    <span className="tab-label">
      {icon && <NavIcon name={icon} size={16} className="tab-icon" />}
      <span>{children}</span>
    </span>
  )
}
