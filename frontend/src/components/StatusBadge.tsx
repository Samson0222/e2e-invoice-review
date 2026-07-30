import type { DocumentStatus } from '../lib/types'

const labels: Record<DocumentStatus, string> = {
  ready: 'Ready',
  needs_review: 'Needs review',
  approved: 'Approved',
  rejected: 'Rejected',
  failed: 'Failed',
}

const styles: Record<DocumentStatus, string> = {
  ready: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  needs_review: 'bg-amber-50 text-amber-700 border-amber-200',
  approved: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  rejected: 'bg-zinc-100 text-zinc-600 border-zinc-200',
  failed: 'bg-red-50 text-red-700 border-red-200',
}

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}
    >
      {labels[status]}
    </span>
  )
}
