'use client'

import { useState, useEffect, useCallback } from 'react'
import { Play, Square, Zap, List } from 'lucide-react'
import {
  getInterfaces, startCapture, stopCapture, sendDeauth, getHandshakes,
} from '@/lib/api'
import { Terminal } from '@/components/ui/Terminal'
import { StatusBadge } from '@/components/ui/Badge'
import { useWebSocket } from '@/lib/websocket'
import type { WifiInterface, Handshake } from '@/types'

export default function HandshakePage() {
  const [ifaces, setIfaces]     = useState<WifiInterface[]>([])
  const [iface, setIface]       = useState('')
  const [bssid, setBssid]       = useState('')
  const [channel, setChannel]   = useState<number>(1)
  const [capturing, setCapturing] = useState(false)
  const [handshakes, setHandshakes] = useState<Handshake[]>([])
  const [lines, setLines]       = useState<string[]>([])
  const [error, setError]       = useState('')

  const { subscribe, logs } = useWebSocket()

  useEffect(() => {
    getInterfaces().then(d => {
      setIfaces(d)
      if (d.length && !iface) setIface(d[0].name)
    }).catch(console.error)
    getHandshakes().then(setHandshakes).catch(console.error)
  }, [])

  // Listen for handshake detection events
  useEffect(() => {
    return subscribe('handshake_detected', (msg) => {
      const d = msg.data as { bssid: string }
      setLines(prev => [...prev, `[✓] HANDSHAKE CAPTURADO: ${d.bssid}`])
      getHandshakes().then(setHandshakes).catch(console.error)
    })
  }, [subscribe])

  // Listen for command output
  useEffect(() => {
    return subscribe('command_output', (msg) => {
      const d = msg.data as { line: string }
      setLines(prev => [...prev, d.line])
    })
  }, [subscribe])

  const handleStart = async () => {
    if (!bssid || !iface) return
    setError('')
    setLines([])
    try {
      await startCapture(bssid, channel, iface)
      setCapturing(true)
    } catch (e: unknown) { setError((e as Error).message) }
  }

  const handleStop = async () => {
    try { await stopCapture() } finally { setCapturing(false) }
  }

  const handleDeauth = async () => {
    if (!bssid || !iface) return
    try {
      await sendDeauth(bssid, iface, undefined, 64)
      setLines(prev => [...prev, `[*] Enviando paquetes deauth a ${bssid}...`])
    } catch (e: unknown) { setError((e as Error).message) }
  }

  return (
    <div className="max-w-5xl space-y-6">
      {/* Config */}
      <div className="card space-y-4">
        <p className="section-title">Configuración de captura</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="text-xs text-muted mb-1 block">Interfaz (monitor)</label>
            <select className="input" value={iface} onChange={e => setIface(e.target.value)} disabled={capturing}>
              {ifaces.map(i => <option key={i.name} value={i.name}>{i.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted mb-1 block">BSSID objetivo</label>
            <input className="input" placeholder="AA:BB:CC:DD:EE:FF" value={bssid}
              onChange={e => setBssid(e.target.value.toUpperCase())} disabled={capturing} />
          </div>
          <div>
            <label className="text-xs text-muted mb-1 block">Canal</label>
            <input className="input" type="number" min={1} max={14} value={channel}
              onChange={e => setChannel(Number(e.target.value))} disabled={capturing} />
          </div>
        </div>

        <div className="flex gap-2 flex-wrap">
          <StatusBadge variant={capturing ? 'running' : 'idle'} label={capturing ? 'Capturando' : 'Inactivo'} pulse={capturing} />
          {!capturing ? (
            <button className="btn-primary" onClick={handleStart} disabled={!bssid || !iface}>
              <Play className="w-4 h-4" /> Iniciar captura
            </button>
          ) : (
            <button className="btn-danger" onClick={handleStop}>
              <Square className="w-4 h-4" /> Detener
            </button>
          )}
          <button className="btn-success" onClick={handleDeauth} disabled={!bssid || !iface}>
            <Zap className="w-4 h-4" /> Enviar deauth
          </button>
        </div>

        {error && <p className="text-danger text-sm font-mono">{error}</p>}
      </div>

      {/* Terminal output */}
      <Terminal lines={lines} title="airodump-ng / output" loading={capturing} height="h-64" />

      {/* Handshake list */}
      <div className="card">
        <p className="section-title flex items-center gap-2">
          <List className="w-3.5 h-3.5" /> Handshakes capturados ({handshakes.length})
        </p>
        {handshakes.length === 0 ? (
          <p className="text-muted text-sm text-center py-6">Sin handshakes capturados</p>
        ) : (
          <div className="overflow-auto rounded-lg border border-border/40">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-border/40 bg-surface text-muted">
                  <th className="text-left px-3 py-2">Archivo</th>
                  <th className="text-left px-3 py-2">Red</th>
                  <th className="text-center px-3 py-2">Craqueado</th>
                  <th className="text-left px-3 py-2">Contraseña</th>
                  <th className="text-left px-3 py-2">Fecha</th>
                </tr>
              </thead>
              <tbody>
                {handshakes.map(h => (
                  <tr key={h.id} className="border-b border-border/20 hover:bg-surface/50">
                    <td className="px-3 py-2 text-accent truncate max-w-[200px]">{h.capture_file}</td>
                    <td className="px-3 py-2 text-text">{h.essid ?? h.bssid ?? '—'}</td>
                    <td className="px-3 py-2 text-center">
                      {h.cracked
                        ? <span className="text-success">✓</span>
                        : <span className="text-muted">—</span>}
                    </td>
                    <td className="px-3 py-2 text-success">{h.password ?? '—'}</td>
                    <td className="px-3 py-2 text-muted">{new Date(h.capture_date).toLocaleDateString('es')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
