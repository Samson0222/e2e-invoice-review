import { useState } from 'react'
import { login } from '../lib/api'
import { Button } from './ui/Button'
import { Card, CardContent, CardHeader } from './ui/Card'

interface LoginGateProps {
  onAuthenticated: () => void
}

export function LoginGate({ onAuthenticated }: LoginGateProps) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function submit() {
    setSubmitting(true)
    setError(null)
    try {
      await login(password)
      onAuthenticated()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not sign in.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm items-center px-6">
      <Card className="w-full">
        <CardHeader className="p-8">
          <p className="text-sm font-medium text-zinc-500">Northstar Facilities B.V.</p>
          <h1 className="pt-2 text-xl font-semibold tracking-tight text-zinc-950">Document review</h1>
          <p className="pt-1 text-sm text-zinc-600">Enter the password to continue.</p>
        </CardHeader>
        <CardContent className="p-8 pt-0">
          <form
            onSubmit={(event) => {
              event.preventDefault()
              void submit()
            }}
          >
            <input
              type="password"
              autoFocus
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Password"
              className="w-full rounded-lg border border-zinc-200 px-3 py-2 text-sm shadow-sm outline-none focus:border-zinc-400"
            />
            {error && (
              <p role="alert" className="mt-3 text-sm text-red-800">
                {error}
              </p>
            )}
            <Button type="submit" disabled={submitting || !password} className="mt-5 w-full">
              {submitting ? 'Signing in…' : 'Sign in'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  )
}
