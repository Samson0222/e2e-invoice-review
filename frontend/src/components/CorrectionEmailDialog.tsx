import { useEffect, useState } from 'react'
import { draftCorrectionEmail } from '../lib/api'
import type { CorrectionEmailDraft } from '../lib/types'
import { Button } from './ui/Button'
import { Dialog } from './ui/Dialog'

interface CorrectionEmailDialogProps {
  documentId: string
  open: boolean
  onClose: () => void
}

export function CorrectionEmailDialog({ documentId, open, onClose }: CorrectionEmailDialogProps) {
  if (!open) return null
  return <CorrectionEmailDialogContent key={documentId} documentId={documentId} onClose={onClose} />
}

function CorrectionEmailDialogContent({
  documentId,
  onClose,
}: {
  documentId: string
  onClose: () => void
}) {
  const [draft, setDraft] = useState<CorrectionEmailDraft | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let cancelled = false
    draftCorrectionEmail(documentId)
      .then((result) => {
        if (!cancelled) setDraft(result)
      })
      .catch((reason: unknown) => {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : 'Could not draft the correction email.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [documentId])

  async function copy() {
    if (!draft) return
    await navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`)
    setCopied(true)
  }

  return (
    <Dialog
      open
      onClose={onClose}
      title="Correction request"
      footer={
        <>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          {draft && <Button onClick={() => void copy()}>{copied ? 'Copied' : 'Copy'}</Button>}
        </>
      }
    >
      {loading && <p className="text-sm text-zinc-500">Drafting a correction request…</p>}
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      {draft && (
        <div className="space-y-3 text-sm">
          <p className="text-zinc-500">To: {draft.recipient_name}</p>
          <p className="font-medium text-zinc-900">{draft.subject}</p>
          <p className="whitespace-pre-wrap leading-6 text-zinc-700">{draft.body}</p>
        </div>
      )}
      <p className="mt-4 text-xs text-zinc-400">
        This draft is never sent automatically -- copy it into your own email client.
      </p>
    </Dialog>
  )
}
