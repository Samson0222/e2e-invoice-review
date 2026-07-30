import { useState } from 'react'
import { documentTotal, vendorOrMerchantName } from '../lib/document-summary'
import type { Document } from '../lib/types'
import { StatusBadge } from './StatusBadge'
import { Button } from './ui/Button'
import { Card } from './ui/Card'
import { ConfirmDialog } from './ui/ConfirmDialog'

interface DocumentInboxProps {
  documents: Document[]
  loading: boolean
  onOpen: (document: Document) => void
  onDelete: (id: string) => void
}

export function DocumentInbox({ documents, loading, onOpen, onDelete }: DocumentInboxProps) {
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null)

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <div className="mb-6">
        <p className="text-sm text-zinc-500">History</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Reviewed documents</h1>
      </div>

      {loading && <p className="text-sm text-zinc-500">Loading…</p>}

      {!loading && documents.length === 0 && (
        <Card className="p-10 text-center text-sm text-zinc-500">No documents have been reviewed yet.</Card>
      )}

      <ul className="space-y-3">
        {documents.map((document) => {
          const name = vendorOrMerchantName(document) ?? document.original_filename
          const typeLabel =
            document.document_type === 'receipt'
              ? 'Receipt'
              : document.document_type === 'invoice'
                ? 'Invoice'
                : 'Document'
          const total = documentTotal(document)

          return (
            <li key={document.id}>
              <Card className="flex items-center justify-between gap-4 p-4">
                <button
                  type="button"
                  onClick={() => onOpen(document)}
                  className="min-w-0 flex-1 text-left"
                >
                  <p className="truncate text-sm font-medium text-zinc-900">{name}</p>
                  <p className="mt-0.5 truncate text-xs text-zinc-500">
                    <span className="font-medium text-zinc-600">{typeLabel}</span>{' '}
                    {document.original_filename}
                  </p>
                </button>
                <div className="flex shrink-0 items-center gap-4">
                  <div className="text-right">
                    {total && <p className="text-sm font-medium text-zinc-900">{total}</p>}
                    <div className="mt-0.5">
                      <StatusBadge status={document.status} />
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setPendingDeleteId(document.id)}
                    aria-label="Delete this review"
                    title="Delete"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.75"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="h-4 w-4"
                      aria-hidden="true"
                    >
                      <path d="M3 6h18" />
                      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                      <path d="M10 11v6" />
                      <path d="M14 11v6" />
                    </svg>
                  </Button>
                </div>
              </Card>
            </li>
          )
        })}
      </ul>

      <ConfirmDialog
        open={pendingDeleteId !== null}
        title="Delete this review?"
        description="This removes the saved review and its uploaded file so the same document can be demonstrated again."
        confirmLabel="Delete"
        onCancel={() => setPendingDeleteId(null)}
        onConfirm={() => {
          if (pendingDeleteId) onDelete(pendingDeleteId)
          setPendingDeleteId(null)
        }}
      />
    </main>
  )
}
