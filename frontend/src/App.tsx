import { useEffect, useState } from 'react'
import { DocumentInbox } from './components/DocumentInbox'
import { DocumentReview } from './components/DocumentReview'
import { LoginGate } from './components/LoginGate'
import { ProcessingStep } from './components/ProcessingStep'
import { UploadStep } from './components/UploadStep'
import { WelcomePortal } from './components/WelcomePortal'
import { Button } from './components/ui/Button'
import { deleteDocument, getAuthStatus, listDocuments, listGlAccounts, uploadDocument } from './lib/api'
import type { Document, GlAccount } from './lib/types'

type View = 'welcome' | 'upload' | 'processing' | 'review' | 'history'

function AppHeader({
  view,
  onHome,
  onNew,
  onHistory,
}: {
  view: View
  onHome: () => void
  onNew: () => void
  onHistory: () => void
}) {
  return (
    <header className="border-b border-zinc-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
        <button
          type="button"
          onClick={onHome}
          className="rounded-md text-left transition-opacity hover:opacity-70"
          title="Back to home"
        >
          <p className="font-semibold text-zinc-950">Document review</p>
          <p className="text-xs text-zinc-500">Northstar Facilities B.V.</p>
        </button>
        <nav className="flex items-center gap-2" aria-label="Application">
          {view !== 'history' && (
            <Button onClick={onHistory} variant="ghost" size="sm">
              History
            </Button>
          )}
          {view !== 'upload' && (
            <Button onClick={onNew} size="sm">
              New review
            </Button>
          )}
        </nav>
      </div>
    </header>
  )
}

function App() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)
  const [view, setView] = useState<View>('welcome')
  const [file, setFile] = useState<File | null>(null)
  const [selected, setSelected] = useState<Document | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [glAccounts, setGlAccounts] = useState<GlAccount[]>([])
  const [glAccountsError, setGlAccountsError] = useState<string | null>(null)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function loadGlAccounts() {
    try {
      setGlAccounts(await listGlAccounts())
      setGlAccountsError(null)
    } catch (reason) {
      setGlAccountsError(reason instanceof Error ? reason.message : 'Could not load GL accounts.')
    }
  }

  useEffect(() => {
    getAuthStatus()
      .then((status) => setAuthenticated(!status.required || status.authenticated))
      .catch(() => setAuthenticated(false))
  }, [])

  useEffect(() => {
    if (!authenticated) return
    listGlAccounts()
      .then((accounts) => {
        setGlAccounts(accounts)
        setGlAccountsError(null)
      })
      .catch((reason: unknown) => {
        setGlAccountsError(reason instanceof Error ? reason.message : 'Could not load GL accounts.')
      })
  }, [authenticated])

  function startReview() {
    setFile(null)
    setSelected(null)
    setError(null)
    setView('upload')
  }

  function goHome() {
    setError(null)
    setView('welcome')
  }

  async function openHistory() {
    setView('history')
    setHistoryLoading(true)
    try {
      setDocuments(await listDocuments())
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not load review history.')
    } finally {
      setHistoryLoading(false)
    }
  }

  async function processDocument() {
    if (!file) return
    setError(null)
    setView('processing')
    try {
      const processed = await uploadDocument(file)
      setSelected(processed)
      setView('review')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not process the document.')
      setView('upload')
    }
  }

  async function removeDocument(id: string) {
    try {
      await deleteDocument(id)
      setDocuments((current) => current.filter((document) => document.id !== id))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not delete the document.')
    }
  }

  const showHeader = view !== 'welcome'

  if (authenticated === null) {
    return <div className="min-h-screen bg-zinc-50" />
  }

  if (!authenticated) {
    return <LoginGate onAuthenticated={() => setAuthenticated(true)} />
  }

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-950">
      {showHeader && (
        <AppHeader
          view={view}
          onHome={goHome}
          onNew={startReview}
          onHistory={() => void openHistory()}
        />
      )}

      {view === 'welcome' && (
        <WelcomePortal onStart={startReview} onViewHistory={() => void openHistory()} />
      )}

      {view === 'upload' && (
        <UploadStep
          file={file}
          error={error}
          onChoose={(next) => {
            setFile(next)
            setError(null)
          }}
          onProcess={() => void processDocument()}
          onBack={goHome}
        />
      )}

      {view === 'processing' && file && <ProcessingStep filename={file.name} />}

      {view === 'review' && selected && (
        <DocumentReview
          document={selected}
          glAccounts={glAccounts}
          glAccountsError={glAccountsError}
          onRetryGlAccounts={() => void loadGlAccounts()}
          onUpdated={setSelected}
          onBack={() => void openHistory()}
        />
      )}

      {view === 'history' && (
        <DocumentInbox
          documents={documents}
          loading={historyLoading}
          onOpen={(document) => {
            setSelected(document)
            setView('review')
          }}
          onDelete={(id) => void removeDocument(id)}
        />
      )}
    </div>
  )
}

export default App
