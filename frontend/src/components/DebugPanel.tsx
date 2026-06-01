import { Code2, X } from "lucide-react"

interface DebugPanelProps {
  payload: unknown
  onClear: () => void
}

export function DebugPanel({ payload, onClear }: DebugPanelProps) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2 className="panel-title">Debug</h2>
          <p className="panel-subtitle">Raw API payload.</p>
        </div>
        <Code2 className="h-5 w-5 text-slate-500" aria-hidden="true" />
      </div>

      <details className="mt-4" open={payload !== null}>
        <summary className="cursor-pointer text-sm font-semibold text-slate-700">JSON</summary>
        <div className="mt-3 max-h-96 overflow-auto rounded border border-slate-200 bg-slate-950 p-3 text-xs text-slate-100">
          <pre>{JSON.stringify(payload, null, 2)}</pre>
        </div>
      </details>

      {payload !== null ? (
        <button className="ghost-button mt-3" type="button" onClick={onClear}>
          <X className="h-4 w-4" aria-hidden="true" />
          Clear
        </button>
      ) : null}
    </section>
  )
}
