'use client'

import { useState, useEffect } from 'react'
import { Key, Play, Square, Download } from 'lucide-react'
import { getHandshakes, startCrack, stopCrack, downloadHandshake } from '@/lib/api'
import { Terminal } from '@/components/ui/Terminal'
import { StatusBadge } from '@/components/ui/Badge'
import { useWebSocket } from '@/lib/websocket'
import type { Handshake } from '@/types'

const COMMON_WORDLISTS = [
  '/usr/share/wordlists/rockyou.txt',
  '/usr/share/wordlists/fasttrack.txt',
  '/usr/share/wordlists/dirb/common.txt',
]

export default function CrackingPage() {
  const [handshakes, setHandshakes]   = useState<Handshake[]>([])
  const [captureFile, setCaptureFile] = useState('')
  const [wordlist, setWordlist]       = useState(COMMON_WORDLISTS[0])
  const [bssid, setBssid]             = useState('')
  const [cmdId, setCmdId]             = useState<string | null>(null)
  const [running, setRunning]         = useState(false)
  const [lines, setLines]             = useState<string[]>([])
  const [error, setError]             = useState('')

  const { subscribe } = useWebSocket()

  useEffect(() => {
    getHandshakes().then(setHandshakes).catch(console.error)
  }, [])

  // Refresh handshake list when a new one is captured
  useEffect(() => {
    return subscribe('handshake_detected', () => {
      getHandshakes().then(setHandshakes).catch(console.error)
      setTimeout(() => getHandshakes().then(setHandshakes).catch(console.error), 2000)
    })
  }, [subscribe])

  // Stream command output
  useEffect(() => {
    return subscribe('command_output', (msg) => {
      const d = msg.data as { cmd_id: string; line: string }
      if (!cmdId || d.cmd_id === cmdId) {
        setLines(prev => [...prev, d.line])
        // detect success
        if (d.line.toLowerCase().includes('key found') || d.line.toLowerCase().includes('password')) {
          setRunning(false)
        }
      }
    })
  }, [subscribe, cmdId])

  const handleStart = async () => {
    if (!captureFile || !wordlist) return
    setError('')
    setLines([])
    try {
      const res = await startCrack(captureFile, wordlist, bssid || undefined) as { cmd_id: string }
      setCmdId(res.cmd_id)
      setRunning(true)
    } catch (e: unknown) { setError((e as Error).message) }
  }

  const handleStop = async () => {
    if (!cmdId) return
    try { await stopCrack(cmdId) } finally { setRunning(false) }
  }

  const handleSelectHandshake = (h: Handshake) => {
    setCaptureFile(h.capture_file)
    setBssid(h.bssid ?? '')
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Config */}
        <div className="card space-y-4">
          <p className="section-title flex items-center gap-2">
            <Key className="w-3.5 h-3.5" /> Configuración
          </p>

          <div>
            <label className="text-xs text-muted mb-1 block">Archivo de captura (.cap / .hccapx)</label>
            <input className="input" value={captureFile}
              onChange={e => setCaptureFile(e.target.value)}
              placeholder="/path/to/capture.cap" disabled={running} />
          </div>

          <div>
            <label className="text-xs text-muted mb-1 block">Wordlist</label>
            <select className="input" value={wordlist} onChange={e => setWordlist(e.target.value)} disabled={running}>
              {COMMON_WORDLISTS.map(w => <option key={w} value={w}>{w}</option>)}
            </select>
            <input className="input mt-2" value={wordlist} onChange={e => setWordlist(e.target.value)}
              placeholder="O escribe ruta personalizada..." disabled={running} />
          </div>

          <div>
            <label className="text-xs text-muted mb-1 block">BSSID (opcional)</label>
            <input className="input font-mono" value={bssid} onChange={e => setBssid(e.target.value.toUpperCase())}
              placeholder="AA:BB:CC:DD:EE:FF" disabled={running} />
          </div>

          {error && <p className="text-danger text-xs font-mono">{error}</p>}

          <div className="flex gap-2 items-center">
            <StatusBadge variant={running ? 'running' : 'idle'} label={running ? 'Craqueando' : 'Inactivo'} pulse={running} />
            {!running ? (
              <button className="btn-primary" onClick={handleStart} disabled={!captureFile || !wordlist}>
                <Play className="w-4 h-4" /> Iniciar aircrack-ng
              </button>
            ) : (
              <button className="btn-danger" onClick={handleStop}>
                <Square className="w-4 h-4" /> Detener
              </button>
            )}
          </div>
        </div>

        {/* Handshake selector */}
        <div className="card">
          <p className="section-title">Seleccionar handshake guardado</p>
          {handshakes.length === 0 ? (
            <p className="text-muted text-sm text-center py-6">No hay handshakes almacenados</p>
          ) : (
            <div className="space-y-1 max-h-[280px] overflow-y-auto">
              {handshakes.map(h => (
                <div key={h.id} className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-mono transition-colors border ${
                    captureFile === h.capture_file
                      ? 'border-accent/40 bg-accent/10 text-accent'
                      : 'border-transparent hover:bg-surface text-muted hover:text-text'
                  }`}>
                  <button
                    onClick={() => handleSelectHandshake(h)}
                    className="flex-1 text-left min-w-0"
                  >
                    <div className="text-text">{h.essid ?? h.bssid}</div>
                    <div className="text-muted/60 truncate">{h.capture_file}</div>
                    {h.cracked && <div className="text-success mt-0.5">\u2713 {h.password}</div>}
                  </button>
                  <a href={downloadHandshake(h.id)} download
                    className="shrink-0 p-1 text-accent hover:text-cyan-300 transition-colors"
                    title="Descargar .pcap">
                    <Download className="w-3.5 h-3.5" />
                  </a>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Terminal */}
      <Terminal lines={lines} title="aircrack-ng output" loading={running} height="h-80" />
    </div>
  )
}
