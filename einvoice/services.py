import json
import hashlib
import base64
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
import requests
from django.utils import timezone
from django.conf import settings

from .models import EInvoiceConfig, EInvoiceToken, EInvoiceDocument, EInvoiceLog, TINValidation

logger = logging.getLogger(__name__)

SANDBOX_BASE_URL = "https://preprod-api.myinvois.hasil.gov.my"
PRODUCTION_BASE_URL = "https://api.myinvois.hasil.gov.my"

SANDBOX_IDENTITY_URL = "https://preprod-api.myinvois.hasil.gov.my"
PRODUCTION_IDENTITY_URL = "https://api.myinvois.hasil.gov.my"


class MyInvoisError(Exception):
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class MyInvoisService:
    def __init__(self):
        self.config = EInvoiceConfig.get_config()
        self.base_url = PRODUCTION_BASE_URL if self.config.environment == 'production' else SANDBOX_BASE_URL
        self.identity_url = PRODUCTION_IDENTITY_URL if self.config.environment == 'production' else SANDBOX_IDENTITY_URL

    def _get_headers(self, include_auth: bool = True) -> Dict[str, str]:
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if include_auth:
            token = self._get_valid_token()
            if token:
                headers['Authorization'] = f'Bearer {token}'
        return headers

    def _get_valid_token(self) -> Optional[str]:
        token = EInvoiceToken.objects.filter(expires_at__gt=timezone.now()).order_by('-created_at').first()
        if token:
            return token.access_token
        return None

    def _log_request(self, action: str, document: EInvoiceDocument = None, request_data: dict = None,
                     response_data: dict = None, status_code: int = None, error_message: str = '',
                     is_success: bool = False, user=None):
        EInvoiceLog.objects.create(
            document=document,
            action=action,
            request_data=request_data,
            response_data=response_data,
            status_code=status_code,
            error_message=error_message,
            is_success=is_success,
            created_by=user
        )

    def authenticate(self, user=None) -> Tuple[bool, str]:
        if not self.config.is_active:
            return False, "E-Invoice is not active"

        client_id = self.config.client_id
        client_secret = self.config.client_secret

        if not client_id or not client_secret:
            return False, "Client ID and Client Secret are required"

        url = f"{self.identity_url}/connect/token"

        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'client_credentials',
            'scope': 'InvoicingAPI'
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        try:
            response = requests.post(url, data=data, headers=headers, timeout=30)
            response_data = response.json() if response.content else {}

            self._log_request(
                action='authenticate',
                request_data={'url': url, 'client_id': client_id},
                response_data=response_data,
                status_code=response.status_code,
                is_success=response.status_code == 200,
                error_message=response_data.get('error', '') if response.status_code != 200 else '',
                user=user
            )

            if response.status_code == 200:
                access_token = response_data.get('access_token')
                expires_in = response_data.get('expires_in', 3600)
                expires_at = timezone.now() + timedelta(seconds=expires_in - 60)

                EInvoiceToken.objects.create(
                    access_token=access_token,
                    token_type=response_data.get('token_type', 'Bearer'),
                    expires_at=expires_at
                )

                return True, "Authentication successful"
            else:
                error_msg = response_data.get('error_description', response_data.get('error', 'Authentication failed'))
                return False, error_msg

        except requests.RequestException as e:
            self._log_request(
                action='authenticate',
                request_data={'url': url},
                error_message=str(e),
                is_success=False,
                user=user
            )
            return False, f"Connection error: {str(e)}"

    def ensure_authenticated(self, user=None) -> bool:
        if self._get_valid_token():
            return True
        success, _ = self.authenticate(user)
        return success

    def validate_tin(self, tin: str, id_type: str = 'BRN', id_value: str = '', user=None) -> Tuple[bool, str, Dict]:
        if not self.ensure_authenticated(user):
            return False, "Authentication failed", {}

        url = f"{self.base_url}/api/v1.0/taxpayer/validate/{tin}"

        params = {}
        if id_type:
            params['idType'] = id_type
        if id_value:
            params['idValue'] = id_value

        try:
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=30)
            response_data = response.json() if response.content else {}

            is_valid = response.status_code == 200

            self._log_request(
                action='validate_tin',
                request_data={'tin': tin, 'id_type': id_type, 'id_value': id_value},
                response_data=response_data,
                status_code=response.status_code,
                is_success=is_valid,
                error_message='' if is_valid else response_data.get('error', 'Invalid TIN'),
                user=user
            )

            TINValidation.objects.update_or_create(
                tin=tin,
                defaults={
                    'id_type': id_type,
                    'id_value': id_value,
                    'is_valid': is_valid,
                    'taxpayer_name': response_data.get('name', ''),
                    'validation_response': response_data
                }
            )

            if is_valid:
                return True, response_data.get('name', 'Valid TIN'), response_data
            else:
                return False, response_data.get('error', 'Invalid TIN'), response_data

        except requests.RequestException as e:
            self._log_request(
                action='validate_tin',
                request_data={'tin': tin},
                error_message=str(e),
                is_success=False,
                user=user
            )
            return False, f"Connection error: {str(e)}", {}

    def build_invoice_payload(self, einvoice_doc: EInvoiceDocument) -> Dict[str, Any]:
        invoice = einvoice_doc.invoice
        if not invoice:
            raise MyInvoisError("No invoice linked to e-invoice document")

        config = self.config

        supplier = {
            "TIN": config.taxpayer_tin,
            "BRN": config.clinic_brn,
            "Name": config.clinic_name,
            "Address": {
                "AddressLine1": config.clinic_address_line1,
                "AddressLine2": config.clinic_address_line2 or "",
                "City": config.clinic_city,
                "State": config.clinic_state,
                "PostalZone": config.clinic_postcode,
                "Country": config.clinic_country or "MYS"
            },
            "ContactNumber": config.clinic_phone,
            "Email": config.clinic_email
        }

        buyer_tin = einvoice_doc.buyer_tin or "EI00000000010"
        buyer_name = einvoice_doc.buyer_name or invoice.patient.full_name

        buyer = {
            "TIN": buyer_tin,
            "Name": buyer_name,
            "Address": {
                "AddressLine1": getattr(invoice.patient, 'address', '') or "N/A",
                "City": getattr(invoice.patient, 'city', '') or "N/A",
                "State": getattr(invoice.patient, 'state', '') or "N/A",
                "PostalZone": getattr(invoice.patient, 'postcode', '') or "00000",
                "Country": "MYS"
            },
            "ContactNumber": getattr(invoice.patient, 'phone', '') or "",
            "Email": getattr(invoice.patient, 'email', '') or ""
        }

        invoice_lines = []
        for idx, item in enumerate(invoice.items.all(), start=1):
            line = {
                "ID": str(idx),
                "Description": item.description,
                "Quantity": float(item.quantity),
                "UnitPrice": float(item.unit_price),
                "TaxAmount": float(item.total * (item.tax_rate / 100)) if item.tax_rate else 0,
                "TaxType": "01",
                "TaxRate": float(item.tax_rate) if item.tax_rate else 0,
                "SubTotal": float(item.total),
                "TotalAmount": float(item.total)
            }
            invoice_lines.append(line)

        payload = {
            "ID": einvoice_doc.internal_id,
            "IssueDateTime": timezone.now().isoformat(),
            "InvoiceTypeCode": "01",
            "CurrencyCode": einvoice_doc.currency or "MYR",
            "Supplier": supplier,
            "Buyer": buyer,
            "InvoiceLines": invoice_lines,
            "TaxTotal": float(invoice.tax_amount),
            "SubTotal": float(invoice.subtotal),
            "TotalAmount": float(invoice.total_amount),
            "PaymentMode": "01",
            "PaymentTerms": "Due upon receipt"
        }

        return payload

    def submit_document(self, einvoice_doc: EInvoiceDocument, user=None) -> Tuple[bool, str, Dict]:
        if not self.ensure_authenticated(user):
            return False, "Authentication failed", {}

        if not einvoice_doc.can_resubmit:
            return False, f"Document cannot be submitted in {einvoice_doc.status} status", {}

        try:
            payload = self.build_invoice_payload(einvoice_doc)
            einvoice_doc.payload_json = payload
            einvoice_doc.save()

            documents_payload = {
                "documents": [payload]
            }

            url = f"{self.base_url}/api/v1.0/documentsubmissions"

            response = requests.post(
                url,
                json=documents_payload,
                headers=self._get_headers(),
                timeout=60
            )
            response_data = response.json() if response.content else {}

            self._log_request(
                action='submit',
                document=einvoice_doc,
                request_data={'url': url, 'document_id': einvoice_doc.internal_id},
                response_data=response_data,
                status_code=response.status_code,
                is_success=response.status_code in [200, 202],
                error_message='' if response.status_code in [200, 202] else str(response_data),
                user=user
            )

            if response.status_code in [200, 202]:
                submission_uid = response_data.get('submissionUid', '')
                accepted_docs = response_data.get('acceptedDocuments', [])
                rejected_docs = response_data.get('rejectedDocuments', [])

                einvoice_doc.submission_uid = submission_uid
                einvoice_doc.response_json = response_data

                if accepted_docs:
                    doc_info = accepted_docs[0]
                    einvoice_doc.myinvois_uuid = doc_info.get('uuid', '')
                    einvoice_doc.long_id = doc_info.get('longId', '')
                    einvoice_doc.status = 'submitted'
                    einvoice_doc.submitted_at = timezone.now()
                    einvoice_doc.save()
                    return True, "Document submitted successfully", response_data

                elif rejected_docs:
                    doc_info = rejected_docs[0]
                    einvoice_doc.status = 'invalid'
                    einvoice_doc.validation_errors = doc_info.get('error', {})
                    einvoice_doc.save()
                    error_msg = doc_info.get('error', {}).get('message', 'Document rejected')
                    return False, error_msg, response_data

            einvoice_doc.status = 'invalid'
            einvoice_doc.response_json = response_data
            einvoice_doc.save()
            error_msg = response_data.get('error', {}).get('message', 'Submission failed')
            return False, error_msg, response_data

        except MyInvoisError as e:
            self._log_request(
                action='submit',
                document=einvoice_doc,
                error_message=e.message,
                is_success=False,
                user=user
            )
            return False, e.message, {}

        except requests.RequestException as e:
            self._log_request(
                action='submit',
                document=einvoice_doc,
                error_message=str(e),
                is_success=False,
                user=user
            )
            return False, f"Connection error: {str(e)}", {}

    def get_document_status(self, einvoice_doc: EInvoiceDocument, user=None) -> Tuple[bool, str, Dict]:
        if not self.ensure_authenticated(user):
            return False, "Authentication failed", {}

        if not einvoice_doc.myinvois_uuid:
            return False, "Document has no MyInvois UUID", {}

        url = f"{self.base_url}/api/v1.0/documents/{einvoice_doc.myinvois_uuid}/details"

        try:
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            response_data = response.json() if response.content else {}

            self._log_request(
                action='get_status',
                document=einvoice_doc,
                request_data={'uuid': einvoice_doc.myinvois_uuid},
                response_data=response_data,
                status_code=response.status_code,
                is_success=response.status_code == 200,
                user=user
            )

            if response.status_code == 200:
                status_map = {
                    'Valid': 'valid',
                    'Invalid': 'invalid',
                    'Rejected': 'rejected',
                    'Cancelled': 'cancelled',
                    'Submitted': 'submitted'
                }
                myinvois_status = response_data.get('status', '')
                einvoice_doc.status = status_map.get(myinvois_status, einvoice_doc.status)

                if einvoice_doc.status == 'valid' and not einvoice_doc.validated_at:
                    einvoice_doc.validated_at = timezone.now()

                einvoice_doc.response_json = response_data
                einvoice_doc.save()

                return True, f"Status: {einvoice_doc.get_status_display()}", response_data

            return False, response_data.get('error', {}).get('message', 'Failed to get status'), response_data

        except requests.RequestException as e:
            self._log_request(
                action='get_status',
                document=einvoice_doc,
                error_message=str(e),
                is_success=False,
                user=user
            )
            return False, f"Connection error: {str(e)}", {}

    def cancel_document(self, einvoice_doc: EInvoiceDocument, reason: str, user=None) -> Tuple[bool, str, Dict]:
        if not self.ensure_authenticated(user):
            return False, "Authentication failed", {}

        if not einvoice_doc.can_cancel:
            return False, f"Document cannot be cancelled in {einvoice_doc.status} status", {}

        if not einvoice_doc.myinvois_uuid:
            return False, "Document has no MyInvois UUID", {}

        url = f"{self.base_url}/api/v1.0/documents/state/{einvoice_doc.myinvois_uuid}/state"

        payload = {
            "status": "cancelled",
            "reason": reason
        }

        try:
            response = requests.put(url, json=payload, headers=self._get_headers(), timeout=30)
            response_data = response.json() if response.content else {}

            self._log_request(
                action='cancel',
                document=einvoice_doc,
                request_data={'uuid': einvoice_doc.myinvois_uuid, 'reason': reason},
                response_data=response_data,
                status_code=response.status_code,
                is_success=response.status_code == 200,
                user=user
            )

            if response.status_code == 200:
                einvoice_doc.status = 'cancelled'
                einvoice_doc.cancelled_at = timezone.now()
                einvoice_doc.cancellation_reason = reason
                einvoice_doc.save()
                return True, "Document cancelled successfully", response_data

            error_msg = response_data.get('error', {}).get('message', 'Cancellation failed')
            return False, error_msg, response_data

        except requests.RequestException as e:
            self._log_request(
                action='cancel',
                document=einvoice_doc,
                error_message=str(e),
                is_success=False,
                user=user
            )
            return False, f"Connection error: {str(e)}", {}

    def get_recent_documents(self, page_size: int = 100, page_no: int = 1, user=None) -> Tuple[bool, str, Dict]:
        if not self.ensure_authenticated(user):
            return False, "Authentication failed", {}

        url = f"{self.base_url}/api/v1.0/documents/recent"
        params = {
            'pageSize': page_size,
            'pageNo': page_no
        }

        try:
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=30)
            response_data = response.json() if response.content else {}

            if response.status_code == 200:
                return True, "Documents retrieved", response_data

            return False, response_data.get('error', {}).get('message', 'Failed to get documents'), response_data

        except requests.RequestException as e:
            return False, f"Connection error: {str(e)}", {}

    def search_documents(self, filters: Dict = None, user=None) -> Tuple[bool, str, Dict]:
        if not self.ensure_authenticated(user):
            return False, "Authentication failed", {}

        url = f"{self.base_url}/api/v1.0/documents/search"

        try:
            response = requests.get(url, params=filters or {}, headers=self._get_headers(), timeout=30)
            response_data = response.json() if response.content else {}

            if response.status_code == 200:
                return True, "Search completed", response_data

            return False, response_data.get('error', {}).get('message', 'Search failed'), response_data

        except requests.RequestException as e:
            return False, f"Connection error: {str(e)}", {}


def create_einvoice_from_invoice(invoice, user=None) -> EInvoiceDocument:
    config = EInvoiceConfig.get_config()

    buyer_name = invoice.patient.full_name
    buyer_tin = ""

    if invoice.panel:
        buyer_name = invoice.panel.company_name
        buyer_tin = getattr(invoice.panel, 'tin', '') or ""

    internal_id = f"INV-{invoice.invoice_number}"

    einvoice_doc = EInvoiceDocument.objects.create(
        invoice=invoice,
        document_type='invoice',
        internal_id=internal_id,
        status='pending',
        environment=config.environment,
        buyer_tin=buyer_tin,
        buyer_name=buyer_name,
        total_amount=invoice.total_amount,
        tax_amount=invoice.tax_amount,
        currency='MYR',
        created_by=user
    )

    return einvoice_doc


def create_einvoice_from_panel_claim(panel_claim, user=None) -> EInvoiceDocument:
    config = EInvoiceConfig.get_config()

    buyer_name = panel_claim.panel.company_name
    buyer_tin = getattr(panel_claim.panel, 'tin', '') or ""

    internal_id = f"PC-{panel_claim.claim_number}"

    einvoice_doc = EInvoiceDocument.objects.create(
        invoice=panel_claim.invoice,
        panel_claim=panel_claim,
        document_type='invoice',
        internal_id=internal_id,
        status='pending',
        environment=config.environment,
        buyer_tin=buyer_tin,
        buyer_name=buyer_name,
        total_amount=panel_claim.claim_amount,
        tax_amount=panel_claim.invoice.tax_amount if panel_claim.invoice else 0,
        currency='MYR',
        created_by=user
    )

    return einvoice_doc
