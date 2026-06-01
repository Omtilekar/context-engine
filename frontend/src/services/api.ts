import type {
  DocumentIngestRequest,
  HealthResponse,
  IngestResponse,
  QueryRequest,
  QueryResponse,
  StatusResponse,
} from "../types/api"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"

async function readError(response: Response): Promise<string> {
  const body = await response.text()
  if (!body) {
    return `${response.status} ${response.statusText}`
  }

  try {
    const parsed = JSON.parse(body) as { detail?: string }
    return parsed.detail ?? body
  } catch {
    return body
  }
}

async function requestJson<TResponse>(
  path: string,
  options: RequestInit = {},
): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  })

  if (!response.ok) {
    throw new Error(await readError(response))
  }

  return (await response.json()) as TResponse
}

export function getHealth(): Promise<HealthResponse> {
  return requestJson<HealthResponse>("/health")
}

export function getStatus(): Promise<StatusResponse> {
  return requestJson<StatusResponse>("/status")
}

export function submitQuery(request: QueryRequest): Promise<QueryResponse> {
  return requestJson<QueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify(request),
  })
}

export function ingestDocument(request: DocumentIngestRequest): Promise<IngestResponse> {
  return requestJson<IngestResponse>("/ingest", {
    method: "POST",
    body: JSON.stringify(request),
  })
}
