'use client'

import { useState, useEffect, useCallback } from 'react'
import { Target, Plus, Trash2, FileText, ChevronRight, Play, Loader2, CheckCircle2, XCircle, Download, Eye } from 'lucide-react'
import {
  getCampaigns, createCampaign, deleteCampaign,
  getTargets, addTarget, removeTarget, getNetworks,
  setTargetTechniques, startAudit, getAuditStatus,
  generateReport, listCampaignReports, deleteReport,
  downloadReport, viewReportUrl,
} from '@/lib/api'
import { SecurityBadge } from '@/components/ui/Badge'
import { useWebSocket } from '@/lib/websocket'
import type { Campaign, CampaignTarget, Network, Report } from '@/types'

const TECHNIQUES = [
  { id: 'handshake', label: 'Handshake', desc: 'Captura 4-way handshake' },
  { id: 'deauth',    label: 'Deauth',    desc: 'Ataque de desautenticación' },
  { id: 'wps_scan',  label: 'WPS Scan',  desc: 'Detectar WPS vulnerable' },
]

function StatusPill({ status }: { status?: string }) {
  const map: Record<string, string> = {
    pending:     'bg-muted/10 text-muted',
    in_progress: 'bg-warning/20 text-warning',
    completed:   'bg-success/20 text-success',
    failed:      'bg-danger/20 text-danger',
  }
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded font-semibold uppercase ${map[status ?? 'pending'] ?? map.pending}`}>
      {status ?? 'pending'}
    </span>
  )
}

export default function CampaignsPage() {
  const [campaigns, setCampaigns]   = useState<Campaign[]>([])
  const [selected, setSelected]     = useState<Campaign | null>(null)
  const [targets, setTargets]       = useState<CampaignTarget[]>([])
  const [networks, setNetworks]     = useState<Network[]>([])
  const [newName, setNewName]       = useState('')
  const [newDesc, setNewDesc]       = useState('')
  const [error, setError]           = useState('')
  const [auditing, setAuditing]     = useState(false)
  const [reports, setReports]       = useState<Report[]>([])
  const [generating, setGenerating] = useState(false)

  const { subscribe } = useWebSocket()

  const load = useCallback(async () => {
    const c = await getCampaigns().catch(() => [])
    setCampaigns(c)
  }, [])

  const loadTargets = useCallback(async (id: number) => {
    const t = await getTargets(id).catch(() => [])
    setTargets(t)
  }, [])

  const loadReports = useCallback(async (id: number) => {
    const r = await listCampaignReports(id).catch(() => [])
    setReports(r)
  }, [])

  useEffect(() => {
    load()
    getNetworks().then(setNetworks).catch(console.error)
  }, [load])

  // Listen for audit progress
  useEffect(() => {
    return subscribe('audit_progress', () => {
      if (selected) {
        loadTargets(selected.id)
        getAuditStatus(selected.id).then(s => setAuditing(s.running)).catch(() => null)
      }
    })
  }, [subscribe, selected, loadTargets])

  const handleSelect = (c: Campaign) => {
    setSelected(c); setError('')
    loadTargets(c.id)
    loadReports(c.id)
  }

  const handleCreate = async () => {
    if (!newName) return
    setError('')
    try {
      await createCampaign(newName, newDesc)
      setNewName(''); setNewDesc('')
      await load()
    } catch (e: unknown) { setError((e as Error).message) }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteCampaign(id)
      if (selected?.id === id) { setSelected(null); setTargets([]) }
      await load()
    } catch (e: unknown) { setError((e as Error).message) }
  }

  const handleAddTarget = async (net: Network) => {
    if (!selected) return
    setError('')
    try {
      await addTarget(selected.id, net)
      await loadTargets(selected.id)
    } catch (e: unknown) { setError((e as Error).message) }
  }

  const handleRemoveTarget = async (targetId: number) => {
    if (!selected) return
    await removeTarget(selected.id, targetId).catch(() => null)
    await loadTargets(selected.id)
  }

  const handleToggleTechnique = async (target: CampaignTarget, tech: string) => {
    if (!selected) return
    const current: string[] = (() => {
      try { return JSON.parse(target.techniques || '[]') } catch { return [] }
    })()
    const updated = current.includes(tech) ? current.filter(t => t !== tech) : [...current, tech]
    await setTargetTechniques(selected.id, target.id, updated).catch(() => null)
    await loadTargets(selected.id)
  }

  const handleStartAudit = async () => {
    if (!selected) return
    setError('')
    try {
      await startAudit(selected.id)
      setAuditing(true)
    } catch (e: unknown) { setError((e as Error).message) }
  }

  const handleGenerateReport = async () => {
    if (!selected) return
    setGenerating(true)
    try {
      await generateReport(selected.id)
      await loadReports(selected.id)
    } catch (e: unknown) { setError((e as Error).message) }
    finally { setGenerating(false) }
  }

  const handleDeleteReport = async (reportId: number) => {
    await deleteReport(reportId).catch(() => null)
    if (selected) await loadReports(selected.id)
  }

  const isInTargets = (bssid: string) => targets.some(t => t.bssid === bssid)

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* ── Campaign list ── */}
        <div className="card space-y-4">
          <p className="section-title flex items-center gap-2">
            <Target className="w-3.5 h-3.5" /> Campañas
          </p>

          <div className="space-y-2">
            <input className="input text-xs" placeholder="Nombre de campaña" value={newName}
              onChange={e => setNewName(e.target.value)} />
            <input className="input text-xs" placeholder="Descripción (opcional)" value={newDesc}
              onChange={e => setNewDesc(e.target.value)} />
            <button className="btn-primary w-full text-xs" onClick={handleCreate} disabled={!newName}>
              <Plus className="w-3.5 h-3.5" /> Nueva campaña
            </button>
          </div>

          {error && <p className="text-danger text-xs font-mono">{error}</p>}

          <div className="space-y-1 max-h-[400px] overflow-y-auto">
            {campaigns.length === 0 ? (
              <p className="text-muted text-xs text-center py-4">Sin campañas</p>
            ) : campaigns.map(c => (
              <div key={c.id}
                onClick={() => handleSelect(c)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer text-xs transition-colors ${
                  selected?.id === c.id
                    ? 'bg-accent/10 text-accent border border-accent/20'
                    : 'hover:bg-surface text-muted hover:text-text border border-transparent'
                }`}
              >
                <ChevronRight className="w-3 h-3 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{c.name}</p>
                  <p className="text-muted/60">{c.target_count ?? 0} objetivos</p>
                </div>
                <button onClick={e => { e.stopPropagation(); handleDelete(c.id) }}
                  className="p-0.5 rounded hover:bg-red-500/20 text-muted hover:text-red-400 transition-colors">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* ── Targets + audit ── */}
        <div className="lg:col-span-2 space-y-4">
          {selected ? (
            <>
              {/* Current targets */}
              <div className="card">
                <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
                  <p className="section-title mb-0">Objetivos · {selected.name}</p>
                  <div className="flex gap-2">
                    <button
                      className="btn-success text-xs"
                      onClick={handleStartAudit}
                      disabled={auditing || targets.length === 0}
                    >
                      {auditing
                        ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Auditando...</>
                        : <><Play className="w-3.5 h-3.5" /> Iniciar auditoría</>}
                    </button>
                    <button
                      className="btn-ghost text-xs"
                      onClick={handleGenerateReport}
                      disabled={generating || targets.length === 0}
                    >
                      {generating
                        ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Generando...</>
                        : <><FileText className="w-3.5 h-3.5" /> Generar reporte</>}
                    </button>
                  </div>
                </div>

                {targets.length === 0 ? (
                  <p className="text-muted text-xs text-center py-4">Sin objetivos. Añade redes detectadas.</p>
                ) : (
                  <div className="space-y-2">
                    {targets.map(t => {
                      const techs: string[] = (() => { try { return JSON.parse(t.techniques || '[]') } catch { return [] } })()
                      return (
                        <div key={t.id} className="rounded-lg bg-surface border border-border/30 p-3">
                          <div className="flex items-center gap-3 text-xs font-mono mb-2">
                            <span className="text-accent">{t.bssid ?? '—'}</span>
                            <span className="text-text flex-1">{t.essid || '(hidden)'}</span>
                            <span className="text-muted">CH{t.channel ?? '?'}</span>
                            <SecurityBadge value={t.security ?? ''} />
                            <StatusPill status={t.audit_status} />
                            <button onClick={() => handleRemoveTarget(t.id)}
                              className="p-0.5 rounded hover:bg-red-500/20 text-muted hover:text-red-400 transition-colors">
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                          {/* Technique toggles */}
                          <div className="flex gap-1.5 flex-wrap">
                            {TECHNIQUES.map(tech => (
                              <button key={tech.id}
                                onClick={() => handleToggleTechnique(t, tech.id)}
                                title={tech.desc}
                                className={`text-[10px] px-2 py-0.5 rounded border transition-all ${
                                  techs.includes(tech.id)
                                    ? 'bg-accent/20 border-accent text-accent font-semibold'
                                    : 'border-border/40 text-muted hover:border-accent/40 hover:text-text'
                                }`}
                              >
                                {tech.label}
                              </button>
                            ))}
                          </div>
                          {/* Audit result */}
                          {t.audit_result && (() => {
                            try {
                              const r = JSON.parse(t.audit_result)
                              const findings = r.findings || {}
                              if (Object.keys(findings).length === 0) return null
                              return (
                                <div className="mt-2 text-[10px] font-mono text-muted space-y-0.5">
                                  {Object.entries(findings).map(([k, v]) => (
                                    <div key={k} className="flex gap-2">
                                      <span className="text-accent">{k}:</span>
                                      <span className={String(v).toLowerCase().includes('capturado') ? 'text-success' : ''}>{String(v)}</span>
                                    </div>
                                  ))}
                                </div>
                              )
                            } catch { return null }
                          })()}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>

              {/* Add from scanner */}
              <div className="card">
                <p className="section-title">Añadir desde escáner</p>
                <div className="space-y-1 max-h-[220px] overflow-y-auto">
                  {networks.length === 0 ? (
                    <p className="text-muted text-center py-3 text-xs">Ejecuta el escáner primero</p>
                  ) : networks.map(net => (
                    <button key={net.bssid}
                      onClick={() => handleAddTarget(net)}
                      disabled={isInTargets(net.bssid)}
                      className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-mono border transition-colors ${
                        isInTargets(net.bssid)
                          ? 'border-transparent text-muted/40 cursor-not-allowed'
                          : 'hover:bg-surface border-transparent hover:border-accent/20 text-muted hover:text-text'
                      }`}
                    >
                      <span className="text-accent">{net.bssid}</span>
                      <span className="flex-1 text-left">{net.essid || '(hidden)'}</span>
                      <span className="text-muted">CH{net.channel}</span>
                      <SecurityBadge value={net.security} />
                      {isInTargets(net.bssid)
                        ? <CheckCircle2 className="w-3 h-3 text-success" />
                        : <Plus className="w-3 h-3 text-success" />}
                    </button>
                  ))}
                </div>
              </div>

              {/* Reports */}
              {reports.length > 0 && (
                <div className="card">
                  <p className="section-title flex items-center gap-2">
                    <FileText className="w-3.5 h-3.5" /> Reportes generados
                  </p>
                  <div className="space-y-2">
                    {reports.map(r => (
                      <div key={r.id} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-surface border border-border/30 text-xs">
                        <FileText className="w-3.5 h-3.5 text-accent shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="font-mono text-text truncate">{r.filename}</p>
                          <p className="text-muted">
                            {new Date(r.created_date).toLocaleString('es')} · {(r.size / 1024).toFixed(1)} KB
                          </p>
                        </div>
                        <a href={viewReportUrl(r.id)} target="_blank" rel="noreferrer"
                          className="p-1 rounded hover:bg-accent/10 text-muted hover:text-accent transition-colors" title="Ver reporte">
                          <Eye className="w-3.5 h-3.5" />
                        </a>
                        <a href={downloadReport(r.id)}
                          className="p-1 rounded hover:bg-success/10 text-muted hover:text-success transition-colors" title="Descargar">
                          <Download className="w-3.5 h-3.5" />
                        </a>
                        <button onClick={() => handleDeleteReport(r.id)}
                          className="p-1 rounded hover:bg-red-500/20 text-muted hover:text-red-400 transition-colors" title="Eliminar">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="card flex flex-col items-center justify-center h-64 text-muted text-sm gap-3">
              <Target className="w-10 h-10 opacity-20" />
              <p>Selecciona una campaña para gestionar sus objetivos</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}


export default function CampaignsPage() {
  const [campaigns, setCampaigns]   = useState<Campaign[]>([])
  const [selected, setSelected]     = useState<Campaign | null>(null)
  const [targets, setTargets]       = useState<CampaignTarget[]>([])
  const [networks, setNetworks]     = useState<Network[]>([])
  const [newName, setNewName]       = useState('')
  const [newDesc, setNewDesc]       = useState('')
  const [error, setError]           = useState('')
  const [report, setReport]         = useState('')

  const load = useCallback(async () => {
    const c = await getCampaigns().catch(() => [])
    setCampaigns(c)
  }, [])

  const loadTargets = useCallback(async (id: number) => {
    const t = await getTargets(id).catch(() => [])
    setTargets(t)
  }, [])

  useEffect(() => {
    load()
    getNetworks().then(setNetworks).catch(console.error)
  }, [load])

  const handleSelect = (c: Campaign) => {
    setSelected(c)
    setReport('')
    loadTargets(c.id)
  }

  const handleCreate = async () => {
    if (!newName) return
    setError('')
    try {
      await createCampaign(newName, newDesc)
      setNewName(''); setNewDesc('')
      await load()
    } catch (e: unknown) { setError((e as Error).message) }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteCampaign(id)
      if (selected?.id === id) { setSelected(null); setTargets([]) }
      await load()
    } catch (e: unknown) { setError((e as Error).message) }
  }

  const handleAddTarget = async (net: Network) => {
    if (!selected) return
    try {
      await addTarget(selected.id, 0) // backend looks up by bssid via body
      await loadTargets(selected.id)
    } catch { /* ignore */ }
  }

  const handleRemoveTarget = async (targetId: number) => {
    if (!selected) return
    try {
      await removeTarget(selected.id, targetId)
      await loadTargets(selected.id)
    } catch { /* ignore */ }
  }

  const handleReport = async () => {
    if (!selected) return
    const html = await getCampaignReport(selected.id).catch(() => '')
    setReport(html)
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Campaign list */}
        <div className="card space-y-4">
          <p className="section-title flex items-center gap-2">
            <Target className="w-3.5 h-3.5" /> Campañas
          </p>

          {/* Create */}
          <div className="space-y-2">
            <input className="input text-xs" placeholder="Nombre de campaña" value={newName}
              onChange={e => setNewName(e.target.value)} />
            <input className="input text-xs" placeholder="Descripción (opcional)" value={newDesc}
              onChange={e => setNewDesc(e.target.value)} />
            <button className="btn-primary w-full text-xs" onClick={handleCreate} disabled={!newName}>
              <Plus className="w-3.5 h-3.5" /> Nueva campaña
            </button>
          </div>

          {error && <p className="text-danger text-xs font-mono">{error}</p>}

          {/* List */}
          <div className="space-y-1 max-h-[400px] overflow-y-auto">
            {campaigns.length === 0 ? (
              <p className="text-muted text-xs text-center py-4">Sin campañas</p>
            ) : campaigns.map(c => (
              <div
                key={c.id}
                onClick={() => handleSelect(c)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer text-xs transition-colors ${
                  selected?.id === c.id
                    ? 'bg-accent/10 text-accent border border-accent/20'
                    : 'hover:bg-surface text-muted hover:text-text border border-transparent'
                }`}
              >
                <ChevronRight className="w-3 h-3 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{c.name}</p>
                  <p className="text-muted/60">{c.target_count ?? 0} objetivos</p>
                </div>
                <button
                  onClick={e => { e.stopPropagation(); handleDelete(c.id) }}
                  className="text-muted hover:text-danger transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Targets */}
        <div className="lg:col-span-2 space-y-4">
          {selected ? (
            <>
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <p className="section-title mb-0">Objetivos · {selected.name}</p>
                  <button className="btn-ghost text-xs" onClick={handleReport}>
                    <FileText className="w-3.5 h-3.5" /> Generar reporte
                  </button>
                </div>

                {targets.length === 0 ? (
                  <p className="text-muted text-xs text-center py-4">Sin objetivos. Añade redes detectadas.</p>
                ) : (
                  <div className="space-y-1">
                    {targets.map(t => (
                      <div key={t.id} className="flex items-center gap-3 px-3 py-2 rounded-lg bg-surface border border-border/30 text-xs font-mono">
                        <span className="text-accent">{t.bssid ?? '—'}</span>
                        <span className="text-text flex-1">{t.essid ?? '—'}</span>
                        <span className={`text-[10px] px-2 py-0.5 rounded ${
                          t.status === 'completed' ? 'bg-success/10 text-success' :
                          t.status === 'failed'    ? 'bg-danger/10 text-danger'   :
                          'bg-muted/10 text-muted'
                        }`}>{t.status}</span>
                        <button onClick={() => handleRemoveTarget(t.id)} className="text-muted hover:text-danger">
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Add from scanner */}
              <div className="card">
                <p className="section-title">Añadir desde escáner</p>
                <div className="space-y-1 max-h-[200px] overflow-y-auto">
                  {networks.map(net => (
                    <button
                      key={net.bssid}
                      onClick={() => handleAddTarget(net)}
                      className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-mono hover:bg-surface border border-transparent hover:border-accent/20 text-muted hover:text-text transition-colors"
                    >
                      <span className="text-accent">{net.bssid}</span>
                      <span className="flex-1 text-left">{net.essid || 'hidden'}</span>
                      <SecurityBadge value={net.security} />
                      <Plus className="w-3 h-3 text-success" />
                    </button>
                  ))}
                  {networks.length === 0 && <p className="text-muted text-center py-3">Ejecuta el escáner primero</p>}
                </div>
              </div>
            </>
          ) : (
            <div className="card flex items-center justify-center h-64 text-muted text-sm">
              Selecciona una campaña para gestionar sus objetivos
            </div>
          )}
        </div>
      </div>

      {/* HTML report */}
      {report && (
        <div className="card">
          <p className="section-title">Reporte HTML</p>
          <div
            className="bg-white text-gray-900 rounded-lg p-4 max-h-[500px] overflow-auto text-xs"
            dangerouslySetInnerHTML={{ __html: report }}
          />
        </div>
      )}
    </div>
  )
}
