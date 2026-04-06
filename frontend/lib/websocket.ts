'use client'

import { useEffect, useRef, useCallback, useState } from 'react'
import type { WSMessage, LogEntry, Network, CommandOutputData } from '@/types'

const WS_URL = typeof window !== 'undefined'
  ? `ws://${window.location.hostname}:8000/ws`
  : 'ws://localhost:8000/ws'

export type WSHandler = (msg: WSMessage) => void

interface UseWebSocketReturn {
  connected: boolean
  logs: LogEntry[]
  networks: Network[]
  subscribe: (type: WSMessage['type'] | '*', handler: WSHandler) => () => void
  send: (data: unknown) => void
}

export function useWebSocket(): UseWebSocketReturn {
  const ws               = useRef<WebSocket | null>(null)
  const handlers         = useRef<Map<string, Set<WSHandler>>>(new Map())
  const reconnectTimer   = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [connected, setConnected] = useState(false)
  const [logs,     setLogs]     = useState<LogEntry[]>([])
  const [networks, setNetworks] = useState<Network[]>([])

  const dispatch = useCallback((msg: WSMessage) => {
    // Global listeners
    handlers.current.get('*')?.forEach(h => h(msg))
    // Type-specific listeners
    handlers.current.get(msg.type)?.forEach(h => h(msg))

    // Built-in state updaters
    if (msg.type === 'log') {
      const d = msg.data as { level: string; message: string; source?: string }
      setLogs(prev => [
        ...prev.slice(-499),
        { level: d.level as LogEntry['level'], message: d.message, timestamp: msg.timestamp, source: d.source },
      ])
    }
    if (msg.type === 'scan_update') {
      const d = msg.data as { networks: Network[] }
      setNetworks(d.networks ?? [])
    }
  }, [])

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return
    const socket = new WebSocket(WS_URL)

    socket.onopen = () => {
      setConnected(true)
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
    }

    socket.onclose = () => {
      setConnected(false)
      reconnectTimer.current = setTimeout(connect, 3000)
    }

    socket.onerror = () => {
      socket.close()
    }

    socket.onmessage = (evt) => {
      try {
        const msg: WSMessage = JSON.parse(evt.data)
        dispatch(msg)
      } catch {
        // ignore malformed messages
      }
    }

    ws.current = socket
  }, [dispatch])

  useEffect(() => {
    connect()
    const ping = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: 'ping' }))
      }
    }, 20000)
    return () => {
      clearInterval(ping)
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      ws.current?.close()
    }
  }, [connect])

  const subscribe = useCallback((
    type: WSMessage['type'] | '*',
    handler: WSHandler
  ): (() => void) => {
    if (!handlers.current.has(type)) handlers.current.set(type, new Set())
    handlers.current.get(type)!.add(handler)
    return () => handlers.current.get(type)?.delete(handler)
  }, [])

  const send = useCallback((data: unknown) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data))
    }
  }, [])

  return { connected, logs, networks, subscribe, send }
}

// ─── Focused hook: stream command output ─────────────────────────────
export function useCommandOutput(cmdId: string | null) {
  const [lines, setLines] = useState<string[]>([])
  const { subscribe } = useWebSocket()

  useEffect(() => {
    if (!cmdId) return
    setLines([])
    return subscribe('command_output', (msg) => {
      const d = msg.data as unknown as CommandOutputData
      if (d.cmd_id === cmdId) {
        setLines(prev => [...prev, d.line])
      }
    })
  }, [cmdId, subscribe])

  return lines
}
