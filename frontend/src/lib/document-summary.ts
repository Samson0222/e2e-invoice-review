import type { Document, InvoiceData, Money, ReceiptData } from './types'

export interface Highlight {
  label: string
  value: string
}

export function formatMoney(money: Money | null): string | null {
  if (!money || money.amount === null) return null
  const currency = money.currency_code ?? money.currency_symbol ?? ''
  return [currency, money.amount.toFixed(2)].filter(Boolean).join(' ')
}

export function vendorOrMerchantName(document: Document): string | null {
  if (!document.data) return null
  return document.document_type === 'receipt'
    ? (document.data as ReceiptData).merchant_name
    : (document.data as InvoiceData).vendor_name
}

export function documentTotal(document: Document): string | null {
  if (!document.data) return null
  const money =
    document.document_type === 'receipt'
      ? (document.data as ReceiptData).total
      : (document.data as InvoiceData).invoice_total
  return formatMoney(money)
}

export function summaryLine(document: Document): string {
  const parts = [
    document.document_type,
    vendorOrMerchantName(document),
    documentTotal(document),
  ].filter((part): part is string => Boolean(part))
  return parts.join(' · ')
}

export function extractionHighlights(document: Document): Highlight[] {
  if (!document.data) return []

  const entries: Array<[string, string | null]> =
    document.document_type === 'receipt'
      ? (() => {
          const data = document.data as ReceiptData
          return [
            ['Merchant', data.merchant_name],
            ['Transaction date', data.transaction_date],
            ['Subtotal', formatMoney(data.subtotal)],
            ['VAT', formatMoney(data.total_tax)],
            ['Total', formatMoney(data.total)],
          ]
        })()
      : (() => {
          const data = document.data as InvoiceData
          return [
            ['Vendor', data.vendor_name],
            ['Invoice ID', data.invoice_id],
            ['Invoice date', data.invoice_date],
            ['Due date', data.due_date],
            ['Vendor VAT', data.vendor_tax_id],
            ['Customer VAT', data.customer_tax_id],
            ['Subtotal', formatMoney(data.subtotal)],
            ['VAT', formatMoney(data.total_tax)],
            ['Total', formatMoney(data.invoice_total)],
          ]
        })()

  return entries
    .filter((entry): entry is [string, string] => Boolean(entry[1]))
    .map(([label, value]) => ({ label, value }))
}
