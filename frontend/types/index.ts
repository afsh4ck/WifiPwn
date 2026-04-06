// ─── Network / Scanner ───────────────────────────────────────────────
export interface Network {
  bssid: string
  essid: string
  channel: number
  security: string
  cipher: string
  authentication: string
  power: number
  beacons?: number
  ivs?: number
  lan_ip?: string
  id_length?: number
  wps?: boolean
  first_seen?: string
  last_seen?: string
  notes?: string
}

// ─── Handshake ───────────────────────────────────────────────────────
export interface Handshake {
  id: number
  network_id: number
  capture_file: string
  capture_date: string
  cracked: boolean
  password?: string
  wordlist_used?: string
  bssid?: string
  essid?: string
}

// ─── Credentials / Evil Portal ───────────────────────────────────────
export interface Credential {
  id: number
  source: string
  username?: string
  password: string
  capture_date: string
  ip_address?: string
}

// ─── Campaigns ──────────────────────────────────────────────────────
export interface Campaign {
  id: number
  name: string
  description?: string
  created_date: string
  updated_date: string
  status: 'active' | 'completed' | 'archived'
  target_count?: number
}

export interface CampaignTarget {
  id: number
  campaign_id: number
  network_id: number
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  notes?: string
  bssid?: string
  essid?: string
}

// ─── WiFi Interface ─────────────────────────────────────────────────
export interface WifiInterface {
  name: string
  mac?: string
  mode?: string
  supports_monitor?: boolean
}

// ─── Statistics ──────────────────────────────────────────────────────
export interface Stats {
  total_networks: number
  handshakes_captured: number
  passwords_cracked: number
  credentials_captured: number
  active_campaigns: number
  deauth_attacks: number
}

// ─── WebSocket Events ────────────────────────────────────────────────
export type WSMessageType =
  | 'log'
  | 'scan_update'
  | 'command_output'
  | 'handshake_detected'
  | 'credential_captured'
  | 'status_update'
  | 'pong'

export interface WSMessage {
  type: WSMessageType
  timestamp: string
  data: Record<string, unknown>
}

export interface LogData {
  level: 'info' | 'warning' | 'error' | 'success'
  message: string
  source?: string
}

export interface CommandOutputData {
  cmd_id: string
  line: string
}

export interface ScanUpdateData {
  networks: Network[]
}

export interface StatusUpdateData {
  module: string
  status: string
  details?: Record<string, unknown>
}

// ─── API Responses ───────────────────────────────────────────────────
export interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface ScanStatus {
  running: boolean
  interface?: string
  networks_found: number
}

export interface CaptureStatus {
  running: boolean
  interface?: string
  bssid?: string
  channel?: number
  output_file?: string
}

export interface PortalStatus {
  running: boolean
  ssid?: string
  interface?: string
  credentials_count: number
}

export type LogLevel = 'info' | 'warning' | 'error' | 'success'

export interface LogEntry {
  id?: number
  level: LogLevel
  message: string
  timestamp: string
  source?: string
}
