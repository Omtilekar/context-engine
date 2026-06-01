import { Database, GitBranch, Layers3, Library, Search, Sigma } from "lucide-react"

import type { QueryRoute, RouteDecision } from "../types/api"

interface RouteDecisionBadgeProps {
  decision: RouteDecision | null
}

const routeStyles: Record<QueryRoute, string> = {
  wiki: "border-sky-200 bg-sky-50 text-sky-800",
  semantic: "border-emerald-200 bg-emerald-50 text-emerald-800",
  bm25: "border-amber-200 bg-amber-50 text-amber-900",
  sql: "border-violet-200 bg-violet-50 text-violet-800",
  graph: "border-rose-200 bg-rose-50 text-rose-800",
  hybrid: "border-slate-300 bg-slate-100 text-slate-900",
}

const routeIcons: Record<QueryRoute, typeof Library> = {
  wiki: Library,
  semantic: Search,
  bm25: Sigma,
  sql: Database,
  graph: GitBranch,
  hybrid: Layers3,
}

export function RouteDecisionBadge({ decision }: RouteDecisionBadgeProps) {
  if (decision === null) {
    return (
      <span className="inline-flex items-center rounded border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-500">
        route pending
      </span>
    )
  }

  const Icon = routeIcons[decision.route]

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-xs font-semibold ${routeStyles[decision.route]}`}
      title={decision.reasoning}
    >
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {decision.route}
      <span className="font-mono text-[11px]">{Math.round(decision.confidence * 100)}%</span>
    </span>
  )
}
