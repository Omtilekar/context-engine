import { BookOpenText } from "lucide-react"

import type { SourceCitation } from "../types/api"

interface SourceCardsProps {
  sources: SourceCitation[]
}

export function SourceCards({ sources }: SourceCardsProps) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2 className="panel-title">Sources</h2>
          <p className="panel-subtitle">Retrieved context and provenance.</p>
        </div>
        <BookOpenText className="h-5 w-5 text-slate-500" aria-hidden="true" />
      </div>

      <div className="mt-4 space-y-3">
        {sources.length === 0 ? (
          <p className="rounded border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            No sources returned.
          </p>
        ) : (
          sources.map((source, index) => (
            <article className="rounded border border-slate-200 bg-white p-4" key={`${source.title}-${index}`}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-slate-950">{source.title}</h3>
                  <p className="mt-1 text-xs text-slate-500">
                    {source.retrieval_mode ?? source.source_type} | score {source.score.toFixed(2)}
                  </p>
                </div>
                <span className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-700">
                  #{index + 1}
                </span>
              </div>
              <p className="mt-3 line-clamp-4 text-sm leading-6 text-slate-700">{source.snippet}</p>
              {source.retrieval_modes.length > 0 ? (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {source.retrieval_modes.map((mode) => (
                    <span
                      className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-semibold text-slate-600"
                      key={mode}
                    >
                      {mode}
                    </span>
                  ))}
                </div>
              ) : null}
            </article>
          ))
        )}
      </div>
    </section>
  )
}
