import { Gauge } from "lucide-react"

import type { ConfidenceResult } from "../types/api"

interface ConfidenceBadgeProps {
  confidence: ConfidenceResult | null
}

const labelStyles: Record<ConfidenceResult["label"], string> = {
  high: "border-emerald-200 bg-emerald-50 text-emerald-800",
  medium: "border-amber-200 bg-amber-50 text-amber-900",
  low: "border-rose-200 bg-rose-50 text-rose-800",
}

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  if (confidence === null) {
    return (
      <span className="inline-flex items-center rounded border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-500">
        confidence pending
      </span>
    )
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-xs font-semibold ${labelStyles[confidence.label]}`}
      title={confidence.explanation}
    >
      <Gauge className="h-3.5 w-3.5" aria-hidden="true" />
      {confidence.label}
      <span className="font-mono text-[11px]">{Math.round(confidence.score * 100)}%</span>
    </span>
  )
}
