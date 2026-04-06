import { clsx } from 'clsx'

type SecurityType = 'WPA2' | 'WPA' | 'WEP' | 'OPN' | 'WPA3' | string

const SEC: Record<SecurityType, string> = {
  WPA2: 'bg-warning/10 text-warning border-warning/30',
  WPA3: 'bg-success/10 text-success border-success/30',
  WPA:  'bg-orange-400/10 text-orange-400 border-orange-400/30',
  WEP:  'bg-danger/10 text-danger border-danger/30',
  OPN:  'bg-red-500/20 text-red-400 border-red-500/30',
}

interface BadgeProps {
  value: string
  className?: string
}

export function SecurityBadge({ value, className }: BadgeProps) {
  const key = value?.toUpperCase() as SecurityType
  const style = SEC[key] ?? 'bg-muted/10 text-muted border-muted/20'
  return (
    <span className={clsx(
      'inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold border',
      style, className
    )}>
      {value || 'UNK'}
    </span>
  )
}

type StatusVariant = 'running' | 'idle' | 'success' | 'error' | 'warning'
const STATUS: Record<StatusVariant, string> = {
  running: 'bg-accent/10 text-accent border-accent/30',
  idle:    'bg-muted/10 text-muted border-muted/20',
  success: 'bg-success/10 text-success border-success/30',
  error:   'bg-danger/10 text-danger border-danger/30',
  warning: 'bg-warning/10 text-warning border-warning/30',
}

interface StatusBadgeProps {
  variant: StatusVariant
  label: string
  pulse?: boolean
  className?: string
}

export function StatusBadge({ variant, label, pulse, className }: StatusBadgeProps) {
  const style = STATUS[variant]
  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border',
      style, className
    )}>
      <span className={clsx(
        'w-1.5 h-1.5 rounded-full',
        variant === 'running' ? 'bg-accent' : variant === 'success' ? 'bg-success' : variant === 'error' ? 'bg-danger' : 'bg-muted',
        pulse && variant === 'running' && 'animate-ping'
      )} />
      {label}
    </span>
  )
}
