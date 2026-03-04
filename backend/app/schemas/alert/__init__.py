"""
告警相关 Schema
"""
from .alert import AlertRecordCreate, AlertRecordResponse, AlertListResponse
from .diagnosis import DiagnosisResultResponse
from .webhook import WebhookConfigCreate, WebhookConfigUpdate, WebhookConfigResponse

__all__ = [
    'AlertRecordCreate',
    'AlertRecordResponse', 
    'AlertListResponse',
    'DiagnosisResultResponse',
    'WebhookConfigCreate',
    'WebhookConfigUpdate',
    'WebhookConfigResponse'
]
