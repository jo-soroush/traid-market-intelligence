"""Strict whole-token grammar for model-written statements (final F6, G1-G5).

G1  printable ASCII only (U+0020-U+007E), checked before anything else, so no Unicode sign,
    dash, space or digit look-alike can reach the number checks and no literal can hide one.
G2  tokens separated by single spaces; every token is exactly one of
        LITERAL := ["("] lit [")"] [P]       lit in L, exact equality, parentheses both or neither
        NUMBER  := ["-"] ("0" | [1-9][0-9]*) ["." [0-9]+] ["%"] [P]
        WORD    := [A-Za-z]+ ("-" [A-Za-z]+)* ["'" [A-Za-z]+] [P]
        P       := "," | ";" | ":" | "."
    tried in that order. L holds only code-supplied identifiers, dates, periods, intervals and
    categorical values of the cited items (never claim text, model text or prose, never a bare
    number). Any other token is TOKEN_INVALID, or UNSUPPORTED_CHARACTER when it holds a character
    outside the non-literal set ``A-Za-z0-9.,;:'()-%``.
G3  word rules on WORD tokens: number words, arithmetic words, and comparison words in a
    statement that contains a NUMBER.
G4  NUMBER tokens correspond one to one, in order, with ``numbers[]``; more than one only inside
    one code-declared group.
G5  binding: token == declaration (DECLARATION_MISMATCH); declaration is a code display of the value
    (DISPLAY_MISMATCH); a "%" and every unit-like word of the statement must be explained by the value's
    closed unit phrases: in unit position (after the number and any connector words) only an allowed
    phrase; elsewhere an allowed phrase or a non-unit descriptor of that family (UNIT_MISMATCH);
    the value belongs to a cited item (UNCITED_VALUE).

Acceptance shows only these lexical properties (NUMERIC_CHECK_IS_LEXICAL_NOT_SEMANTIC); rejection is
conservative and fails closed.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

PUNCT = ",;:."
NUMBER = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?%?")
WORD = re.compile(r"[A-Za-z]+(-[A-Za-z]+)*('[A-Za-z]+)?")
BARE_NUMBER = re.compile(r"-?\d+(\.\d+)?%?")
NON_LITERAL_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,;:'()-%")

_TENS = ("twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
NUMBER_WORDS = frozenset((
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
    "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", *_TENS,
    "hundred", "hundreds", "thousand", "thousands", "million", "millions", "billion", "billions", "trillion",
    "trillions", "dozen", "dozens", "half", "halves", "quarter", "quarters", "double", "twice", "triple"))
ARITHMETIC_WORDS = frozenset((
    "plus", "minus", "less", "times", "multiplied", "multiply", "divided", "divide", "equals", "subtract",
    "subtracted", "subtracting", "add", "added", "adding", "sum", "sums", "summed", "difference", "differences",
    "ratio", "ratios", "average", "averages", "averaged", "product", "quotient", "computed", "compute",
    "computes", "calculated", "calculate", "calculates", "derived", "derive", "derives"))
ARITHMETIC_PHRASES = (("equal", "to"),)
COMPARISON_WORDS = frozenset((
    "rose", "rise", "rises", "rising", "fell", "fall", "falls", "falling", "increased", "increase", "increases",
    "increasing", "decreased", "decrease", "decreases", "decreasing", "higher", "lower", "above", "below",
    "exceeds", "exceed", "exceeded", "exceeding", "up", "down", "gained", "gain", "gains", "dropped", "drop",
    "drops", "jumped", "jump", "jumps", "doubled", "halved", "more", "fewer", "than"))

# Units of admitted fields only, as closed per-unit phrases (no implicit conversion: 0.025 is never 2.5%,
# 159044 thousands of payroll jobs is never "159044 payroll jobs"). Families, from the units selection.py
# admits: CPI index; payroll employment (thousands); percent; percentage points; bps; USD; USDC; BTC;
# shares; the C10 fractions (momentum, flow share, funding). Other admitted units (volatility in
# ln(price ratio), the dimensionless imbalance "1") have no writable unit phrase.
UNIT_CLASSES = {
    "percent": "percent",
    "percentage points": "percentage points",
    "bps": "bps",
    "USD": "USD",
    "USDC": "USDC",
    "BTC": "BTC",
    "shares": "shares",
    "index, 1982-84=100": "index",
    "thousands of payroll jobs": "thousands of payroll jobs",
}
UNIT_PHRASES = {
    "percent": (("percent",),),
    "percentage points": (("percentage", "points"), ("percentage", "point")),
    "bps": (("bps",), ("basis", "points"), ("basis", "point")),
    "USD": (("usd",),),
    "USDC": (("usdc",),),
    "BTC": (("btc",),),
    "shares": (("shares",),),
    "index": (("index", "points"), ("index",)),
    "fraction": (("fraction",),),
    "thousands of payroll jobs": (),          # "thousand" is a number word: no unit phrase can be written
}
# Words that may describe the measured subject without asserting a unit; never accepted in unit position.
DESCRIPTORS = {"thousands of payroll jobs": frozenset({"payroll", "payrolls", "employment"})}
GENERIC_DESCRIPTORS = frozenset({"btc", "bitcoin"})       # the T1 asset; the macro task rejects them anyway
# The asset word is a descriptor only in one closed construction: a standalone word opening the statement,
# alone or after a determiner, naming an approved subject noun ("The BTC funding rate"). Anything else ("measured
# in BTC", "the BTC denomination", "BTC-quoted") is a unit assertion, and so is any use in a statement that
# also attributes a unit.
DETERMINERS = frozenset({"the", "a", "an", "this"})
ASSET_SUBJECTS = frozenset({
    "funding", "perpetual", "perpetuals", "perp", "perps", "futures", "derivatives", "spot", "market", "markets",
    "price", "prices", "order", "orderbook", "book", "spread", "depth", "liquidity", "flow", "flows", "aggressor",
    "volume", "volatility", "regime", "whale", "whales", "positioning", "open", "etf", "etfs", "fund", "funds"})
UNIT_ATTRIBUTION = frozenset({
    "denomination", "denominations", "denominated", "denominate", "currency", "currencies", "amount", "amounts",
    "quantity", "quantities", "unit", "units", "measured", "measure", "expressed", "express", "quoted", "quote",
    "reported", "using", "terms", "valued", "priced", "worth"})
# Every unit-like word known to C14. In a statement with a number each must be explained by the rules above.
UNIT_VOCABULARY = frozenset({w for phrases in UNIT_PHRASES.values() for phrase in phrases for w in phrase} | {
    "point", "points", "pct", "percentage", "percents", "bp", "bip", "bips", "basis", "payroll", "payrolls",
    "jobs", "job", "employees", "employee", "employment", "workers", "worker", "people", "persons", "dollar",
    "dollars", "usd", "usdc", "usdt", "cent", "cents", "euro", "euros", "eur", "gbp", "pounds", "yen", "jpy",
    "sats", "satoshi", "satoshis", "bitcoin", "bitcoins", "btc", "eth", "ether", "coin", "coins", "token", "tokens",
    "units", "unit", "share", "shares", "fraction", "fractions", "ratio", "contracts", "contract", "lots", "lot",
    "index", "indices", "denomination", "denominations", "currency", "currencies"})
# Words that, after a number, may link it to a unit ("336.940 measured as the stated value in USD").
CONNECTORS = frozenset({"in", "measured", "expressed", "denominated", "quoted", "reported", "stated", "given",
                        "as", "of", "worth", "terms", "a", "an", "the", "value", "values", "with", "its", "being",
                        "unit", "units", "is", "are", "was", "which", "that"})


def unit_class(unit: str) -> str:
    if unit in UNIT_CLASSES:
        return UNIT_CLASSES[unit]
    return "fraction" if unit.startswith("fraction") else unit


def _parts(word: str) -> set[str]:
    w = word.lower().split("'")[0]
    return {w, *w.split("-")}


def _unit_like(token) -> bool:
    return token.kind == "WORD" and bool(_parts(token.core) & UNIT_VOCABULARY)


def _phrase_at(tokens, start: int, cls: str) -> int:
    """Length of an allowed unit phrase of ``cls`` starting at ``start`` (0 if none)."""
    for phrase in sorted(UNIT_PHRASES.get(cls, ()), key=len, reverse=True):
        if start + len(phrase) <= len(tokens) and all(
                tokens[start + k].kind in ("WORD", "LITERAL") and tokens[start + k].core.lower() == phrase[k]
                for k in range(len(phrase))):
            return len(phrase)
    return 0


def check_units(tokens, positions: list[int], bound: list) -> None:
    """Whole-statement unit safety for a statement that writes numbers."""
    classes = {unit_class(b.unit) for b in bound}
    if len(classes) > 1:
        raise GrammarError("UNIT_MISMATCH", "values with different units in one statement")
    (cls,) = classes
    covered: set[int] = set()
    for j in range(len(tokens)):
        n = _phrase_at(tokens, j, cls)
        covered |= set(range(j, j + n))
    unit_position: set[int] = set()
    for pos in positions:
        j = pos + 1
        # a unit word itself ("unit", "units") may also be a connector: "with its unit being payroll jobs"
        # evidence identifiers and period literals do not separate a number from its unit
        while j < len(tokens) and not _phrase_at(tokens, j, cls) and (
                tokens[j].kind == "WORD" and tokens[j].core.lower() in CONNECTORS
                or tokens[j].kind == "LITERAL" and tokens[j].core.lower() not in UNIT_VOCABULARY):
            j += 1
        if j < len(tokens):
            if _phrase_at(tokens, j, cls):
                continue                      # an allowed unit phrase
            if tokens[j].kind == "LITERAL" and tokens[j].core.lower() in UNIT_VOCABULARY:
                raise GrammarError("UNIT_MISMATCH", f"{tokens[j].core} for {bound[0].unit}")
            k = j
            while k < len(tokens) and _unit_like(tokens[k]):
                unit_position.add(k)
                k += 1
    allowed = DESCRIPTORS.get(cls, frozenset()) | GENERIC_DESCRIPTORS
    for i, t in enumerate(tokens):
        if i in covered or not _unit_like(t):
            continue
        unit_words = _parts(t.core) & UNIT_VOCABULARY
        if i in unit_position or not unit_words <= allowed or (
                unit_words <= GENERIC_DESCRIPTORS and not _asset_descriptor(tokens, i)):
            raise GrammarError("UNIT_MISMATCH", f"{t.core} for {bound[0].unit}")


def _asset_descriptor(tokens, i: int) -> bool:
    if tokens[i].core.lower().split("'")[0] not in GENERIC_DESCRIPTORS:      # a compound: "BTC-denominated"
        return False
    if any(_parts(t.core) & UNIT_ATTRIBUTION for t in tokens if t.kind == "WORD"):
        return False
    # the statement's opening noun phrase only: "As a BTC price ..." or "..., as a BTC price" never qualify
    before = i == 0 or i == 1 and tokens[0].kind == "WORD" and tokens[0].core.lower() in DETERMINERS
    nxt = tokens[i + 1] if i + 1 < len(tokens) else None      # a field name such as "funding" may be a literal
    return before and nxt is not None and nxt.kind in ("WORD", "LITERAL") and nxt.core.lower() in ASSET_SUBJECTS


class GrammarError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}{': ' + detail if detail else ''}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class Token:
    kind: str          # LITERAL, NUMBER or WORD
    core: str          # the literal, the number text, or the word, without trailing punctuation


@dataclass(frozen=True)
class Bound:
    """What G5 needs to know about one eligible value."""
    value_id: str
    displays: tuple[str, ...]
    unit: str
    group: str | None
    owner: str          # the evidence item holding the value


def is_literal_candidate(value: str) -> bool:
    """A literal must be printable ASCII, a single token and never a bare number."""
    return bool(value) and " " not in value and all(" " <= ch <= "~" for ch in value) \
        and BARE_NUMBER.fullmatch(value) is None


def _strip_punct(token: str) -> tuple[str, bool]:
    if len(token) > 1 and token[-1] in PUNCT:
        return token[:-1], True
    return token, False


def classify(token: str, literals: frozenset[str]) -> Token:
    body, _ = _strip_punct(token)
    for candidate in dict.fromkeys((token, body)):
        if candidate in literals:
            return Token("LITERAL", candidate)
        if len(candidate) > 2 and candidate[0] == "(" and candidate[-1] == ")" and candidate[1:-1] in literals:
            return Token("LITERAL", candidate[1:-1])
    if NUMBER.fullmatch(body):
        return Token("NUMBER", body)
    if WORD.fullmatch(body):
        return Token("WORD", body)
    bad = next((ch for ch in token if ch not in NON_LITERAL_CHARS), None)
    if bad is not None:
        raise GrammarError("UNSUPPORTED_CHARACTER", f"U+{ord(bad):04X}")
    raise GrammarError("TOKEN_INVALID", token)


def check_characters(text: str) -> None:
    """G1."""
    for ch in text:
        if not " " <= ch <= "~":
            raise GrammarError("UNSUPPORTED_CHARACTER", f"U+{ord(ch):04X}")


def tokenize(statement: str, literals: frozenset[str]) -> list[Token]:
    """G1 and G2."""
    check_characters(statement)
    parts = statement.split(" ")
    if any(p == "" for p in parts):
        raise GrammarError("TOKEN_INVALID", "spacing")
    return [classify(p, literals) for p in parts]


def check_words(tokens: list[Token]) -> None:
    """G3."""
    words = [t.core.lower() for t in tokens if t.kind == "WORD"]
    has_number = any(t.kind == "NUMBER" for t in tokens)
    for w in words:
        stem = w.split("'")[0]
        parts = stem.split("-")
        if stem in NUMBER_WORDS or any(p in NUMBER_WORDS for p in parts):
            raise GrammarError("NUMBER_WORD", w)
        if stem in ARITHMETIC_WORDS or any(p in ARITHMETIC_WORDS for p in parts):
            raise GrammarError("ARITHMETIC_WORD", w)
    for a, b in zip(words, words[1:]):
        if (a, b) in ARITHMETIC_PHRASES:
            raise GrammarError("ARITHMETIC_WORD", f"{a} {b}")
    if has_number:
        for w in words:
            stem = w.split("'")[0]
            if stem in COMPARISON_WORDS or any(p in COMPARISON_WORDS for p in stem.split("-")):
                raise GrammarError("DERIVED_COMPARISON", w)


def check_numbers(tokens: list[Token], numbers: list[tuple[str, str]], index: dict[str, Bound],
                  citable: frozenset[str]) -> None:
    """G4 and G5. ``numbers`` is the declared (value_id, text) list; ``citable`` the value ids the
    statement's section cites: every value of a cited item, and the linked values of a cited fact."""
    positions = [i for i, t in enumerate(tokens) if t.kind == "NUMBER"]
    if len(positions) != len(numbers):
        raise GrammarError("UNBOUND_NUMBER", f"{len(positions)} written, {len(numbers)} declared")
    bound = [index[value_id] for value_id, _ in numbers]
    if len(bound) > 1:
        groups = {b.group for b in bound}
        if None in groups or len(groups) != 1 or len({b.value_id for b in bound}) != len(bound):
            raise GrammarError("MULTI_VALUE_STATEMENT")
    for pos, (value_id, text), b in zip(positions, numbers, bound):
        written = tokens[pos].core
        if written != text:
            raise GrammarError("DECLARATION_MISMATCH", f"{written} != {text}")
        cls = unit_class(b.unit)
        if written.endswith("%") and cls != "percent":
            raise GrammarError("UNIT_MISMATCH", f"{written} for {b.unit}")
        if text not in b.displays:
            raise GrammarError("DISPLAY_MISMATCH", f"{text} for {value_id}")
        if value_id not in citable:
            raise GrammarError("UNCITED_VALUE", value_id)
    if bound:
        check_units(tokens, positions, bound)


def check_statement(statement: str, literals: frozenset[str], numbers: list[tuple[str, str]],
                    index: dict[str, Bound], citable: frozenset[str]) -> list[Token]:
    tokens = tokenize(statement, literals)
    check_words(tokens)
    check_numbers(tokens, numbers, index, citable)
    return tokens
