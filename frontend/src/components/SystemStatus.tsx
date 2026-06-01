import { useQuery } from "@tanstack/react-query"
import { Activity, Server } from "lucide-react"

import { getHealth, getStatus } from "../services/api"

export function SystemStatus() {
  const healthQuery = useQuery({ queryKey: ["health"], queryFn: getHealth })
  const statusQuery = useQuery({ queryKey: ["status"], queryFn: getStatus })
  const status = statusQuery.data

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2 className="panel-title">Backend</h2>
          <p className="panel-subtitle">Health and feature flags.</p>
        </div>
        <Server className="h-5 w-5 text-slate-500" aria-hidden="true" />
      </div>

      <div className="mt-4 flex items-center gap-2">
        <span
          className={`h-2.5 w-2.5 rounded-full ${
            healthQuery.isSuccess ? "bg-emerald-500" : "bg-amber-500"
          }`}
        />
        <p className="text-sm font-semibold text-slate-800">
          {healthQuery.isSuccess ? healthQuery.data.service : "Waiting for backend"}
        </p>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2">
        <StatusTile label="Env" value={status?.environment ?? "-"} />
        <StatusTile label="DB" value={status?.database_configured ? "configured" : "missing"} />
        <StatusTile label="Wiki" value={status?.wiki_enabled ? "on" : "off"} />
        <StatusTile label="Graph" value={status?.graph_enabled ? "on" : "off"} />
      </div>

      {statusQuery.error instanceof Error ? (
        <p className="error-text mt-4">{statusQuery.error.message}</p>
      ) : null}

      <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
        <Activity className="h-3.5 w-3.5" aria-hidden="true" />
        <span>{status?.vector_support ?? "pgvector status pending"}</span>
      </div>
    </section>
  )
}

function StatusTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-slate-200 bg-slate-50 p-2">
      <p className="text-[11px] font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-1 truncate text-sm font-semibold text-slate-900">{value}</p>
    </div>
  )
}
