'use client'

import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import { ChevronUp, ChevronDown, ChevronsUpDown, Wifi } from 'lucide-react'
import type { Network } from '@/types'

// ─── Sub-components ──────────────────────────────────────────────────

function Signal({ dbm }: { dbm: number }) {
  const pct   = Math.max(0, Math.min(100, (dbm + 100) * 1.5))
  const bars  = pct > 80 ? 5 : pct > 60 ? 4 : pct > 40 ? 3 : pct > 20 ? 2 : 1
  const color = bars >= 4 ? 'text-green-400' : bars >= 3 ? 'text-yellow-400' : bars >= 2 ? 'text-orange-400' : 'text-red-500'
  return (
    <span className={clsx('inline-flex items-center gap-1.5', color)}>
      <span className="inline-flex items-end gap-[2px] h-3.5">
        {[1, 2, 3, 4, 5].map(b => (
          <span key={b} className={clsx('w-[3px] rounded-sm', b <= bars ? 'bg-current' : 'bg-current opacity-15')}
            style={{ height: `${b * 19}%` }} />
        ))}
      </span>
      <span className="font-mono text-xs tabular-nums">{dbm}</span>
    </span>
  )
}

function EncBadge({ enc }: { enc: string }) {
  const e = (enc ?? '').toUpperCase()
  if (!e || e === 'OPN')       return <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-500/15 text-red-400 border border-red-500/25">OPN</span>
  if (e.includes('WPA3'))      return <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-cyan-500/15 text-cyan-400 border border-cyan-500/25">WPA3</span>
  if (e.includes('WPA2'))      return <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-green-500/15 text-green-400 border border-green-500/25">WPA2</span>
  if (e.includes('WPA'))       return <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-yellow-500/15 text-yellow-400 border border-yellow-500/25">WPA</span>
  if (e.includes('WEP'))       return <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-bold bg-orange-500/15 text-orange-400 border border-orange-500/25">WEP</span>
  return <span className="inline-block px-1.5 py-0.5 rounded text-[10px] font-mono border border-border/40 text-muted">{enc || '—'}</span>
}

// ─── Sort helpers ─────────────────────────────────────────────────────

type SortKey = 'bssid' | 'essid' | 'power' | 'channel' | 'speed' | 'security' | 'beacons' | 'ivs'
type SortDir = 'asc' | 'desc'

interface ColDef {
  key?: SortKey
  label: string
  align: 'left' | 'right' | 'center'
}

const COLUMNS: ColDef[] = [
  { key: 'bssid',    label: 'BSSID',    align: 'left'   },
  { key: 'essid',    label: 'ESSID',    align: 'left'   },
  { key: 'power',    label: 'Signal',   align: 'right'  },
  { key: 'channel',  label: 'CH',       align: 'right'  },
  { key: 'speed',    label: 'MB',       align: 'right'  },
  { key: 'security', label: 'ENC',      align: 'center' },
  {                  label: 'CIPHER',   align: 'center' },
  {                  label: 'AUTH',     align: 'center' },
  { key: 'beacons',  label: 'Beacons',  align: 'right'  },
  { key: 'ivs',      label: '#Data',    align: 'right'  },
]

// ─── Main component ───────────────────────────────────────────────────

interface NetworkTableProps {
  networks: Network[]
  onSelect?: (network: Network) => void
  selectedBssid?: string
}

export function NetworkTable({ networks, onSelect, selectedBssid }: NetworkTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('power')
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  const handleSort = (key?: SortKey) => {
    if (!key) return
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sorted = useMemo(() => {
    return [...networks].sort((a, b) => {
      const va = (a[sortKey as keyof Network] ?? '') as string | number
      const vb = (b[sortKey as keyof Network] ?? '') as string | number
      const cmp = typeof va === 'number' && typeof vb === 'number'
        ? va - vb
        : String(va).toLowerCase().localeCompare(String(vb).toLowerCase())
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [networks, sortKey, sortDir])

  const SortIcon = ({ col }: { col: ColDef }) => {
    if (!col.key) return null
    if (sortKey !== col.key) return <ChevronsUpDown className="w-3 h-3 opacity-25" />
    return sortDir === 'asc'
      ? <ChevronUp   className="w-3 h-3 text-accent" />
      : <ChevronDown className="w-3 h-3 text-accent" />
  }

  if (networks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-muted gap-3">
        <Wifi className="w-10 h-10 opacity-20" />
        <p className="text-sm">Sin redes detectadas — inicia el escaneo</p>
      </div>
    )
  }

  return (
    <div className="overflow-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-card/60 text-muted text-xs uppercase tracking-wider">
            {COLUMNS.map(col => (
              <th
                key={col.label}
                className={clsx(
                  'px-4 py-3 font-semibold select-none whitespace-nowrap',
                  col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left',
                  col.key ? 'cursor-pointer hover:text-text transition-colors' : ''
                )}
                onClick={() => handleSort(col.key)}
              >
                <span className="inline-flex items-center gap-1">
                  {col.label}
                  <SortIcon col={col} />
                </span>
              </th>
            ))}
            <th className="px-4 py-3" />
          </tr>
        </thead>
        <tbody>
          {sorted.map(net => {
            const sel = net.bssid === selectedBssid
            return (
              <tr
                key={net.bssid}
                onClick={() => onSelect?.(net)}
                className={clsx(
                  'border-b border-border/30 transition-colors',
                  sel ? 'bg-accent/8 border-accent/20' : 'hover:bg-surface/60',
                  onSelect && 'cursor-pointer'
                )}
              >
                {/* BSSID */}
                <td className="px-4 py-2.5 font-mono text-xs text-text/60 tracking-wider whitespace-nowrap">
                  {net.bssid}
                </td>
                {/* ESSID */}
                <td className="px-4 py-2.5 font-medium max-w-[200px] truncate">
                  {net.essid || <span className="text-muted italic text-xs">hidden</span>}
                </td>
                {/* Signal */}
                <td className="px-4 py-2.5 text-right"><Signal dbm={Number(net.power) || 0} /></td>
                {/* CH */}
                <td className="px-4 py-2.5 text-right font-mono text-xs text-yellow-400">{net.channel}</td>
                {/* MB */}
                <td className="px-4 py-2.5 text-right font-mono text-xs text-muted">{net.speed ?? '—'}</td>
                {/* ENC */}
                <td className="px-4 py-2.5 text-center"><EncBadge enc={net.security} /></td>
                {/* CIPHER */}
                <td className="px-4 py-2.5 text-center font-mono text-xs text-muted">{net.cipher || '—'}</td>
                {/* AUTH */}
                <td className="px-4 py-2.5 text-center font-mono text-xs text-muted">{net.authentication || '—'}</td>
                {/* Beacons */}
                <td className="px-4 py-2.5 text-right font-mono text-xs text-muted">{net.beacons ?? 0}</td>
                {/* #Data */}
                <td className="px-4 py-2.5 text-right font-mono text-xs text-muted">{net.ivs ?? 0}</td>
                {/* Select */}
                <td className="px-4 py-2.5 text-right">
                  <button
                    onClick={e => { e.stopPropagation(); onSelect?.(net) }}
                    className={clsx(
                      'text-xs px-2 py-1 rounded border transition-colors whitespace-nowrap',
                      sel
                        ? 'border-accent text-accent bg-accent/10'
                        : 'border-border text-muted hover:border-accent hover:text-accent'
                    )}
                  >
                    {sel ? '✓ Target' : 'Seleccionar'}
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

