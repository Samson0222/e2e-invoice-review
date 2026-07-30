import { useMemo, useState } from 'react'
import {
  correctDocument,
  decideDocument,
  documentFileUrl,
  selectGlAccount,
} from '../lib/api'
import { formatMoney } from '../lib/document-summary'
import type {
  Document,
  DocumentCorrections,
  GlAccount,
  InvoiceData,
  Money,
  ReceiptData,
  ValidationIssue,
} from '../lib/types'
import { CorrectionEmailDialog } from './CorrectionEmailDialog'
import { DocumentPreview } from './DocumentPreview'
import { StatusBadge } from './StatusBadge'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'
import { Card, CardContent, CardHeader } from './ui/Card'

interface FieldConfig {
  key: string
  label: string
  correctionKey: keyof DocumentCorrections
  value: string
  isMoney: boolean
  wide?: boolean
}

interface FieldGroup {
  title: string
  fields: FieldConfig[]
}

function moneyToInput(amount: number | null | undefined): string {
  return amount === null || amount === undefined ? '' : String(amount)
}

function textField(
  key: string,
  label: string,
  correctionKey: keyof DocumentCorrections,
  value: string | null,
  wide?: boolean,
): FieldConfig {
  return { key, label, correctionKey, value: value ?? '', isMoney: false, wide }
}

function moneyField(
  key: string,
  label: string,
  correctionKey: keyof DocumentCorrections,
  value: Money | null | undefined,
): FieldConfig {
  return { key, label, correctionKey, value: moneyToInput(value?.amount), isMoney: true }
}

function invoiceCurrency(data: InvoiceData): string | null {
  return (
    data.invoice_total?.currency_code ??
    data.subtotal?.currency_code ??
    data.total_tax?.currency_code ??
    null
  )
}

function invoiceGroups(data: InvoiceData): FieldGroup[] {
  return [
    {
      title: 'Invoice details',
      fields: [
        textField('invoice_id', 'Invoice number', 'invoice_id', data.invoice_id),
        textField('purchase_order', 'Purchase order', 'purchase_order', data.purchase_order),
        textField('invoice_date', 'Invoice date', 'invoice_date', data.invoice_date),
        textField('due_date', 'Due date', 'due_date', data.due_date),
        textField('currency_code', 'Currency', 'currency_code', invoiceCurrency(data)),
      ],
    },
    {
      title: 'Parties and VAT',
      fields: [
        textField('vendor_name', 'Supplier', 'vendor_name', data.vendor_name, true),
        textField('vendor_tax_id', 'Supplier VAT number', 'vendor_tax_id', data.vendor_tax_id),
        textField('customer_name', 'Customer', 'customer_name', data.customer_name, true),
        textField(
          'customer_tax_id',
          'Customer VAT number',
          'customer_tax_id',
          data.customer_tax_id,
        ),
      ],
    },
    {
      title: 'Amounts',
      fields: [
        moneyField('subtotal', 'Subtotal', 'subtotal_amount', data.subtotal),
        moneyField('total_tax', 'VAT', 'total_tax_amount', data.total_tax),
        moneyField('invoice_total', 'Invoice total', 'invoice_total_amount', data.invoice_total),
      ],
    },
  ]
}

function receiptGroups(data: ReceiptData): FieldGroup[] {
  return [
    {
      title: 'Receipt details',
      fields: [
        textField('merchant_name', 'Merchant', 'merchant_name', data.merchant_name, true),
        textField(
          'transaction_date',
          'Transaction date',
          'transaction_date',
          data.transaction_date,
        ),
        moneyField('subtotal', 'Subtotal', 'subtotal_amount', data.subtotal),
        moneyField('total_tax', 'VAT', 'total_tax_amount', data.total_tax),
        moneyField('total', 'Total', 'total_amount', data.total),
      ],
    },
  ]
}

function pluralize(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? '' : 's'}`
}

function StatusBanner({ issues }: { issues: ValidationIssue[] }) {
  const errorCount = issues.filter((issue) => issue.severity === 'error').length
  const warningCount = issues.filter((issue) => issue.severity === 'warning').length

  if (errorCount === 0 && warningCount === 0) {
    return (
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
        <p className="text-sm font-medium text-emerald-800">All checks passed</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm font-medium text-amber-900">Needs attention</p>
        <div className="flex gap-2">
          {errorCount > 0 && <Badge tone="error">{pluralize(errorCount, 'error')}</Badge>}
          {warningCount > 0 && <Badge tone="warning">{pluralize(warningCount, 'warning')}</Badge>}
        </div>
      </div>
    </div>
  )
}

function AutomaticChecksCard({ document }: { document: Document }) {
  const kind = document.document_type === 'receipt' ? 'receipt' : 'invoice'
  return (
    <Card>
      <CardHeader className="border-b border-zinc-100">
        <p className="text-sm font-medium text-zinc-900">Automatic checks</p>
        <p className="text-xs text-zinc-500">
          Deterministic {kind} rules decide whether this review can be approved.
        </p>
      </CardHeader>
      <CardContent className="space-y-2 pt-6">
        {document.issues.length === 0 ? (
          <p className="text-sm text-zinc-500">No issues found.</p>
        ) : (
          document.issues.map((issue) => (
            <div
              key={issue.code}
              className={`rounded-lg border p-3 text-sm ${
                issue.severity === 'error'
                  ? 'border-red-200 bg-red-50 text-red-800'
                  : 'border-amber-200 bg-amber-50 text-amber-800'
              }`}
            >
              <span className="font-medium">
                {issue.severity === 'error' ? 'Error' : 'Warning'}:
              </span>{' '}
              {issue.message}
            </div>
          ))
        )}
      </CardContent>
    </Card>
  )
}

function LlmCrossCheckCard({ document, fields }: { document: Document; fields: FieldConfig[] }) {
  const fieldByKey = useMemo(() => new Map(fields.map((field) => [field.key, field])), [fields])
  const fallbackKeys = Object.entries(document.field_sources)
    .filter(([, source]) => source === 'llm_fallback')
    .map(([key]) => key)
  const conflicts = document.conflicts
  const rowKeys = Array.from(new Set([...fallbackKeys, ...conflicts.map((c) => c.field)]))

  const summaryParts: string[] = []
  if (fallbackKeys.length > 0) {
    summaryParts.push(`LLM filled ${pluralize(fallbackKeys.length, 'missing field')}`)
  }
  if (conflicts.length > 0) {
    summaryParts.push(
      `${pluralize(conflicts.length, 'conflict')} found between Document Intelligence and the LLM`,
    )
  }
  const summary =
    summaryParts.length > 0
      ? `${summaryParts.join('; ')}.`
      : 'Independent LLM review found no gaps or conflicts.'

  return (
    <Card>
      <CardHeader className="border-b border-zinc-100">
        <p className="text-sm font-medium text-zinc-900">Independent LLM cross-check</p>
        <p className="text-xs text-zinc-500">
          Azure OpenAI reads the original document separately; Document Intelligence stays
          primary.
        </p>
      </CardHeader>
      <CardContent className="space-y-3 pt-6">
        <p className="text-sm text-zinc-700">{summary}</p>
        {rowKeys.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-zinc-200">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-zinc-100 bg-zinc-50 text-xs uppercase tracking-wide text-zinc-500">
                <tr>
                  <th className="px-3 py-2 font-medium">Field</th>
                  <th className="px-3 py-2 font-medium">Document Intelligence</th>
                  <th className="px-3 py-2 font-medium">Azure OpenAI</th>
                </tr>
              </thead>
              <tbody>
                {rowKeys.map((key) => {
                  const conflict = conflicts.find((c) => c.field === key)
                  const isFallback = document.field_sources[key] === 'llm_fallback'
                  return (
                    <tr key={key} className="border-b border-zinc-100 last:border-0">
                      <td className="px-3 py-2 align-top">
                        <span className="flex flex-wrap items-center gap-2">
                          {fieldByKey.get(key)?.label ?? key}
                          {isFallback && <Badge tone="warning">LLM fallback</Badge>}
                        </span>
                      </td>
                      <td className="px-3 py-2 align-top text-zinc-600">
                        {conflict ? conflict.document_intelligence_value : 'Not found'}
                      </td>
                      <td className="px-3 py-2 align-top text-zinc-900">
                        {conflict ? conflict.llm_value : (fieldByKey.get(key)?.value ?? '')}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface LineItemRow {
  key: string
  description: string
  quantity: string
  unitPrice: string
  amount: string
}

function lineItemRows(document: Document): LineItemRow[] {
  if (!document.data) return []
  if (document.document_type === 'receipt') {
    return ((document.data as ReceiptData).items ?? []).map((item, index) => ({
      key: `${index}-${item.description ?? ''}`,
      description: item.description ?? '—',
      quantity: item.quantity !== null ? String(item.quantity) : '—',
      unitPrice: formatMoney(item.price) ?? '—',
      amount: formatMoney(item.total_price) ?? '—',
    }))
  }
  return ((document.data as InvoiceData).items ?? []).map((item, index) => ({
    key: `${index}-${item.description ?? ''}`,
    description: item.description ?? '—',
    quantity: item.quantity !== null ? String(item.quantity) : '—',
    unitPrice: formatMoney(item.unit_price) ?? '—',
    amount: formatMoney(item.amount) ?? '—',
  }))
}

function LineItemsCard({ document }: { document: Document }) {
  const rows = lineItemRows(document)
  if (rows.length === 0) return null

  return (
    <Card>
      <CardHeader className="border-b border-zinc-100">
        <p className="text-sm font-medium text-zinc-900">Line items</p>
        <p className="text-xs text-zinc-500">As extracted by Document Intelligence.</p>
      </CardHeader>
      <CardContent className="pt-6">
        <div className="overflow-x-auto rounded-lg border border-zinc-200">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-zinc-100 bg-zinc-50 text-xs uppercase tracking-wide text-zinc-500">
              <tr>
                <th className="px-3 py-2 font-medium">Description</th>
                <th className="px-3 py-2 font-medium">Qty</th>
                <th className="px-3 py-2 font-medium">Unit price</th>
                <th className="px-3 py-2 font-medium">Amount</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.key} className="border-b border-zinc-100 last:border-0">
                  <td className="px-3 py-2 align-top">{row.description}</td>
                  <td className="px-3 py-2 align-top text-zinc-600">{row.quantity}</td>
                  <td className="px-3 py-2 align-top text-zinc-600">{row.unitPrice}</td>
                  <td className="px-3 py-2 align-top text-zinc-900">{row.amount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}

interface DocumentReviewProps {
  document: Document
  glAccounts: GlAccount[]
  glAccountsError: string | null
  onRetryGlAccounts: () => void
  onUpdated: (document: Document) => void
  onBack: () => void
}

export function DocumentReview({
  document,
  glAccounts,
  glAccountsError,
  onRetryGlAccounts,
  onUpdated,
  onBack,
}: DocumentReviewProps) {
  const groups = useMemo(
    () =>
      document.data
        ? document.document_type === 'receipt'
          ? receiptGroups(document.data as ReceiptData)
          : invoiceGroups(document.data as InvoiceData)
        : [],
    [document],
  )
  const fields = useMemo(() => groups.flatMap((group) => group.fields), [groups])

  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(fields.map((field) => [field.key, field.value])),
  )
  const [saving, setSaving] = useState(false)
  const [deciding, setDeciding] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [emailOpen, setEmailOpen] = useState(false)

  const dirtyKeys = fields.filter((field) => values[field.key] !== field.value).map((f) => f.key)
  const decided = document.status === 'approved' || document.status === 'rejected'
  const errorIssues = document.issues.filter((issue) => issue.severity === 'error')

  async function saveCorrections() {
    setSaving(true)
    setActionError(null)
    try {
      const body: DocumentCorrections = {}
      for (const field of fields) {
        if (values[field.key] === field.value) continue
        const raw = values[field.key].trim()
        if (field.isMoney) {
          ;(body as Record<string, unknown>)[field.correctionKey] = raw === '' ? null : Number(raw)
        } else {
          ;(body as Record<string, unknown>)[field.correctionKey] = raw === '' ? null : raw
        }
      }
      const updated = await correctDocument(document.id, body)
      onUpdated(updated)
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : 'Could not save corrections.')
    } finally {
      setSaving(false)
    }
  }

  async function chooseGlAccount(code: string) {
    setActionError(null)
    try {
      onUpdated(await selectGlAccount(document.id, code))
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : 'Could not update the GL account.')
    }
  }

  async function decide(decision: 'approved' | 'rejected') {
    setDeciding(true)
    setActionError(null)
    try {
      onUpdated(await decideDocument(document.id, decision))
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : 'Could not record the decision.')
    } finally {
      setDeciding(false)
    }
  }

  const selectedGlCode =
    document.gl_classification?.reviewer_override_code ??
    document.gl_classification?.suggested_account_code ??
    ''

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <Button onClick={onBack} variant="ghost" size="sm" className="-ml-3">
            ← Back
          </Button>
          <p className="mt-4 text-sm text-zinc-500">Review</p>
          <h1 className="mt-1 break-all text-2xl font-semibold tracking-tight">
            {document.original_filename}
          </h1>
        </div>
        <StatusBadge status={document.status} />
      </div>

      {document.error_message && (
        <div role="alert" className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          {document.error_message}
        </div>
      )}

      <div className="space-y-6">
        <StatusBanner issues={document.issues} />

        <div className="grid gap-6 lg:grid-cols-2">
          <AutomaticChecksCard document={document} />
          <LlmCrossCheckCard document={document} fields={fields} />
        </div>

        <div className="grid gap-6 lg:grid-cols-[1fr_460px] lg:items-start">
          <div className="lg:sticky lg:top-6 lg:h-[calc(100vh-4.5rem)]">
            <DocumentPreview
              src={documentFileUrl(document.id)}
              filename={document.original_filename}
              contentType={document.content_type}
            />
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader className="flex-row items-center justify-between border-b border-zinc-100">
                <p className="text-sm font-medium text-zinc-900">GL account</p>
                {document.gl_classification && (
                  <Badge>{(document.gl_classification.confidence * 100).toFixed(0)}% confidence</Badge>
                )}
              </CardHeader>
              <CardContent className="space-y-3 pt-6">
                {document.gl_classification ? (
                  <>
                    {glAccounts.length > 0 ? (
                      <select
                        value={selectedGlCode}
                        onChange={(event) => void chooseGlAccount(event.target.value)}
                        disabled={decided}
                        className="w-full rounded-md border border-zinc-200 px-3 py-1.5 text-sm disabled:bg-zinc-50 disabled:text-zinc-500"
                      >
                        {glAccounts.map((account) => (
                          <option key={account.code} value={account.code}>
                            {account.code} · {account.name}
                          </option>
                        ))}
                      </select>
                    ) : glAccountsError ? (
                      <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                        <p>{glAccountsError}</p>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={onRetryGlAccounts}
                          className="mt-2"
                        >
                          Retry
                        </Button>
                      </div>
                    ) : (
                      <p className="text-sm text-zinc-500">Loading GL accounts…</p>
                    )}
                    <p className="text-xs text-zinc-500">
                      Suggested: {document.gl_classification.suggested_account_code} ·{' '}
                      {document.gl_classification.suggested_account_name}.{' '}
                      {document.gl_classification.rationale}
                    </p>
                  </>
                ) : (
                  <p className="text-sm text-zinc-500">No GL suggestion is available.</p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="border-b border-zinc-100">
                <p className="text-sm font-medium text-zinc-900">Review extracted fields</p>
                <p className="text-xs text-zinc-500">
                  Correct anything that Azure read incorrectly, then rerun the checks.
                </p>
              </CardHeader>
              <CardContent className="space-y-6 pt-6">
                {groups.map((group) => (
                  <div key={group.title}>
                    <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                      {group.title}
                    </p>
                    <div className="mt-3 grid gap-4 sm:grid-cols-2">
                      {group.fields.map((field) => (
                        <label
                          key={field.key}
                          className={`block ${field.wide ? 'sm:col-span-2' : ''}`}
                        >
                          <span className="text-xs font-medium text-zinc-600">{field.label}</span>
                          <input
                            type={field.isMoney ? 'number' : 'text'}
                            step={field.isMoney ? '0.01' : undefined}
                            value={values[field.key]}
                            onChange={(event) =>
                              setValues((current) => ({
                                ...current,
                                [field.key]: event.target.value,
                              }))
                            }
                            disabled={decided}
                            className="mt-1 w-full rounded-md border border-zinc-200 px-3 py-1.5 text-sm disabled:bg-zinc-50 disabled:text-zinc-500"
                          />
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
                {!decided && (
                  <Button
                    onClick={saveCorrections}
                    disabled={saving || dirtyKeys.length === 0}
                    className="w-full"
                  >
                    {saving ? 'Saving…' : 'Save and rerun checks'}
                  </Button>
                )}
              </CardContent>
            </Card>

            <LineItemsCard document={document} />
          </div>
        </div>

        {actionError && (
          <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            {actionError}
          </div>
        )}

        {!decided ? (
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => void decide('approved')} disabled={deciding || errorIssues.length > 0}>
              Approve
            </Button>
            <Button onClick={() => void decide('rejected')} variant="outline" disabled={deciding}>
              Reject
            </Button>
            <Button onClick={() => setEmailOpen(true)} variant="ghost">
              Request correction…
            </Button>
          </div>
        ) : (
          <Button onClick={() => setEmailOpen(true)} variant="outline">
            Request correction…
          </Button>
        )}
      </div>

      <CorrectionEmailDialog
        documentId={document.id}
        open={emailOpen}
        onClose={() => setEmailOpen(false)}
      />
    </main>
  )
}
