import { AlertTriangle, CheckCircle2, ShieldCheck } from "lucide-react"
import type { ReactNode } from "react"

import type { VerificationResult } from "../types/api"

interface VerificationPanelProps {
  verification: VerificationResult | null
}

export function VerificationPanel({ verification }: VerificationPanelProps) {
  const grounded = verification?.is_grounded ?? false
  const hasConflicts = verification?.has_conflicts ?? false

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2 className="panel-title">Verification</h2>
          <p className="panel-subtitle">Grounding, conflicts, warnings.</p>
        </div>
        <ShieldCheck className="h-5 w-5 text-slate-500" aria-hidden="true" />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <StatePill
          active={grounded}
          icon={<CheckCircle2 className="h-4 w-4" aria-hidden="true" />}
          label="Grounded"
        />
        <StatePill
          active={!hasConflicts}
          icon={<AlertTriangle className="h-4 w-4" aria-hidden="true" />}
          label={hasConflicts ? "Conflicts" : "No conflicts"}
        />
      </div>

      {verification === null ? (
        <p className="mt-4 text-sm text-slate-600">No verification result yet.</p>
      ) : (
        <div className="mt-4 space-y-4">
          <div>
            <p className="field-label">Evidence</p>
            <p className="mt-1 text-sm text-slate-800">
              {verification.evidence_count} sources across{" "}
              {verification.retrieval_modes.length || 0} retrieval modes
            </p>
          </div>

          <ListBlock title="Warnings" items={verification.warnings} emptyLabel="No warnings" />
          <ListBlock title="Conflict notes" items={verification.conflict_notes} emptyLabel="No conflicts" />
        </div>
      )}
    </section>
  )
}

function StatePill({
  active,
  icon,
  label,
}: {
  active: boolean
  icon: ReactNode
  label: string
}) {
  return (
    <div
      className={`flex items-center gap-2 rounded border px-3 py-2 text-sm font-semibold ${
        active
          ? "border-emerald-200 bg-emerald-50 text-emerald-800"
          : "border-rose-200 bg-rose-50 text-rose-800"
      }`}
    >
      {icon}
      {label}
    </div>
  )
}

function ListBlock({
  title,
  items,
  emptyLabel,
}: {
  title: string
  items: string[]
  emptyLabel: string
}) {
  return (
    <div>
      <p className="field-label">{title}</p>
      {items.length === 0 ? (
        <p className="mt-1 text-sm text-slate-600">{emptyLabel}</p>
      ) : (
        <ul className="mt-2 space-y-1">
          {items.map((item) => (
            <li className="rounded border border-slate-200 bg-slate-50 px-2 py-1 text-sm text-slate-700" key={item}>
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
