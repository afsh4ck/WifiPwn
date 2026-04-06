'use client'

import { useState, useCallback, useEffect, useRef, useMemo } from 'react'
import { Play, Square, RefreshCw, Wifi, WifiOff, AlertTriangle, ShieldAlert } from 'lucide-react'
import { getInterfaces, getInterfaceInfo, enableMonitor, startScan, stopScan, getNetworks } from '@/lib/api'
import { NetworkTable } from '@/components/ui/NetworkTable'
import { StatusBadge } from '@/components/ui/Badge'
import { useWebSocket } from '@/lib/websocket'
import { useWifi } from '@/lib/context'
import type { WifiInterface, Network } from '@/types'

export default function ScannerPage() {
  const { networks, mergeNetworks, clearNetworks, target, setTarget } = useWifi()

  const [ifaces, setIfaces]           = useState<WifiInterface[]>([])
  const [selected, setSelected]       = useState('')
  const [ifaceMode, setIfaceMode]     = useState<string>('')
  const [enablingMon, setEnablingMon] = useState(false)
  const [scanning, setScanning]       = useState(false)
  const [error, setError]             = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const { networks: wsNets, connected } = useWebSocket()

  // ── Vulnerability scoring ──────────────────────────────────────────
  const vulnScore = useCallback((n: Network): number => {
    const enc = (n.security || '').toUpperCase()
    let score = 0
    // Encryption weakness (higher = more vulnerable)
    if (enc.includes('OPN') || enc === '' || enc === 'OPEN')       score += 100
    else if (enc.includes('WEP'))                                   score += 80
    else if (enc.includes('WPA') && !enc.includes('WPA2'))          score += 40
    else if (enc.includes('WPA2') && !enc.includes('WPA3'))         score += 20
    else if (enc.includes('WPA3'))                                  score += 5
    // Signal strength bonus (closer = easier to attack)
    const pwr = typeof n.power === 'number' ? n.power : -100
    score += Math.max(0, 100 + pwr) / 2  // -30dBm → +35, -80dBm → +10
    // WPS bonus
    if (n.wps) score += 15
    // TKIP is weaker than CCMP
    if ((n.cipher || '').toUpperCase().includes('TKIP')) score += 10
    return score
  }, [])

  const top5Vuln = useMemo(() => {
    if (networks.length === 0) return []
    return [...networks]
      .sort((a, b) => vulnScore(b) - vulnScore(a))
      .slice(0, 5)
  }, [networks, vulnScore])

  // WS live updates take priority when scanning
  useEffect(() => {
    if (scanning && wsNets.length > 0) mergeNetworks(wsNets)
  }, [wsNets, scanning])

  // Polling fallback: every 3s while scanning
  useEffect(() => {
    if (scanning) {
      pollRef.current = setInterval(async () => {
        const data = await getNetworks().catch(() => [])
        if (data.length > 0) mergeNetworks(data)
      }, 3000)
    } else {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
    }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null } }
  }, [scanning])

  const loadIfaceMode = useCallback(async (name: string) => {
    if (!name) return
    try {
      const info = await getInterfaceInfo(name)
      setIfaceMode(info.mode ?? 'Managed')
    } catch { setIfaceMode('') }
  }, [])

  const loadIfaces = useCallback(async () => {
    try {
      const data = await getInterfaces()
      setIfaces(data)
      if (data.length > 0 && !selected) {
        setSelected(data[0].name)
        loadIfaceMode(data[0].name)
      }
    } catch { /* ignore */ }
  }, [selected, loadIfaceMode])

  useEffect(() => { loadIfaces() }, [loadIfaces])

  const handleIfaceChange = (name: string) => {
    setSelected(name)
    setIfaceMode('')
    loadIfaceMode(name)
  }

  const isMonitor = ifaceMode.toLowerCase() === 'monitor'

  const handleEnableMonitor = async () => {
    if (!selected) return
    setEnablingMon(true)
    setError('')
    try {
      await enableMonitor(selected)
      await loadIfaceMode(selected)
    } catch (e: unknown) {
      setError((e as Error).message)
    } finally {
      setEnablingMon(false)
    }
  }

  const handleStart = async () => {
    if (!selected) return
    setError('')
    clearNetworks()
    try {
      await startScan(selected)   // backend auto-enables monitor if needed
      setScanning(true)
      setIfaceMode('Monitor')     // optimistic update
    } catch (e: unknown) {
      setError((e as Error).message)
    }
  }

  const handleStop = async () => {
    try { await stopScan() } finally {
      setScanning(false)
      const data = await getNetworks().catch(() => [])
      if (data.length > 0) mergeNetworks(data)
      loadIfaceMode(selected)
    }
  }

  return (
    <div className="space-y-4">
      {/* Controls bar */}
      <div className="card flex flex-wrap gap-4 items-center">
        {/* Interface selector */}
        <div className="flex items-center gap-2">
          <label className="text-muted text-sm whitespace-nowrap">Interfaz:</label>
          <select
            className="input py-1"
            value={selected}
            onChange={e => handleIfaceChange(e.target.value)}
            disabled={scanning}
          >
            {ifaces.length === 0
              ? <option value="">Sin interfaces</option>
              : ifaces.map(i => <option key={i.name} value={i.name}>{i.name}</option>)
            }
          </select>
        </div>

        {/* Monitor mode status */}
        <div className="flex items-center gap-2">
          {isMonitor ? (
            <span className="flex items-center gap-1.5 text-xs font-mono px-2 py-1 rounded-md bg-green-500/10 text-green-400 border border-green-500/20">
              <Wifi className="w-3 h-3" /> Monitor
            </span>
          ) : ifaceMode ? (
            <span className="flex items-center gap-1.5 text-xs font-mono px-2 py-1 rounded-md bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
              <WifiOff className="w-3 h-3" /> {ifaceMode || 'Managed'}
            </span>
          ) : null}
        </div>

        <div className="flex items-center gap-2 ml-auto">
          {/* Enable monitor button (when not in monitor and not scanning) */}
          {!isMonitor && !scanning && selected && (
            <button
              className="btn-ghost text-yellow-400 border-yellow-500/30 hover:border-yellow-400 text-xs"
              onClick={handleEnableMonitor}
              disabled={enablingMon}
            >
              <Wifi className="w-3.5 h-3.5" />
              {enablingMon ? 'Activando...' : 'Activar monitor'}
            </button>
          )}

          <StatusBadge
            variant={scanning ? 'running' : 'idle'}
            label={scanning ? `Escaneando (${networks.length})` : 'Detenido'}
            pulse={scanning}
          />

          {!connected && <StatusBadge variant="warning" label="WS off" />}

          {!scanning ? (
            <button className="btn-primary" onClick={handleStart} disabled={!selected}>
              <Play className="w-4 h-4" /> Escanear
            </button>
          ) : (
            <button className="btn-danger" onClick={handleStop}>
              <Square className="w-4 h-4" /> Detener
            </button>
          )}

          <button className="btn-ghost" title="Refrescar" onClick={async () => {
            clearNetworks()
            const data = await getNetworks().catch(() => [])
            if (data.length > 0) mergeNetworks(data)
          }}>
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-sm px-4 py-2 rounded-lg border bg-danger/10 text-danger border-danger/30 font-mono">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />{error}
        </div>
      )}

      {/* Warning: not in monitor mode */}
      {!isMonitor && !scanning && ifaceMode && (
        <div className="flex items-center gap-2 text-sm px-4 py-2 rounded-lg border bg-yellow-500/10 text-yellow-400 border-yellow-500/20">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span>{selected} está en modo <strong>{ifaceMode}</strong>. Al pulsar Escanear se activará el modo monitor automáticamente.</span>
        </div>
      )}

      {/* Selected target detail */}
      {target && (
        <div className="card border-green-500/20 bg-green-900/10 font-mono text-sm">
          <div className="flex items-center justify-between mb-2">
            <p className="text-green-400 text-xs tracking-widest">TARGET SELECCIONADO</p>
            <button
              className="text-gray-500 hover:text-red-400 text-xs"
              onClick={() => setTarget(null)}
            >✕ Quitar</button>
          </div>
          <div className="flex flex-wrap gap-6">
            <div><span className="text-gray-500 text-xs">BSSID</span><br /><span className="text-cyan-400">{target.bssid}</span></div>
            <div><span className="text-gray-500 text-xs">ESSID</span><br /><span className="text-white">{target.essid || '—'}</span></div>
            <div><span className="text-gray-500 text-xs">CH</span><br /><span className="text-yellow-400">{target.channel}</span></div>
            <div><span className="text-gray-500 text-xs">ENC</span><br /><span className="text-green-400">{target.security}</span></div>
            <div><span className="text-gray-500 text-xs">CIPHER</span><br /><span className="text-gray-300">{target.cipher}</span></div>
            <div><span className="text-gray-500 text-xs">AUTH</span><br /><span className="text-gray-300">{target.authentication}</span></div>
            <div><span className="text-gray-500 text-xs">PWR</span><br /><span className="text-orange-400">{target.power} dBm</span></div>
          </div>
        </div>
      )}

      {/* Top 5 most vulnerable */}
      {top5Vuln.length > 0 && (
        <div className="card p-0 overflow-hidden border-red-500/20">
          <div className="flex items-center gap-2 px-5 py-3 border-b border-red-500/20 bg-red-500/5">
            <ShieldAlert className="w-4 h-4 text-red-400" />
            <p className="text-sm font-semibold text-red-400 tracking-wide">TOP 5 — REDES MÁS VULNERABLES</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-5 divide-y sm:divide-y-0 sm:divide-x divide-border/30">
            {top5Vuln.map((n, i) => {
              const enc = (n.security || 'OPN').toUpperCase()
              const isOpen = enc.includes('OPN') || enc === '' || enc === 'OPEN'
              const isWep = enc.includes('WEP')
              const color = isOpen ? 'text-red-400' : isWep ? 'text-orange-400' : 'text-yellow-400'
              return (
                <button
                  key={n.bssid}
                  className="flex flex-col items-center gap-1.5 px-3 py-3 hover:bg-surface/60 transition-colors cursor-pointer text-center"
                  onClick={() => setTarget(n)}
                >
                  <span className="text-[10px] font-bold text-muted">#{i + 1}</span>
                  <span className="text-xs font-bold text-text truncate max-w-full">{n.essid || '(oculta)'}</span>
                  <span className={`text-[11px] font-mono font-bold ${color}`}>{enc || 'OPN'}</span>
                  <span className="text-[10px] text-muted font-mono">{n.bssid}</span>
                  <span className="text-[10px] text-muted">CH{n.channel} · {n.power}dBm</span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Network table */}
      <div className="card p-0 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-border/60">
          <p className="section-title mb-0 text-sm">
            Redes detectadas
            {networks.length > 0 && (
              <span className="ml-2 text-accent font-normal normal-case">{networks.length}</span>
            )}
          </p>
          {scanning && (
            <span className="text-xs text-muted animate-pulse">actualizando cada 2s…</span>
          )}
        </div>
        <NetworkTable
          networks={networks}
          onSelect={setTarget}
          selectedBssid={target?.bssid}
        />
      </div>
    </div>
  )
}
