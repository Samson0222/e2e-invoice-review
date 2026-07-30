export type DocumentType = 'invoice' | 'receipt'
export type DocumentStatus = 'ready' | 'needs_review' | 'approved' | 'rejected' | 'failed'
export type IssueSeverity = 'error' | 'warning'
export type FieldSource = 'document_intelligence' | 'llm_fallback'

export interface ValidationIssue {
  code: string
  field: string | null
  severity: IssueSeverity
  message: string
}

export interface FieldConflict {
  field: string
  document_intelligence_value: string
  llm_value: string
}

export interface GlClassification {
  suggested_account_code: string
  suggested_account_name: string
  rationale: string
  confidence: number
  reviewer_override_code: string | null
}

export interface GlAccount {
  code: string
  name: string
}

export interface Money {
  amount: number | null
  currency_code: string | null
  currency_symbol: string | null
}

export interface InvoiceLineItem {
  description: string | null
  quantity: number | null
  unit_price: Money | null
  amount: Money | null
}

export interface ReceiptLineItem {
  description: string | null
  quantity: number | null
  price: Money | null
  total_price: Money | null
}

export interface InvoiceData {
  vendor_name: string | null
  vendor_tax_id: string | null
  customer_name: string | null
  customer_tax_id: string | null
  invoice_id: string | null
  invoice_date: string | null
  due_date: string | null
  purchase_order: string | null
  subtotal: Money | null
  total_tax: Money | null
  invoice_total: Money | null
  items: InvoiceLineItem[]
}

export interface ReceiptData {
  merchant_name: string | null
  transaction_date: string | null
  subtotal: Money | null
  total_tax: Money | null
  total: Money | null
  items: ReceiptLineItem[]
}

export interface Document {
  id: string
  original_filename: string
  content_type: string
  status: DocumentStatus
  document_type: DocumentType | null
  classification_confidence: number | null
  classification_reasoning: string | null
  data: InvoiceData | ReceiptData | null
  field_sources: Record<string, FieldSource>
  conflicts: FieldConflict[]
  issues: ValidationIssue[]
  gl_classification: GlClassification | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface CorrectionEmailDraft {
  recipient_name: string
  subject: string
  body: string
}

export interface DocumentCorrections {
  vendor_name?: string | null
  vendor_tax_id?: string | null
  customer_name?: string | null
  customer_tax_id?: string | null
  invoice_id?: string | null
  purchase_order?: string | null
  invoice_date?: string | null
  due_date?: string | null
  currency_code?: string | null
  subtotal_amount?: number | null
  total_tax_amount?: number | null
  invoice_total_amount?: number | null
  merchant_name?: string | null
  transaction_date?: string | null
  total_amount?: number | null
}
