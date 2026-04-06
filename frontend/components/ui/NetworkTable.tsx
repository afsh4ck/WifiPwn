'use client'

import { clsx } from 'clsx'
import type { Network } from '@/types'

function pwrColor(pwr: number): string {
  if (pwr >= -50) return 'text-green-400'
  if (pwr >= -65) return 'text-yellow-300'
  if (pwr >= -80) return 'text-orange-400'
  return 'text-red-500'
}

function encColor(enc: string): string {
  const e = (enc ?? '').toUpperCase()
  if (!e || e === 'OPN') return 'text-red-400'
  if (e.includes('WPA3'))  return 'text-cyan-400'
  if (e.includes('WPA2'))  return 'text-green-400'
  if (e.includes('WPA'))   return 'text-yellow-400'
  if (e.includes('WEP'))   return 'text-orange-400'
  return 'text-gray-400'
}

interface NetworkTableProps {
  networks: Network[]
  onSelect?: (network: Network) => void
  selectedBssid?: string
}

export function NetworkTable({ networks, onSelect, selectedBssid }: NetworkTableProps) {
  if (networks.length === 0) {
    return (
      <div className="font-mono text-xs bg-black/90 rounded-lg px-4 py-10 text-center">
        <div className="text-green-500/40 tracking-widest text-[11px] mb-3">
          BSSID&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
          PWR&nbsp;&nbsp;Beacons&nbsp;&nbsp;#Data&nbsp;&nbsp;CH&nbsp;&nbsp;MB&nbsp;&nbsp;ENC&nbsp;&nbsp;&nbsp;&nbsp;CIPHER&nbsp;&nbsp;AUTH&nbsp;&nbsp;ESSID
        </div>
        <div className="text-gray-600 text-xs mt-4">[ sin redes — inicia el escaneo en modo monitor ]</div>
      </div>
    )
  }

  return (
    <div className="font-mono text-xs bg-black/90 rounded-lg overflow-auto border border-green-900/30">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-[#0d0d0d] border-b border-green-900/40 px-3 py-2 text-green-400/60 whitespace-nowrap select-none flex items-center gap-1">
        <span className="inline-block" style={{width:'19ch'}}>BSSID</span>
        <span className="inline-block text-right" style={{width:'5ch'}}>PWR</span>
        <span className="inline-block text-right" style={{width:'9ch'}}>Beacons</span>
        <span className="inline-block text-right" style={{width:'7ch'}}>#Data</span>
        <span className="inline-block text-right" style={{width:'4ch'}}>CH</span>
        <span className="inline-block text-right" style={{width:'6ch'}}>MB</span>
        <span className="inline-block text-right" style={{width:'7ch'}}>ENC</span>
        <span className="inline-block text-right" style={{width:'8ch'}}>CIPHER</span>
        <span className="inline-block text-right" style={{width:'6ch'}}>AUTH</span>
        <span className="ml-3">ESSID</span>
      </div>

      {/* Rows */}
      <div>
        {networks.map((net) => {
          const selected  = net.bssid === selectedBssid
          const pwr       = typeof net.power === 'number' ? net.power : parseInt(String(net.power)) || 0
          const enc       = net.security || 'OPN'

          return (
            <div
              key={net.bssid}
              className={clsx(
                'flex items-center px-3 py-[3px] whitespace-nowrap transition-colors border-l-2',
                selected
                  ? 'bg-green-900/25 border-green-400 cursor-pointer'
                  : 'border-transparent hover:bg-white/[0.04] cursor-pointer'
              )}
              onClick={() => onSelect?.(net)}
            >
              <span className="inline-block text-cyan-400"      style={{width:'19ch'}}>{net.bssid}</span>
              <span className={clsx('inline-block text-right',  pwrColor(pwr))} style={{width:'5ch'}}>{pwr}</span>
              <span className="inline-block text-right text-gray-500" style={{width:'9ch'}}>{net.beacons ?? 0}</span>
              <span className="inline-block text-right text-gray-500" style={{width:'7ch'}}>{net.ivs ?? 0}</span>
              <span className="inline-block text-right text-yellow-400" style={{width:'4ch'}}>{net.channel}</span>
              <span className="inline-block text-right text-gray-600" style={{width:'6ch'}}>{net.speed ?? '-'}</span>
              <span className={clsx('inline-block text-right', encColor(enc))} style={{width:'7ch'}}>{enc}</span>
              <span className="inline-block text-right text-gray-400" style={{width:'8ch'}}>{net.cipher || '-'}</span>
              <span className="inline-block text-right text-gray-400" style={{width:'6ch'}}>{net.authentication || '-'}</span>
              <span className="ml-3 text-white/90 truncate max-w-xs">
                {net.essid || <span className="text-gray-600 italic">&lt;hidden&gt;</span>}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
