import type { ReactNode } from 'react'

export type IconName = 'home' | 'pantry' | 'recipes' | 'cook' | 'shopping' | 'plus' | 'arrow' | 'clock' | 'people' | 'check' | 'warning' | 'menu' | 'leaf'
const paths: Record<IconName, string> = {
  home: 'm3 10 9-7 9 7 M5 9v12h5v-7h4v7h5V9',
  pantry: 'M5 4h14v17H5z M5 10h14 M9 7h2 M9 14h2 M9 18h2 M8 1v3 M16 1v3',
  recipes: 'M4 4h6a3 3 0 0 1 2 1 3 3 0 0 1 2-1h6v16h-6a3 3 0 0 0-2 1 3 3 0 0 0-2-1H4z M12 5v16 M7 8h2 M15 8h2',
  cook: 'M7 15a4 4 0 0 1-2-7 5 5 0 0 1 9-3 4 4 0 0 1 5 7l-2 3v5H7z M7 17h10 M10 12v2 M14 12v2',
  shopping: 'M3 3h2l3 12h10l3-9H6 M9 19h.01 M17 19h.01 M9 18a1 1 0 1 0 0 2 1 1 0 0 0 0-2 M17 18a1 1 0 1 0 0 2 1 1 0 0 0 0-2',
  plus: 'M12 5v14 M5 12h14',
  arrow: 'M5 12h14 M14 7l5 5-5 5',
  clock: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0 M12 7v5l3 2',
  people: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0 M17 4a4 4 0 0 1 0 8 M22 21v-2a4 4 0 0 0-3-4',
  check: 'm5 12 4 4L19 6',
  warning: 'm12 3 10 18H2z M12 9v5 M12 17v.01',
  menu: 'M4 6h16 M4 12h16 M4 18h16',
  leaf: 'M19 3C10 2 3 6 5 14c2 8 14 4 14-11 M5 20l10-11 M6 15h5',
}

export function Icon({ name, className = '' }: { name: IconName; className?: string }) {
  return <svg className={'icon ' + className} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d={paths[name]} />
  </svg>
}

export function PageHeader({ title, description, children }: {
  title: string; description: string; children?: ReactNode
}) {
  return <div className="heading page-heading">
    <div><h1>{title}</h1><p className="muted">{description}</p></div>
    {children && <div className="actions">{children}</div>}
  </div>
}

export function StatusBadge({ children, tone = 'neutral' }: {
  children: ReactNode; tone?: 'neutral' | 'success' | 'warning'
}) {
  return <span className={'badge ' + tone}>{tone === 'success' && <Icon name="check" />}{children}</span>
}

export function EmptyState({ title, children, action }: {
  title: string; children: ReactNode; action?: ReactNode
}) {
  return <div className="panel empty">
    <span className="empty-symbol"><Icon name="leaf" /></span>
    <h2>{title}</h2><p className="muted">{children}</p>{action}
  </div>
}

export function LoadingState({ text = 'Cargando…' }: { text?: string }) {
  return <p className="loading-state" role="status"><Icon name="clock" />{text}</p>
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="error" role="alert"><Icon name="warning" /><div><p>{message}</p>
    {onRetry && <button className="secondary" onClick={onRetry}>Reintentar</button>}
  </div></div>
}
