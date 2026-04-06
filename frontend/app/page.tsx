'use client'

import { useEffect, useState } from 'react'
import { Wifi, Key, ShieldAlert, Users, Target, Zap } from 'lucide-react'
import { StatsCard } from '@/components/ui/StatsCard'
import { getStats, getLogs } from '@/lib/api'
import { useWebSocket } from '@/lib/websocket'
import type { Stats, LogEntry } from '@/types'
import { clsx } from 'clsx'

const LOG_COLORS: Record<string, string> = {
  error:   'text-danger',
  warning: 'text-warning',
  success: 'text-success',
  info:    'text-accent',
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats>({
    total_networks: 0,
    handshakes_captured: 0,
    passwords_cracked: 0,
    credentials_captured: 0,
    active_campaigns: 0,
    deauth_attacks: 0,
  })
  const { logs } = useWebSocket()
  const [histLogs, setHistLogs] = useState<LogEntry[]>([])

  useEffect(() => {
    getStats().then(setStats).catch(console.error)
    getLogs(50).then(setHistLogs).catch(console.error)
  }, [])

  // Refresh stats on log updates from WS
  useEffect(() => {
    if (logs.length > 0) {
      getStats().then(setStats).catch(console.error)
    }
  }, [logs.length])

  const allLogs = [...histLogs, ...logs].slice(-60).reverse()

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-2xl border border-accent/20 bg-surface p-6">
        <div className="absolute inset-0 bg-gradient-radial from-accent/5 to-transparent" />
        <div className="relative z-10">
          <div className="flex items-center gap-2 text-accent text-xs font-mono uppercase tracking-widest mb-2">
            <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
            Sistema operativo
          </div>
          <h2 className="text-2xl font-bold text-text mb-1">WifiPwn</h2>
          <p className="text-muted text-sm">Plataforma de auditoría WiFi avanzada · Solo para entornos autorizados</p>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatsCard label="Redes detectadas"    value={stats.total_networks}       icon={<Wifi className="w-5 h-5" />}        color="accent"   />
        <StatsCard label="Handshakes"          value={stats.handshakes_captured}  icon={<Zap className="w-5 h-5" />}         color="warning"  />
        <StatsCard label="Contraseñas craqueadas" value={stats.passwords_cracked} icon={<Key className="w-5 h-5" />}         color="success"  />
        <StatsCard label="Credenciales"        value={stats.credentials_captured} icon={<Users className="w-5 h-5" />}       color="purple"   />
        <StatsCard label="Campañas activas"    value={stats.active_campaigns}     icon={<Target className="w-5 h-5" />}      color="accent"   />
        <StatsCard label="Ataques deauth"      value={stats.deauth_attacks}       icon={<ShieldAlert className="w-5 h-5" />} color="danger"   />
      </div>

      {/* Activity log */}
      <div className="card">
        <p className="section-title">Actividad reciente</p>
        <div className="space-y-1 max-h-[400px] overflow-y-auto font-mono text-xs">
          {allLogs.length === 0 ? (
            <p className="text-muted italic py-6 text-center">Sin actividad registrada</p>
          ) : (
            allLogs.map((log, i) => (
              <div key={i} className="flex items-start gap-3 py-1 border-b border-border/20 last:border-0">
                <span className="text-muted/50 shrink-0 tabular-nums">
                  {new Date(log.timestamp).toLocaleTimeString('es', { hour12: false })}
                </span>
                <span className={clsx(
                  'shrink-0 w-14 text-center uppercase text-[10px] font-bold',
                  LOG_COLORS[log.level] ?? 'text-muted'
                )}>
                  {log.level}
                </span>
                <span className="text-text/80 break-all">{log.message}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
