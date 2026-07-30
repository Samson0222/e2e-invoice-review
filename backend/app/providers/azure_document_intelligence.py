"""Azure Document Intelligence surface used to analyze invoices and receipts."""

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, AnalyzeResult
from azure.core.credentials import AzureKeyCredential


class DocumentIntelligenceService:
    def __init__(self, endpoint: str, key: str) -> None:
        self._client = DocumentIntelligenceClient(
            endpoint=endpoint, credential=AzureKeyCredential(key)
        )

    def analyze_invoice(self, pdf_bytes: bytes) -> AnalyzeResult:
        return self._analyze(model_id="prebuilt-invoice", pdf_bytes=pdf_bytes)

    def analyze_receipt(self, pdf_bytes: bytes) -> AnalyzeResult:
        return self._analyze(model_id="prebuilt-receipt", pdf_bytes=pdf_bytes)

    def _analyze(self, model_id: str, pdf_bytes: bytes) -> AnalyzeResult:
        poller = self._client.begin_analyze_document(
            model_id,
            AnalyzeDocumentRequest(bytes_source=pdf_bytes),
        )
        return poller.result()
