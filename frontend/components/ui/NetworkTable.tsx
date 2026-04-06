'use client'

import { clsx } from 'clsx'
import { SecurityBadge } from './Badge'
import type { Network } from '@/types'

function SignalBar({ dbm }: { dbm: number }) {
  // Convert dBm (-100 to 0) to 1-5 bars
  const pct = Math.max(0, Math.min(100, (dbm + 100) * 1.5))
  const bars = pct > 80 ? 5 : pct > 60 ? 4 : pct > 40 ? 3 : pct > 20 ? 2 : 1
  const color = bars >= 4 ? 'bg-success' : bars === 3 ? 'bg-warning' : 'bg-danger'

  return (
    <span className="flex items-end gap-0.5 h-4">
      {[1, 2, 3, 4, 5].map(b => (
        <span
          key={b}
          className={clsx(
            'w-[3px] rounded-sm transition-all',
            b <= bars ? color : 'bg-muted/20',
          )}
          style={{ height: `${b * 20}%` }}
        />
      ))}
      <span className="ml-1 text-[10px] text-muted tabular-nums">{dbm}</span>
    </span>
  )
}

interface NetworkTableProps {
  networks: Network[]
  onSelect?: (network: Network) => void
  selectedBssid?: string
}

export function NetworkTable({ networks, onSelect, selectedBssid }: NetworkTableProps) {
  if (networks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted gap-3">
        <span className="text-4xl">📡</span>
        <p className="text-sm">No se han detectado redes. Inicia el escaneo.</p>
      </div>
    )
  }

  return (
    <div className="overflow-auto rounded-xl border border-border/60">
      <table className="w-full text-sm font-mono">
        <thead>
          <tr className="border-b border-border/60 bg-card/50 text-muted text-xs uppercase tracking-wider">
            <th className="text-left px-4 py-3">BSSID</th>
            <th className="text-left px-4 py-3">ESSID</th>
            <th className="text-center px-3 py-3">CH</th>
            <th className="text-center px-3 py-3">Seguridad</th>
            <th className="text-left px-4 py-3">Señal</th>
            {onSelect && <th className="px-4 py-3" />}
          </tr>
        </thead>
        <tbody>
          {networks.map((net) => {
            const selected = net.bssid === selectedBssid
            return (
              <tr
                key={net.bssid}
                className={clsx(
                  'border-b border-border/30 transition-colors',
                  selected ? 'bg-accent/10 border-accent/30' : 'hover:bg-surface/50',
                  onSelect && 'cursor-pointer'
                )}
                onClick={() => onSelect?.(net)}
              >
                <td className="px-4 py-3 text-accent tracking-wider">{net.bssid}</td>
                <td className="px-4 py-3 text-text max-w-[180px] truncate">
                  {net.essid || <span className="text-muted italic">hidden</span>}
                </td>
                <td className="px-3 py-3 text-center text-warning">{net.channel}</td>
                <td className="px-3 py-3 text-center">
                  <SecurityBadge value={net.security} />
                </td>
                <td className="px-4 py-3">
                  <SignalBar dbm={net.power} />
                </td>
                {onSelect && (
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={(e) => { e.stopPropagation(); onSelect(net) }}
                      className={clsx(
                        'text-xs px-2 py-1 rounded border transition-colors',
                        selected
                          ? 'border-accent text-accent bg-accent/10'
                          : 'border-border text-muted hover:border-accent hover:text-accent'
                      )}
                    >
                      {selected ? 'Seleccionado' : 'Seleccionar'}
                    </button>
                  </td>
                )}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
