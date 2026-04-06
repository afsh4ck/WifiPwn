import { clsx } from 'clsx'
import type { ReactNode } from 'react'

interface StatsCardProps {
  label: string
  value: number | string
  icon: ReactNode
  color?: 'accent' | 'success' | 'warning' | 'danger' | 'purple'
  sub?: string
}

const COLOR = {
  accent:  { border: 'border-accent/30',   text: 'text-accent',   bg: 'bg-accent/10'  },
  success: { border: 'border-success/30',  text: 'text-success',  bg: 'bg-success/10' },
  warning: { border: 'border-warning/30',  text: 'text-warning',  bg: 'bg-warning/10' },
  danger:  { border: 'border-danger/30',   text: 'text-danger',   bg: 'bg-danger/10'  },
  purple:  { border: 'border-purple/30',   text: 'text-purple',   bg: 'bg-purple/10'  },
}

export function StatsCard({ label, value, icon, color = 'accent', sub }: StatsCardProps) {
  const c = COLOR[color]
  return (
    <div className={clsx(
      'relative overflow-hidden rounded-xl border p-5 bg-card',
      c.border,
      'hover:shadow-lg transition-shadow duration-300'
    )}>
      {/* Background glow */}
      <div className={clsx('absolute -top-6 -right-6 w-24 h-24 rounded-full blur-2xl opacity-20', c.bg)} />

      <div className="flex items-start justify-between relative z-10">
        <div>
          <p className="text-xs font-medium text-muted uppercase tracking-widest mb-1">{label}</p>
          <p className={clsx('text-3xl font-bold tabular-nums', c.text)}>{value}</p>
          {sub && <p className="text-xs text-muted mt-1">{sub}</p>}
        </div>
        <div className={clsx('p-2.5 rounded-lg', c.bg, c.text)}>{icon}</div>
      </div>
    </div>
  )
}
