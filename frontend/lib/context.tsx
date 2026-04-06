'use client'

import {
  createContext, useContext, useState, useEffect, useCallback,
  type ReactNode,
} from 'react'
import type { Network } from '@/types'

// ─── Shape ────────────────────────────────────────────────────────────

interface WifiState {
  networks:    Network[]
  target:      Network | null
  setNetworks: (nets: Network[]) => void
  mergeNetworks: (nets: Network[]) => void   // update / keep existing, no wipe
  clearNetworks: () => void
  setTarget:   (net: Network | null) => void
}

const WifiContext = createContext<WifiState | null>(null)

// ─── Persistence helpers ──────────────────────────────────────────────

const LS_NETS   = 'wifipwn:networks'
const LS_TARGET = 'wifipwn:target'

function load<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch { return fallback }
}

function save(key: string, value: unknown) {
  try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* quota */ }
}

// ─── Provider ─────────────────────────────────────────────────────────

export function WifiProvider({ children }: { children: ReactNode }) {
  const [networks, setNetworksRaw] = useState<Network[]>(() => load<Network[]>(LS_NETS, []))
  const [target,   setTargetRaw]   = useState<Network | null>(() => load<Network | null>(LS_TARGET, null))

  const sortByPower = (nets: Network[]) =>
    [...nets].sort((a, b) => (Number(b.power) || -100) - (Number(a.power) || -100))

  const setNetworks = useCallback((nets: Network[]) => {
    const sorted = sortByPower(nets)
    setNetworksRaw(sorted)
    save(LS_NETS, sorted)
  }, [])

  // Merge: update existing entries by BSSID, add new ones, keep stale ones
  const mergeNetworks = useCallback((incoming: Network[]) => {
    setNetworksRaw(prev => {
      const map = new Map(prev.map(n => [n.bssid, n]))
      for (const n of incoming) map.set(n.bssid, n)
      const merged = [...map.values()].sort((a, b) => (Number(b.power) || -100) - (Number(a.power) || -100))
      save(LS_NETS, merged)
      return merged
    })
  }, [])

  const clearNetworks = useCallback(() => {
    setNetworksRaw([])
    save(LS_NETS, [])
  }, [])

  const setTarget = useCallback((net: Network | null) => {
    setTargetRaw(net)
    save(LS_TARGET, net)
  }, [])

  // If target bssid is in the new networks list, keep it updated
  useEffect(() => {
    if (!target) return
    const updated = networks.find(n => n.bssid === target.bssid)
    if (updated && JSON.stringify(updated) !== JSON.stringify(target)) {
      setTargetRaw(updated)
      save(LS_TARGET, updated)
    }
  }, [networks, target])

  return (
    <WifiContext.Provider value={{ networks, target, setNetworks, mergeNetworks, clearNetworks, setTarget }}>
      {children}
    </WifiContext.Provider>
  )
}

// ─── Hook ─────────────────────────────────────────────────────────────

export function useWifi(): WifiState {
  const ctx = useContext(WifiContext)
  if (!ctx) throw new Error('useWifi must be used inside <WifiProvider>')
  return ctx
}
