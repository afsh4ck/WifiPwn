import type {
  Network,
  Handshake,
  Credential,
  Campaign,
  CampaignTarget,
  WifiInterface,
  Stats,
  LogEntry,
  ScanStatus,
  CaptureStatus,
  PortalStatus,
} from '@/types'

const BASE = '/api'

async function req<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(BASE + url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || err.error || `HTTP ${res.status}`)
  }
  return res.json()
}

const get  = <T>(url: string) => req<T>(url)
const post = <T>(url: string, body?: unknown) =>
  req<T>(url, { method: 'POST', body: body ? JSON.stringify(body) : undefined })
const del  = <T>(url: string) => req<T>(url, { method: 'DELETE' })

// ─── Health ──────────────────────────────────────────────────────────
export const health = () => get<{ status: string; version: string; root: boolean }>('/health')

// ─── Dashboard ───────────────────────────────────────────────────────
export const getStats = () => get<Stats>('/dashboard/stats')
export const getLogs  = (limit = 100) => get<LogEntry[]>(`/dashboard/logs?limit=${limit}`)
export const clearData = (table: string) => del(`/dashboard/data/${table}`)
export const clearAll  = () => del('/dashboard/data')
export const exportData = () => fetch(BASE + '/dashboard/export').then(r => r.blob())

// ─── Interfaces ──────────────────────────────────────────────────────
export const getInterfaces    = ()           => get<WifiInterface[]>('/interfaces')
export const getInterfaceInfo = (name: string) => get<WifiInterface>(`/interfaces/${name}`)
export const enableMonitor    = (iface: string) => post('/interfaces/monitor/enable', { interface: iface })
export const disableMonitor   = (iface: string) => post('/interfaces/monitor/disable', { interface: iface })
export const killAirmon       = ()           => post('/interfaces/kill-processes')
export const resetInterface   = (iface: string) => post('/interfaces/reset', { interface: iface })
export const changeMac        = (iface: string, mac?: string) =>
  post('/interfaces/mac/change', { interface: iface, mac })

// ─── Scanner ─────────────────────────────────────────────────────────
export const getNetworks  = () => get<Network[]>('/scanner/networks')
export const startScan    = (iface: string, channel?: number) =>
  post('/scanner/start', { interface: iface, channel })
export const stopScan     = () => post('/scanner/stop')
export const getScanStatus = () => get<ScanStatus>('/scanner/status')

// ─── Handshake ───────────────────────────────────────────────────────
export const startCapture  = (bssid: string, channel: number, iface: string, output?: string) =>
  post('/handshake/start', { bssid, channel, interface: iface, output_file: output })
export const stopCapture   = () => post('/handshake/stop')
export const sendDeauth    = (bssid: string, iface: string, client?: string, count?: number) =>
  post('/handshake/deauth', { bssid, interface: iface, client, count })
export const checkHandshake = (file: string, bssid: string) =>
  post('/handshake/check', { file, bssid })
export const getHandshakes  = () => get<Handshake[]>('/handshake/list')
export const getCaptureStatus = () => get<CaptureStatus>('/handshake/status')

// ─── Cracking ────────────────────────────────────────────────────────
export const startCrack  = (capture: string, wordlist: string, bssid?: string) =>
  post('/cracking/start', { capture_file: capture, wordlist, bssid })
export const stopCrack   = (cmdId: string) => post(`/cracking/stop/${cmdId}`)
export const getCrackOutput = (cmdId: string) =>
  get<{ lines: string[] }>(`/cracking/output/${cmdId}`)

// ─── Deauth ──────────────────────────────────────────────────────────
export const sendDeauthAttack = (
  bssid: string, iface: string, client?: string, packets?: number, continuous?: boolean
) => post('/deauth/send', { bssid, interface: iface, client, packets, continuous })
export const stopDeauth    = () => post('/deauth/stop')
export const getDeauthHistory = () => get<Record<string, unknown>[]>('/deauth/history')

// ─── Evil Portal ─────────────────────────────────────────────────────
export const startPortal  = (ssid: string, iface: string, passphrase?: string, channel?: number) =>
  post('/evil-portal/start', { ssid, interface: iface, passphrase, channel })
export const stopPortal   = () => post('/evil-portal/stop')
export const getPortalStatus = () => get<PortalStatus>('/evil-portal/status')
export const getPortalCredentials = () => get<Credential[]>('/evil-portal/credentials')

// ─── Campaigns ───────────────────────────────────────────────────────
export const getCampaigns   = () => get<Campaign[]>('/campaigns')
export const createCampaign = (name: string, description?: string) =>
  post<Campaign>('/campaigns', { name, description })
export const getCampaign    = (id: number) => get<Campaign>(`/campaigns/${id}`)
export const deleteCampaign = (id: number) => del(`/campaigns/${id}`)
export const getTargets     = (id: number) => get<CampaignTarget[]>(`/campaigns/${id}/targets`)
export const addTarget      = (id: number, networkId: number) =>
  post(`/campaigns/${id}/targets`, { network_id: networkId })
export const removeTarget   = (id: number, targetId: number) =>
  del(`/campaigns/${id}/targets/${targetId}`)
export const getCampaignReport = (id: number) =>
  fetch(BASE + `/campaigns/${id}/report`).then(r => r.text())
