import { MessageSquareText } from "lucide-react"

import type { QueryResponse } from "../types/api"
import { ConfidenceBadge } from "./ConfidenceBadge"
import { RouteDecisionBadge } from "./RouteDecisionBadge"

interface AnswerDisplayProps {
  response: QueryResponse | null
  isLoading: boolean
}

export function AnswerDisplay({ response, isLoading }: AnswerDisplayProps) {
  return (
    <section className="panel min-h-72">
      <div className="panel-heading">
        <div>
          <h2 className="panel-title">Answer</h2>
          <p className="panel-subtitle">Grounded response with route and confidence.</p>
        </div>
        <MessageSquareText className="h-5 w-5 text-slate-500" aria-hidden="true" />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <RouteDecisionBadge decision={response?.route_decision ?? null} />
        <ConfidenceBadge confidence={response?.confidence ?? null} />
      </div>

      <div className="mt-5 rounded border border-slate-200 bg-slate-50 p-4">
        {isLoading ? (
          <p className="text-sm text-slate-600">Running retrieval pipeline...</p>
        ) : response === null ? (
          <p className="text-sm text-slate-600">No answer yet.</p>
        ) : (
          <p className="whitespace-pre-wrap text-sm leading-6 text-slate-900">{response.answer}</p>
        )}
      </div>

      {response !== null ? (
        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          <Metric label="Sources" value={String(response.sources.length)} />
          <Metric label="Citations" value={String(response.citations.length)} />
          <Metric label="Tokens" value={String(response.tokens_used)} />
          <Metric label="Cost" value={`$${response.cost_usd.toFixed(4)}`} />
        </div>
      ) : null}
    </section>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-slate-200 bg-white p-3">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="mt-1 font-mono text-sm font-semibold text-slate-900">{value}</p>
    </div>
  )
}
