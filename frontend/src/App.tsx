import { useMutation } from "@tanstack/react-query"
import { BrainCircuit } from "lucide-react"

import { AnswerDisplay } from "./components/AnswerDisplay"
import { DebugPanel } from "./components/DebugPanel"
import { IngestPanel } from "./components/IngestPanel"
import { QueryPanel } from "./components/QueryPanel"
import { SourceCards } from "./components/SourceCards"
import { SystemStatus } from "./components/SystemStatus"
import { VerificationPanel } from "./components/VerificationPanel"
import { ingestDocument, submitQuery } from "./services/api"
import { useDashboardStore } from "./stores/useDashboardStore"
import type { DocumentIngestRequest, QueryRequest } from "./types/api"

export function App() {
  const {
    queryResponse,
    ingestResponse,
    debugPayload,
    setQueryResponse,
    setIngestResponse,
    clearDebugPayload,
  } = useDashboardStore()

  const queryMutation = useMutation({
    mutationFn: (request: QueryRequest) => submitQuery(request),
    onSuccess: setQueryResponse,
  })

  const ingestMutation = useMutation({
    mutationFn: (request: DocumentIngestRequest) => ingestDocument(request),
    onSuccess: setIngestResponse,
  })

  const queryError = queryMutation.error instanceof Error ? queryMutation.error.message : null
  const ingestError = ingestMutation.error instanceof Error ? ingestMutation.error.message : null

  return (
    <main className="min-h-screen bg-slate-100 text-slate-950">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1440px] flex-col gap-4 px-4 py-5 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded border border-slate-200 bg-slate-950 text-white">
              <BrainCircuit className="h-6 w-6" aria-hidden="true" />
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-normal text-slate-950">ContextEngine</h1>
              <p className="text-sm text-slate-600">Hybrid RAG dashboard</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 text-xs font-semibold text-slate-600">
            <span className="rounded border border-slate-200 bg-slate-50 px-2.5 py-1">wiki</span>
            <span className="rounded border border-slate-200 bg-slate-50 px-2.5 py-1">semantic</span>
            <span className="rounded border border-slate-200 bg-slate-50 px-2.5 py-1">BM25</span>
            <span className="rounded border border-slate-200 bg-slate-50 px-2.5 py-1">SQL</span>
            <span className="rounded border border-slate-200 bg-slate-50 px-2.5 py-1">graph</span>
            <span className="rounded border border-slate-200 bg-slate-50 px-2.5 py-1">hybrid</span>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-[1440px] gap-4 px-4 py-4 sm:px-6 lg:grid-cols-[360px_minmax(0,1fr)_360px]">
        <div className="space-y-4">
          <QueryPanel
            error={queryError}
            isLoading={queryMutation.isPending}
            onSubmit={(request) => queryMutation.mutate(request)}
          />
          <IngestPanel
            error={ingestError}
            isLoading={ingestMutation.isPending}
            onSubmit={(request) => ingestMutation.mutate(request)}
            response={ingestResponse}
          />
        </div>

        <div className="space-y-4">
          <AnswerDisplay isLoading={queryMutation.isPending} response={queryResponse} />
          <SourceCards sources={queryResponse?.sources ?? []} />
        </div>

        <div className="space-y-4">
          <SystemStatus />
          <VerificationPanel verification={queryResponse?.verification ?? null} />
          <DebugPanel payload={debugPayload} onClear={clearDebugPayload} />
        </div>
      </div>
    </main>
  )
}
