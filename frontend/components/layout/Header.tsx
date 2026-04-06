'use client'

import { usePathname } from 'next/navigation'
import { clsx } from 'clsx'
import { Wifi, WifiOff, AlertTriangle, Target, X } from 'lucide-react'
import { useWebSocket } from '@/lib/websocket'
import { useWifi } from '@/lib/context'

const PAGE_LABELS: Record<string, string> = {
  '/':              'Dashboard',
  '/interfaces':   'Gestión de Interfaces',
  '/scanner':      'Escáner de Redes',
  '/handshake':    'Captura de Handshake',
  '/cracking':     'Cracking de Contraseñas',
  '/deauth':       'Ataque Deauthentication',
  '/evil-portal':  'Evil Portal / Rogue AP',
  '/campaigns':    'Gestión de Campañas',
}

export function Header() {
  const path = usePathname()
  const { connected } = useWebSocket()
  const { target, setTarget } = useWifi()
  const label = PAGE_LABELS[path] ?? 'WifiPwn'

  return (
    <header className="h-14 shrink-0 flex items-center gap-3 px-6 border-b border-border/60 bg-surface/80 backdrop-blur-sm">
      <h1 className="text-sm font-semibold text-text tracking-wide shrink-0">{label}</h1>

      {/* Active target pill */}
      {target && (
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-orange-500/30 bg-orange-500/10 text-orange-400 text-xs font-mono max-w-xs truncate">
          <Target className="w-3 h-3 shrink-0" />
          <span className="truncate font-bold">{target.essid || target.bssid}</span>
          <span className="text-orange-400/60 shrink-0">CH{target.channel}</span>
          <button
            onClick={() => setTarget(null)}
            className="ml-1 hover:text-orange-200 transition-colors shrink-0"
            title="Eliminar target"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      )}

      <div className="ml-auto flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs text-warning">
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>root</span>
        </div>
        <div
          className={clsx(
            'flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border',
            connected
              ? 'text-success border-success/30 bg-success/10'
              : 'text-danger border-danger/30 bg-danger/10'
          )}
        >
          {connected
            ? <><Wifi className="w-3.5 h-3.5" /><span>Live</span></>
            : <><WifiOff className="w-3.5 h-3.5" /><span>Offline</span></>
          }
        </div>
      </div>
    </header>
  )
}
