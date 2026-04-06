'use client'

import { useState, useEffect, useCallback } from 'react'
import { FileText, Download, Eye, Trash2, RefreshCw, BarChart3 } from 'lucide-react'
import { listReports, deleteReport, downloadReport, viewReportUrl } from '@/lib/api'
import type { Report } from '@/types'

export default function ReportsPage() {
  const [reports, setReports]   = useState<Report[]>([])
  const [loading, setLoading]   = useState(true)
  const [preview, setPreview]   = useState<Report | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    const r = await listReports().catch(() => [])
    setReports(r)
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const handleDelete = async (id: number) => {
    await deleteReport(id).catch(() => null)
    await load()
    if (preview?.id === id) setPreview(null)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-accent" /> Reportes de Auditoría
          </h2>
          <p className="text-xs text-muted mt-0.5">{reports.length} reporte{reports.length !== 1 ? 's' : ''} generado{reports.length !== 1 ? 's' : ''}</p>
        </div>
        <button className="btn-ghost text-xs" onClick={load} disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Actualizar
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Report list */}
        <div className="card space-y-2">
          <p className="section-title flex items-center gap-2">
            <FileText className="w-3.5 h-3.5" /> Reportes
          </p>

          {loading ? (
            <div className="flex items-center justify-center py-10 text-muted">
              <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Cargando...
            </div>
          ) : reports.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-muted gap-2">
              <FileText className="w-8 h-8 opacity-20" />
              <p className="text-sm">Sin reportes generados</p>
              <p className="text-xs opacity-60">Ve a Campañas → Generar reporte</p>
            </div>
          ) : (
            <div className="space-y-1 max-h-[600px] overflow-y-auto">
              {reports.map(r => (
                <div
                  key={r.id}
                  onClick={() => setPreview(r)}
                  className={`flex items-start gap-2 px-3 py-2.5 rounded-lg cursor-pointer text-xs border transition-colors ${
                    preview?.id === r.id
                      ? 'bg-accent/10 border-accent/30 text-accent'
                      : 'hover:bg-surface border-transparent text-muted hover:text-text'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5 shrink-0 mt-0.5 text-accent" />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-text truncate">{r.campaign_name ?? '—'}</p>
                    <p className="font-mono opacity-60 truncate text-[10px]">{r.filename}</p>
                    <p className="opacity-50 text-[10px]">
                      {new Date(r.created_date).toLocaleString('es')} · {(r.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Preview / detail */}
        <div className="lg:col-span-2">
          {preview ? (
            <div className="card space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="section-title mb-0">{preview.campaign_name ?? preview.filename}</p>
                  <p className="text-xs text-muted font-mono mt-0.5">{preview.filename}</p>
                </div>
                <div className="flex gap-2">
                  <a
                    href={viewReportUrl(preview.id)}
                    target="_blank"
                    rel="noreferrer"
                    className="btn-ghost text-xs"
                  >
                    <Eye className="w-3.5 h-3.5" /> Ver reporte
                  </a>
                  <a
                    href={downloadReport(preview.id)}
                    className="btn-primary text-xs"
                  >
                    <Download className="w-3.5 h-3.5" /> Descargar HTML
                  </a>
                  <button
                    onClick={() => handleDelete(preview.id)}
                    className="btn-danger text-xs"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="bg-surface rounded-lg p-3 text-center border border-border/30">
                  <p className="text-accent font-mono text-lg font-bold">{preview.id}</p>
                  <p className="text-muted text-xs">ID</p>
                </div>
                <div className="bg-surface rounded-lg p-3 text-center border border-border/30">
                  <p className="text-accent font-mono text-lg font-bold">{(preview.size / 1024).toFixed(1)}</p>
                  <p className="text-muted text-xs">KB</p>
                </div>
                <div className="bg-surface rounded-lg p-3 text-center border border-border/30">
                  <p className="text-accent font-mono text-sm font-bold">
                    {new Date(preview.created_date).toLocaleDateString('es')}
                  </p>
                  <p className="text-muted text-xs">Fecha</p>
                </div>
              </div>

              {/* Inline preview iframe */}
              <div className="rounded-lg border border-border/40 overflow-hidden" style={{ height: '480px' }}>
                <iframe
                  src={viewReportUrl(preview.id)}
                  className="w-full h-full"
                  title={preview.filename}
                  sandbox="allow-same-origin"
                />
              </div>
            </div>
          ) : (
            <div className="card flex flex-col items-center justify-center h-64 text-muted gap-3">
              <FileText className="w-10 h-10 opacity-20" />
              <p className="text-sm">Selecciona un reporte para previsualizarlo</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
