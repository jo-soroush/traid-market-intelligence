"""V1-C13 primary-source news verification: claims versus official evidence in six explicit states.

The core (models, curation, engine, qualification, sources, mods) imports only C02 contracts. The
optional C12 macro adapter lives in ``traid.news.macro_adapter`` and is the only C12 consumer.
"""

from traid.news.engine import FrameOutcome, MacroContext, MacroEvaluator, claim_state, frame_state, verify
from traid.news.models import (
    DEFAULT_POLICY, ENGINE_VERSION, AdmissionRejection, ClaimRecord, CuratedEvent, CuratedFact, CuratedProposition,
    CuratedSpan, CurationRecord, EventIdentity, FileNumberFundLink, FrMetadataRecord, FrPublicInspectionRecord,
    GovInfoHtml, GovInfoModsRetrieval, GovInfoPdf, ManualPassage, ManualPassageVerification, OfficialEvidence,
    PatternId, RecordOrigin, VerificationPolicy, VerificationReport, VerificationResult, VerificationState, make_claim,
)

__all__ = ["DEFAULT_POLICY", "ENGINE_VERSION", "AdmissionRejection", "ClaimRecord", "CuratedEvent", "CuratedFact",
           "CuratedProposition", "CuratedSpan", "CurationRecord", "EventIdentity", "FileNumberFundLink",
           "FrMetadataRecord", "FrPublicInspectionRecord", "FrameOutcome", "GovInfoHtml", "GovInfoModsRetrieval",
           "GovInfoPdf", "MacroContext", "MacroEvaluator", "ManualPassage", "ManualPassageVerification",
           "OfficialEvidence", "PatternId", "RecordOrigin", "VerificationPolicy", "VerificationReport",
           "VerificationResult", "VerificationState", "claim_state", "frame_state", "make_claim", "verify"]
