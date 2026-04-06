'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import { Play, Square, RefreshCw } from 'lucide-react'
import { getInterfaces, startScan, stopScan, getNetworks } from '@/lib/api'
import { NetworkTable } from '@/components/ui/NetworkTable'
import { StatusBadge } from '@/components/ui/Badge'
import { useWebSocket } from '@/lib/websocket'
import type { WifiInterface, Network } from '@/types'

export default function ScannerPage() {
  const [ifaces, setIfaces]         = useState<WifiInterface[]>([])
  const [selected, setSelected]     = useState('')
  const [scanning, setScanning]     = useState(false)
  const [networks, setNetworks]     = useState<Network[]>([])
  const [chosenNet, setChosenNet]   = useState<Network | null>(null)
  const [error, setError]           = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const { networks: wsNets, connected } = useWebSocket()

  // WS live updates take priority when scanning
  useEffect(() => {
    if (scanning && wsNets.length > 0) setNetworks(wsNets)
  }, [wsNets, scanning])

  // Polling fallback: every 3s while scanning (covers WebSocket gaps)
  useEffect(() => {
    if (scanning) {
      pollRef.current = setInterval(async () => {
        const data = await getNetworks().catch(() => [])
        if (data.length > 0) setNetworks(data)
      }, 3000)
    } else {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
    }
    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null } }
  }, [scanning])

  const loadIfaces = useCallback(async () => {
    try {
      const data = await getInterfaces()
      setIfaces(data)
      if (data.length > 0 && !selected) setSelected(data[0].name)
    } catch { /* ignore */ }
  }, [selected])

  useEffect(() => { loadIfaces() }, [loadIfaces])

  const handleStart = async () => {
    if (!selected) return
    setError('')
    try {
      await startScan(selected)
      setScanning(true)
    } catch (e: unknown) {
      setError((e as Error).message)
    }
  }

  const handleStop = async () => {
    try {
      await stopScan()
    } finally {
      setScanning(false)
      // Fetch final state
      const data = await getNetworks().catch(() => [])
      setNetworks(data)
    }
  }

  const handleRefreshOnce = async () => {
    const data = await getNetworks().catch(() => [])
    setNetworks(data)
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="card flex flex-wrap gap-4 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="section-title block">Interfaz (modo monitor)</label>
          <select
            className="input"
            value={selected}
            onChange={e => setSelected(e.target.value)}
            disabled={scanning}
          >
            {ifaces.length === 0
              ? <option value="">Sin interfaces</option>
              : ifaces.map(i => <option key={i.name} value={i.name}>{i.name} ({i.mode ?? 'Managed'})</option>)
            }
          </select>
        </div>

        <div className="flex items-center gap-2">
          <StatusBadge
            variant={scanning ? 'running' : 'idle'}
            label={scanning ? 'Escaneando' : 'Detenido'}
            pulse={scanning}
          />
          {!connected && <StatusBadge variant="warning" label="WS desconectado" />}
        </div>

        {!scanning ? (
          <button className="btn-primary" onClick={handleStart} disabled={!selected}>
            <Play className="w-4 h-4" /> Iniciar escaneo
          </button>
        ) : (
          <button className="btn-danger" onClick={handleStop}>
            <Square className="w-4 h-4" /> Detener
          </button>
        )}

        <button className="btn-ghost" onClick={handleRefreshOnce}>
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {error && (
        <div className="text-sm px-4 py-2 rounded-lg border bg-danger/10 text-danger border-danger/30 font-mono">
          {error}
        </div>
      )}

      {/* Selected network info */}
      {chosenNet && (
        <div className="card border-accent/30 bg-accent/5">
          <p className="section-title">Red seleccionada como objetivo</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm font-mono">
            <div><span className="text-muted">BSSID</span><br /><span className="text-accent">{chosenNet.bssid}</span></div>
            <div><span className="text-muted">ESSID</span><br /><span className="text-text">{chosenNet.essid || '—'}</span></div>
            <div><span className="text-muted">Canal</span><br /><span className="text-warning">{chosenNet.channel}</span></div>
            <div><span className="text-muted">Seguridad</span><br /><span className="text-text">{chosenNet.security}</span></div>
          </div>
        </div>
      )}

      {/* Network table */}
      <div className="card p-0">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border/60">
          <p className="section-title mb-0">
            Redes detectadas
            {networks.length > 0 && (
              <span className="ml-2 text-accent normal-case font-normal">{networks.length}</span>
            )}
          </p>
        </div>
        <div className="p-0">
          <NetworkTable
            networks={networks}
            onSelect={setChosenNet}
            selectedBssid={chosenNet?.bssid}
          />
        </div>
      </div>
    </div>
  )
}
