"""Closed table of verified SEC operative patterns and what each establishes (design §9.1-§9.2).

A pattern matches only the normalized OPERATIVE passage of a manual record, anchored to the
whole passage. Exactly one pattern must match. Wording for NOTICE_OF_FILING, LONGER_PERIOD and
EFFECTIVE_ON_FILING_19B4F6 has been seen only in Federal Register text, so those patterns stay
PATTERN_NOT_FIXTURE_VERIFIED until a human record exists for a real fixture of each.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from traid.news.models import PatternId, RegAction, RegStatus

_ACT = r"(?:Securities Exchange Act of 1934|Exchange Act|Act)"
_FN = r"(?: \d{1,3})?"   # a rendered footnote number after a citation


@dataclass(frozen=True)
class Pattern:
    pattern_id: PatternId
    operative: re.Pattern
    action: RegAction
    family: str                     # RULE_CHANGE_19B2 or SRO_EFFECTIVE: never compared across families
    status: RegStatus | None        # the status label this pattern sets, if any
    anchor: str                     # where the operative passage must sit in the HTML document region
    sequence_member: bool           # an SEC order on the file for LATEST_IDENTITY


PATTERNS = (
    Pattern(PatternId.APPROVAL,
            re.compile(rf"^It is therefore ordered, pursuant to Section 19\(b\)\(2\) of the {_ACT},{_FN} that .+ be, and "
                       r"hereby (?:is|are), approved(?: on an accelerated basis)?\.$"),
            RegAction.APPROVED, "RULE_CHANGE_19B2", RegStatus.APPROVED, "BEFORE_SIGNATURE", True),
    Pattern(PatternId.DISAPPROVAL,
            re.compile(rf"^It is therefore ordered, pursuant to Section 19\(b\)\(2\) of the {_ACT},{_FN} that .+ be, and "
                       r"hereby (?:is|are), disapproved\.$"),
            RegAction.DISAPPROVED, "RULE_CHANGE_19B2", RegStatus.DISAPPROVED, "BEFORE_SIGNATURE", True),
    Pattern(PatternId.PROCEEDINGS,
            re.compile(rf"^The Commission is instituting proceedings pursuant to Section 19\(b\)\(2\)\(B\) of the {_ACT}{_FN} "
                       r"to determine whether the proposed rule changes? (?:should|shall) be approved or disapproved\.$"),
            RegAction.INSTITUTED_PROCEEDINGS, "RULE_CHANGE_19B2", RegStatus.UNDER_PROCEEDINGS, "BODY", True),
    Pattern(PatternId.NOTICE_OF_FILING,
            re.compile(rf"^Pursuant to Section 19\(b\)\(1\) of the {_ACT}.*notice is hereby given that on .+ filed with "
                       r"the Securities and Exchange Commission .*the proposed rule change.*$"),
            RegAction.NOTICE_OF_FILING, "RULE_CHANGE_19B2", RegStatus.FILED, "BODY", False),
    Pattern(PatternId.LONGER_PERIOD,
            re.compile(rf"^Accordingly, the Commission, pursuant to [Ss]ection 19\(b\)\(2\) of the {_ACT},{_FN} designates "
                       r".+ as the date by which the Commission shall either approve or disapprove, or institute proceedings.*$"),
            RegAction.LONGER_PERIOD_DESIGNATED, "RULE_CHANGE_19B2", None, "BEFORE_SIGNATURE", True),
    Pattern(PatternId.EFFECTIVE_ON_FILING_19B4F6,
            re.compile(r"^.*filed .*pursuant to Section 19\(b\)\(3\)\(A\)\(iii\).*Rule 19b-4\(f\)\(6\).*it has become "
                       r"effective pursuant to Section 19\(b\)\(3\)\(A\).*$"),
            RegAction.EFFECTIVE_ON_FILING, "SRO_EFFECTIVE", RegStatus.EFFECTIVE_ON_FILING, "BODY", False),
)
BY_ID = {p.pattern_id: p for p in PATTERNS}
ACTION_FAMILY = {p.action: p.family for p in PATTERNS} | {RegAction.RULE_CHANGE_APPROVED: "RULE_CHANGE_19B2"}


def classify(operative_normalized: str) -> tuple[Pattern, ...]:
    return tuple(p for p in PATTERNS if p.operative.fullmatch(operative_normalized))
