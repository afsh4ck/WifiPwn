'use client'

import { useState, useEffect } from 'react'
import { Skull, Play, Square } from 'lucide-react'
import { getInterfaces, sendDeauthAttack, stopDeauth, getDeauthHistory } from '@/lib/api'
import { Terminal } from '@/components/ui/Terminal'
import { StatusBadge } from '@/components/ui/Badge'
import { useWebSocket } from '@/lib/websocket'
import type { WifiInterface } from '@/types'

export default function DeauthPage() {
  const [ifaces, setIfaces]       = useState<WifiInterface[]>([])
  const [iface, setIface]         = useState('')
  const [bssid, setBssid]         = useState('')
  const [client, setClient]       = useState('')
  const [packets, setPackets]     = useState(100)
  const [continuous, setContinuous] = useState(false)
  const [running, setRunning]     = useState(false)
  const [lines, setLines]         = useState<string[]>([])
  const [history, setHistory]     = useState<Record<string, unknown>[]>([])
  const [error, setError]         = useState('')

  const { subscribe } = useWebSocket()

  useEffect(() => {
    getInterfaces().then(d => { setIfaces(d); if (d.length && !iface) setIface(d[0].name) }).catch(console.error)
    getDeauthHistory().then(setHistory).catch(console.error)
  }, [])

  useEffect(() => {
    return subscribe('command_output', (msg) => {
      const d = msg.data as { line: string }
      setLines(prev => [...prev, d.line])
    })
  }, [subscribe])

  const handleStart = async () => {
    if (!bssid || !iface) return
    setError('')
    setLines([`[*] Enviando deauth a ${bssid}${client ? ` (cliente: ${client})` : ' (broadcast)'}...`])
    try {
      await sendDeauthAttack(bssid, iface, client || undefined, packets, continuous)
      setRunning(continuous)
      if (!continuous) {
        setLines(prev => [...prev, '[✓] Paquetes enviados'])
        getDeauthHistory().then(setHistory).catch(console.error)
      }
    } catch (e: unknown) {
      setError((e as Error).message)
      setRunning(false)
    }
  }

  const handleStop = async () => {
    try { await stopDeauth() } finally {
      setRunning(false)
      setLines(prev => [...prev, '[*] Ataque detenido'])
      getDeauthHistory().then(setHistory).catch(console.error)
    }
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div className="card border-danger/20 space-y-4">
        <p className="section-title flex items-center gap-2 text-danger">
          <Skull className="w-3.5 h-3.5" /> Ataque Deauthentication (802.11)
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-muted mb-1 block">Interfaz (monitor)</label>
            <select className="input" value={iface} onChange={e => setIface(e.target.value)} disabled={running}>
              {ifaces.map(i => <option key={i.name} value={i.name}>{i.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted mb-1 block">BSSID del AP objetivo *</label>
            <input className="input font-mono" placeholder="AA:BB:CC:DD:EE:FF" value={bssid}
              onChange={e => setBssid(e.target.value.toUpperCase())} disabled={running} />
          </div>
          <div>
            <label className="text-xs text-muted mb-1 block">MAC cliente (vacío = broadcast)</label>
            <input className="input font-mono" placeholder="FF:FF:FF:FF:FF:FF" value={client}
              onChange={e => setClient(e.target.value.toUpperCase())} disabled={running} />
          </div>
          <div>
            <label className="text-xs text-muted mb-1 block">Número de paquetes</label>
            <input className="input" type="number" min={1} max={9999} value={packets}
              onChange={e => setPackets(Number(e.target.value))} disabled={running || continuous} />
          </div>
        </div>

        <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
          <input type="checkbox" className="w-4 h-4 accent-danger rounded"
            checked={continuous} onChange={e => setContinuous(e.target.checked)} disabled={running} />
          <span className="text-text">Ataque continuo</span>
          <span className="text-muted text-xs">(hasta detener manualmente)</span>
        </label>

        {error && <p className="text-danger text-xs font-mono">{error}</p>}

        <div className="flex gap-2 items-center">
          <StatusBadge variant={running ? 'running' : 'idle'} label={running ? 'Atacando' : 'Inactivo'} pulse={running} />
          {!running ? (
            <button className="btn-danger" onClick={handleStart} disabled={!bssid || !iface}>
              <Play className="w-4 h-4" /> Enviar deauth
            </button>
          ) : (
            <button className="btn-ghost" onClick={handleStop}>
              <Square className="w-4 h-4" /> Detener
            </button>
          )}
        </div>
      </div>

      <Terminal lines={lines} title="aireplay-ng / deauth" loading={running} height="h-48" />

      {history.length > 0 && (
        <div className="card">
          <p className="section-title">Historial de ataques</p>
          <div className="overflow-auto rounded-lg border border-border/40">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-border/40 bg-surface text-muted">
                  <th className="text-left px-3 py-2">BSSID</th>
                  <th className="text-left px-3 py-2">Cliente</th>
                  <th className="text-center px-3 py-2">Paquetes</th>
                  <th className="text-left px-3 py-2">Fecha</th>
                </tr>
              </thead>
              <tbody>
                {history.map((h, i) => (
                  <tr key={i} className="border-b border-border/20 hover:bg-surface/50">
                    <td className="px-3 py-2 text-accent">{String(h.bssid ?? '—')}</td>
                    <td className="px-3 py-2 text-text">{String(h.client_mac ?? 'broadcast')}</td>
                    <td className="px-3 py-2 text-center text-warning">{String(h.packets_sent ?? '—')}</td>
                    <td className="px-3 py-2 text-muted">{h.attack_date ? new Date(String(h.attack_date)).toLocaleString('es') : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
