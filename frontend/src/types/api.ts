export type QueryRoute = "wiki" | "semantic" | "bm25" | "sql" | "graph" | "hybrid"

export type SourceType = "pdf" | "docx" | "web" | "database" | "api" | "spreadsheet" | "text"

export type MetadataValue = string | number | boolean

export interface HealthResponse {
  status: string
  service: string
}

export interface StatusResponse {
  service: string
  environment: string
  database_configured: boolean
  vector_support: string
  wiki_enabled: boolean
  graph_enabled: boolean
  verification_enabled: boolean
  memory_update_enabled: boolean
}

export interface QueryRequest {
  query: string
  top_k: number
  session_id?: string
}

export interface RouteDecision {
  route: QueryRoute
  confidence: number
  reasoning: string
  entities: string[]
}

export interface SourceCitation {
  title: string
  score: number
  source_type: QueryRoute
  snippet: string
  source_id?: string | null
  chunk_id?: string | null
  document_id?: string | null
  retrieval_mode?: string | null
  retrieval_modes: string[]
  metadata: Record<string, MetadataValue>
}

export interface Citation {
  title: string
  retrieval_mode: string
  score: number
}

export interface VerificationResult {
  grounded: boolean
  is_grounded: boolean
  has_conflicts: boolean
  warnings: string[]
  evidence_count: number
  retrieval_modes: string[]
  conflict_notes: string[]
  conflicts: string[]
  confidence: number
}

export interface ConfidenceResult {
  score: number
  label: "low" | "medium" | "high"
  reasons: string[]
  explanation: string
}

export interface GenerationMetadata {
  provider: string
  model: string
  tokens_used: number
  cost_usd: number
  citation_count: number
  source_count: number
  fallback_reason?: string | null
}

export interface QueryResponse {
  answer: string
  route_decision: RouteDecision
  sources: SourceCitation[]
  citations: Citation[]
  verification: VerificationResult
  confidence: ConfidenceResult
  generation_metadata: GenerationMetadata
  query_log_id?: string | null
  retrieval_run_id?: string | null
  tokens_used: number
  cost_usd: number
}

export interface DocumentIngestRequest {
  source_type: SourceType
  title: string
  filename?: string
  content?: string
  url?: string
  metadata: Record<string, string>
}

export interface IngestResponse {
  document_id: string
  status: string
  source_type: SourceType
  chunks_planned: number
  chunk_count: number
  title: string
  filename: string
  metadata: Record<string, string>
  message: string
}
