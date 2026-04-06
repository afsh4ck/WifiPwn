'use client'

import { useEffect, useState, useCallback } from 'react'
import { RefreshCw, Monitor, MonitorOff, Shuffle, OctagonX } from 'lucide-react'
import { getInterfaces, enableMonitor, disableMonitor, killAirmon, changeMac } from '@/lib/api'
import { StatusBadge } from '@/components/ui/Badge'
import type { WifiInterface } from '@/types'

export default function InterfacesPage() {
  const [interfaces, setIfaces]       = useState<WifiInterface[]>([])
  const [loading, setLoading]         = useState(false)
  const [busy, setBusy]               = useState<string | null>(null)
  const [message, setMessage]         = useState<{ text: string; ok: boolean } | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getInterfaces()
      setIfaces(data)
    } catch (e: unknown) {
      setMessage({ text: (e as Error).message, ok: false })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const withBusy = async (key: string, fn: () => Promise<unknown>) => {
    setBusy(key)
    setMessage(null)
    try {
      const res = await fn() as { message?: string }
      setMessage({ text: res?.message ?? 'Operación completada', ok: true })
      await load()
    } catch (e: unknown) {
      setMessage({ text: (e as Error).message, ok: false })
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text">Interfaces de red inalámbricas</h2>
        <div className="flex gap-2">
          <button className="btn-ghost" onClick={load} disabled={loading}>
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Actualizar
          </button>
          <button
            className="btn-danger"
            onClick={() => withBusy('kill', killAirmon)}
            disabled={busy === 'kill'}
          >
            <OctagonX className="w-4 h-4" />
            Kill processes
          </button>
        </div>
      </div>

      {message && (
        <div className={`text-sm px-4 py-2 rounded-lg border font-mono ${message.ok
          ? 'bg-success/10 text-success border-success/30'
          : 'bg-danger/10 text-danger border-danger/30'}`}>
          {message.text}
        </div>
      )}

      {interfaces.length === 0 && !loading && (
        <div className="card text-center text-muted py-10">
          No se detectaron interfaces inalámbricas.
        </div>
      )}

      <div className="grid gap-4">
        {interfaces.map((iface) => {
          const isMonitor = iface.mode === 'Monitor'
          const id = iface.name
          return (
            <div key={id} className="card flex items-center gap-4">
              {/* Icon */}
              <div className={`p-3 rounded-lg ${isMonitor ? 'bg-accent/10 text-accent' : 'bg-surface text-muted'}`}>
                <Monitor className="w-5 h-5" />
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono font-bold text-text">{iface.name}</span>
                  <StatusBadge
                    variant={isMonitor ? 'running' : 'idle'}
                    label={iface.mode ?? 'Managed'}
                    pulse={isMonitor}
                  />
                </div>
                <p className="text-xs text-muted font-mono">MAC: {iface.mac ?? 'N/A'}</p>
              </div>

              {/* Actions */}
              <div className="flex gap-2 shrink-0">
                {isMonitor ? (
                  <button
                    className="btn-ghost text-xs"
                    disabled={busy === id}
                    onClick={() => withBusy(id, () => disableMonitor(iface.name))}
                  >
                    <MonitorOff className="w-3.5 h-3.5" />
                    Modo managed
                  </button>
                ) : (
                  <button
                    className="btn-primary text-xs"
                    disabled={busy === id}
                    onClick={() => withBusy(id, () => enableMonitor(iface.name))}
                  >
                    <Monitor className="w-3.5 h-3.5" />
                    Modo monitor
                  </button>
                )}
                <button
                  className="btn-ghost text-xs"
                  disabled={busy === id + '_mac'}
                  onClick={() => withBusy(id + '_mac', () => changeMac(iface.name))}
                >
                  <Shuffle className="w-3.5 h-3.5" />
                  Cambiar MAC
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
