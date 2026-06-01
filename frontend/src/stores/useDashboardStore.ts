import { create } from "zustand"

import type { IngestResponse, QueryResponse } from "../types/api"

interface DashboardState {
  queryResponse: QueryResponse | null
  ingestResponse: IngestResponse | null
  debugPayload: QueryResponse | IngestResponse | null
  setQueryResponse: (response: QueryResponse) => void
  setIngestResponse: (response: IngestResponse) => void
  clearDebugPayload: () => void
}

export const useDashboardStore = create<DashboardState>((set) => ({
  queryResponse: null,
  ingestResponse: null,
  debugPayload: null,
  setQueryResponse: (response) =>
    set({
      queryResponse: response,
      debugPayload: response,
    }),
  setIngestResponse: (response) =>
    set({
      ingestResponse: response,
      debugPayload: response,
    }),
  clearDebugPayload: () => set({ debugPayload: null }),
}))
