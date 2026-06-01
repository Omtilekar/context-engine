import { Loader2, Send, SlidersHorizontal } from "lucide-react"
import { FormEvent, useState } from "react"

import type { QueryRequest } from "../types/api"

interface QueryPanelProps {
  isLoading: boolean
  error: string | null
  onSubmit: (request: QueryRequest) => void
}

const sampleQueries = [
  "What is ContextEngine?",
  "Find exact keyword FlashRank",
  "Which entities are linked to ContextEngine?",
  "Compare exact keyword search and semantic search for ContextEngine",
]

export function QueryPanel({ isLoading, error, onSubmit }: QueryPanelProps) {
  const [query, setQuery] = useState(sampleQueries[0])
  const [topK, setTopK] = useState(5)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedQuery = query.trim()
    if (!trimmedQuery) {
      return
    }

    onSubmit({ query: trimmedQuery, top_k: topK })
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2 className="panel-title">Query</h2>
          <p className="panel-subtitle">Route, retrieve, verify, answer.</p>
        </div>
        <SlidersHorizontal className="h-5 w-5 text-slate-500" aria-hidden="true" />
      </div>

      <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
        <label className="block">
          <span className="field-label">Question</span>
          <textarea
            className="field mt-1 min-h-28 resize-y"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Ask a question about the local demo corpus"
          />
        </label>

        <label className="block">
          <span className="field-label">Top K</span>
          <input
            className="field mt-1"
            type="number"
            min={1}
            max={20}
            value={topK}
            onChange={(event) => setTopK(Number(event.target.value))}
          />
        </label>

        <div className="grid grid-cols-1 gap-2">
          {sampleQueries.map((sample) => (
            <button
              className="sample-button"
              key={sample}
              type="button"
              onClick={() => setQuery(sample)}
            >
              {sample}
            </button>
          ))}
        </div>

        {error !== null ? <p className="error-text">{error}</p> : null}

        <button className="primary-button w-full" type="submit" disabled={isLoading}>
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Send className="h-4 w-4" aria-hidden="true" />
          )}
          Run Query
        </button>
      </form>
    </section>
  )
}
