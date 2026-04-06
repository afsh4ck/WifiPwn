'use client'

import { useState, useEffect, useCallback } from 'react'
import { Target, Plus, Trash2, FileText, ChevronRight } from 'lucide-react'
import {
  getCampaigns, createCampaign, deleteCampaign,
  getTargets, addTarget, removeTarget, getNetworks, getCampaignReport,
} from '@/lib/api'
import { SecurityBadge } from '@/components/ui/Badge'
import type { Campaign, CampaignTarget, Network } from '@/types'

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
