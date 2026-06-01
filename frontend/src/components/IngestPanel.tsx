import { FilePlus2, Loader2, Upload } from "lucide-react"
import { FormEvent, useState } from "react"

import type { DocumentIngestRequest, IngestResponse } from "../types/api"

interface IngestPanelProps {
  response: IngestResponse | null
  isLoading: boolean
  error: string | null
  onSubmit: (request: DocumentIngestRequest) => void
}

export function IngestPanel({ response, isLoading, error, onSubmit }: IngestPanelProps) {
  const [title, setTitle] = useState("Recruiter Demo Note")
  const [filename, setFilename] = useState("recruiter-demo-note.txt")
  const [content, setContent] = useState(
    "ContextEngine demonstrates hybrid RAG with BM25 keyword search, pgvector semantic search, graph traversal, wiki memory, verification, confidence scoring, and grounded citations.",
  )

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedTitle = title.trim()
    const trimmedContent = content.trim()
    if (!trimmedTitle || !trimmedContent) {
      return
    }

    onSubmit({
      source_type: "text",
      title: trimmedTitle,
      filename: filename.trim() || `${trimmedTitle.toLowerCase().replace(/\s+/g, "-")}.txt`,
      content: trimmedContent,
      metadata: {
        source: "frontend",
      },
    })
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2 className="panel-title">Ingest</h2>
          <p className="panel-subtitle">Persist text into documents and chunks.</p>
        </div>
        <FilePlus2 className="h-5 w-5 text-slate-500" aria-hidden="true" />
      </div>

      <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
        <label className="block">
          <span className="field-label">Title</span>
          <input className="field mt-1" value={title} onChange={(event) => setTitle(event.target.value)} />
        </label>

        <label className="block">
          <span className="field-label">Filename</span>
          <input
            className="field mt-1"
            value={filename}
            onChange={(event) => setFilename(event.target.value)}
          />
        </label>

        <label className="block">
          <span className="field-label">Content</span>
          <textarea
            className="field mt-1 min-h-32 resize-y"
            value={content}
            onChange={(event) => setContent(event.target.value)}
          />
        </label>

        {error !== null ? <p className="error-text">{error}</p> : null}

        <button className="secondary-button w-full" type="submit" disabled={isLoading}>
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Upload className="h-4 w-4" aria-hidden="true" />
          )}
          Ingest Text
        </button>
      </form>

      {response !== null ? (
        <div className="mt-4 rounded border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
          <p className="font-semibold">{response.status}</p>
          <p>
            {response.chunk_count} chunks stored for {response.filename}
          </p>
        </div>
      ) : null}
    </section>
  )
}
