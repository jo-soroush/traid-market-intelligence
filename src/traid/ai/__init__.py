"""V1-C14 structured AI interpretation behind a provider-neutral boundary.

Interpretation only: no output can create, change or authorize a trade, price, size, risk decision or
execution, and nothing upstream imports this package. ``traid.ai.bedrock`` is the only module that
imports the AWS SDK, and only when a Bedrock provider is used.
"""

from traid.ai.models import (
    AIAnalysisRecord, AIInterpretationRequest, AIResult, AIStatus, Category, Persistence, PersistenceDetail, TaskId,
    TaskOutput, ValidatedInterpretation,
)
from traid.ai.provider import AIProvider, ModelReply, ProviderFailure, ProviderRequest
from traid.ai.records import RecordStore, load_record
from traid.ai.selection import EvidenceInputs, select
from traid.ai.service import AIService, Clock, ProcessSlot, decide, interpret

__all__ = ["AIAnalysisRecord", "AIInterpretationRequest", "AIProvider", "AIResult", "AIService", "AIStatus", "Category",
           "Clock", "EvidenceInputs", "ModelReply", "Persistence", "PersistenceDetail", "ProcessSlot", "ProviderFailure",
           "ProviderRequest", "RecordStore", "TaskId", "TaskOutput", "ValidatedInterpretation", "decide", "interpret",
           "load_record", "select"]
