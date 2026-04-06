'use client'

import { useState, useEffect, useCallback } from 'react'
import { Globe, Play, Square, Users } from 'lucide-react'
import { getInterfaces, startPortal, stopPortal, getPortalStatus, getPortalCredentials } from '@/lib/api'
import { StatusBadge } from '@/components/ui/Badge'
import { useWebSocket } from '@/lib/websocket'
import type { WifiInterface, Credential, PortalStatus } from '@/types'

export default function EvilPortalPage() {
  const [ifaces, setIfaces]       = useState<WifiInterface[]>([])
  const [iface, setIface]         = useState('')
  const [ssid, setSsid]           = useState('Free_WiFi')
  const [passphrase, setPassphrase] = useState('')
  const [portalCh, setPortalCh]   = useState(6)
  const [status, setStatus]       = useState<PortalStatus>({ running: false, credentials_count: 0 })
  const [credentials, setCreds]   = useState<Credential[]>([])
  const [error, setError]         = useState('')

  const { subscribe } = useWebSocket()

  const refreshStatus = useCallback(async () => {
    const s = await getPortalStatus().catch(() => null)
    if (s) setStatus(s)
    const c = await getPortalCredentials().catch(() => [])
    setCreds(c)
  }, [])

  useEffect(() => {
    getInterfaces().then(d => { setIfaces(d); if (d.length && !iface) setIface(d[0].name) }).catch(console.error)
    refreshStatus()
  }, [refreshStatus])

  // Real-time credential captures
  useEffect(() => {
    return subscribe('credential_captured', (msg) => {
      const d = msg.data as { username: string; password: string }
      setCreds(prev => [
        {
          id: Date.now(),
          source: 'evil_portal',
          username: d.username,
          password: d.password,
          capture_date: new Date().toISOString(),
        },
        ...prev,
      ])
      setStatus(prev => ({ ...prev, credentials_count: prev.credentials_count + 1 }))
    })
  }, [subscribe])

  const handleStart = async () => {
    setError('')
    try {
      await startPortal(ssid, iface, passphrase || undefined, portalCh)
      await refreshStatus()
    } catch (e: unknown) { setError((e as Error).message) }
  }

  const handleStop = async () => {
    try { await stopPortal() } finally { await refreshStatus() }
  }

  return (
    <div className="max-w-5xl space-y-6">
      {/* Config */}
      <div className="card space-y-4">
        <p className="section-title flex items-center gap-2">
          <Globe className="w-3.5 h-3.5" /> Evil Portal — Rogue AP
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="text-xs text-muted mb-1 block">Interfaz</label>
            <select className="input" value={iface} onChange={e => setIface(e.target.value)} disabled={status.running}>
              {ifaces.map(i => <option key={i.name} value={i.name}>{i.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-muted mb-1 block">SSID del portal</label>
            <input className="input" value={ssid} onChange={e => setSsid(e.target.value)} disabled={status.running} />
          </div>
          <div>
            <label className="text-xs text-muted mb-1 block">Canal</label>
            <input className="input" type="number" min={1} max={13} value={portalCh}
              onChange={e => setPortalCh(Number(e.target.value))} disabled={status.running} />
          </div>
          <div>
            <label className="text-xs text-muted mb-1 block">Contraseña AP (vacío=abierto)</label>
            <input className="input" type="password" value={passphrase}
              onChange={e => setPassphrase(e.target.value)} disabled={status.running} />
          </div>
        </div>

        {error && <p className="text-danger text-xs font-mono">{error}</p>}

        <div className="flex gap-2 items-center">
          <StatusBadge variant={status.running ? 'running' : 'idle'}
            label={status.running ? `Activo · ${status.ssid}` : 'Inactivo'} pulse={status.running} />
          <StatusBadge variant="warning" label={`${status.credentials_count} capturas`} />

          {!status.running ? (
            <button className="btn-primary" onClick={handleStart} disabled={!ssid || !iface}>
              <Play className="w-4 h-4" /> Iniciar portal
            </button>
          ) : (
            <button className="btn-danger" onClick={handleStop}>
              <Square className="w-4 h-4" /> Detener portal
            </button>
          )}
        </div>
      </div>

      {/* Credentials table */}
      <div className="card">
        <p className="section-title flex items-center gap-2">
          <Users className="w-3.5 h-3.5" /> Credenciales capturadas
        </p>
        {credentials.length === 0 ? (
          <p className="text-muted text-sm text-center py-8">
            {status.running ? 'Esperando víctimas...' : 'Sin credenciales capturadas'}
          </p>
        ) : (
          <div className="overflow-auto rounded-lg border border-border/40">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-border/40 bg-surface text-muted">
                  <th className="text-left px-3 py-2">IP</th>
                  <th className="text-left px-3 py-2">Usuario</th>
                  <th className="text-left px-3 py-2">Contraseña</th>
                  <th className="text-left px-3 py-2">Hora</th>
                </tr>
              </thead>
              <tbody>
                {credentials.map(c => (
                  <tr key={c.id} className="border-b border-border/20 hover:bg-surface/50">
                    <td className="px-3 py-2 text-accent">{c.ip_address ?? '—'}</td>
                    <td className="px-3 py-2 text-text">{c.username ?? '—'}</td>
                    <td className="px-3 py-2 text-success font-bold">{c.password}</td>
                    <td className="px-3 py-2 text-muted">{new Date(c.capture_date).toLocaleTimeString('es')}</td>
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
