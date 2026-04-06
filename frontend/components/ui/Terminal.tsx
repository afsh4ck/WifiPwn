'use client'

import { useEffect, useRef } from 'react'
import { clsx } from 'clsx'

interface TerminalProps {
  lines: string[]
  title?: string
  className?: string
  height?: string
  loading?: boolean
}

const LEVEL_COLOR: Record<string, string> = {
  error:   'text-red-400',
  warning: 'text-yellow-400',
  success: 'text-green-400',
  info:    'text-cyan-400',
}

function colorLine(line: string): string {
  const lower = line.toLowerCase()
  if (lower.includes('error') || lower.includes('fail')) return 'text-red-400'
  if (lower.includes('warn'))  return 'text-yellow-400'
  if (lower.includes('handshake') || lower.includes('found') || lower.includes('success') || lower.includes('password'))
    return 'text-green-400'
  if (lower.includes('[*]') || lower.includes('info')) return 'text-cyan-400'
  return 'text-gray-300'
}

export function Terminal({ lines, title = 'Terminal', className, height = 'h-72', loading }: TerminalProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  return (
    <div className={clsx('rounded-xl overflow-hidden border border-border/60 shadow-xl', className)}>
      {/* Title bar */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-card border-b border-border/60 select-none">
        <span className="w-3 h-3 rounded-full bg-danger/80" />
        <span className="w-3 h-3 rounded-full bg-warning/80" />
        <span className="w-3 h-3 rounded-full bg-success/80" />
        <span className="ml-3 text-xs text-muted font-mono tracking-wider">{title}</span>
        {loading && (
          <span className="ml-auto flex items-center gap-1.5 text-xs text-accent">
            <span className="w-1.5 h-1.5 rounded-full bg-accent animate-ping" />
            RUNNING
          </span>
        )}
      </div>

      {/* Output area */}
      <div
        className={clsx(
          'font-mono text-xs leading-5 p-4 overflow-y-auto bg-[#0a0e1a] scrollbar-thin',
          height
        )}
      >
        {lines.length === 0 ? (
          <p className="text-muted italic">Esperando output...</p>
        ) : (
          lines.map((line, i) => (
            <div key={i} className={clsx('whitespace-pre-wrap break-all', colorLine(line))}>
              <span className="text-muted/50 select-none mr-2">{String(i + 1).padStart(4, ' ')}</span>
              {line}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
