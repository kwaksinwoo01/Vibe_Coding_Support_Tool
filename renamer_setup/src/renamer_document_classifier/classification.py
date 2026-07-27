from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import re


class DocumentKind(StrEnum):
    QUOTE = "QUOTE"
    TRANSACTION = "TRANSACTION"
    UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class ClassificationResult:
    kind: DocumentKind
    quote_score: int = 0
    transaction_score: int = 0
    quote_title_position: int = -1
    transaction_title_position: int = -1
    matches: list[str] = field(default_factory=list)
    reason: str = ""


QUOTE_TITLES = (
    "견적서",
    "見積書",
    "お見積書",
    "御見積書",
    "quotation",
    "pricequotation",
    "salesquotation",
)

TRANSACTION_TITLES = (
    "거래명세서",
    "거래명세표",
    "거래내역서",
    "取引明細書",
    "transactionstatement",
    "statementoftransaction",
)

QUOTE_SIGNALS: tuple[tuple[str, int], ...] = (
    ("견적유효기간", 35),
    ("아래와같이견적합니다", 35),
    ("견적금액", 25),
    ("견적번호", 20),
    ("견적일자", 20),
    ("유효기간", 10),
    ("writtenestimate", 30),
    ("costestimate", 30),
)

TRANSACTION_SIGNALS: tuple[tuple[str, int], ...] = (
    ("거래일자", 25),
    ("인수자", 25),
    ("영수자", 25),
    ("전잔액", 25),
    ("현잔액", 25),
    ("합계잔액", 25),
    ("미수금", 20),
    ("입금액", 15),
    ("납품일자", 20),
    ("출하일자", 20),
    ("거래처", 15),
    ("거래금액", 20),
    ("공급받는자", 10),
)


_WHITESPACE_RE = re.compile(r"\s+")
_SEPARATOR_RE = re.compile(r"[\u00a0\u2000-\u200f\u2028-\u202f\u205f\u3000]+")


def normalize_text(text: str) -> str:
    """Normalize extracted document text while preserving meaningful letters."""

    normalized = text.casefold()
    normalized = _SEPARATOR_RE.sub("", normalized)
    normalized = _WHITESPACE_RE.sub("", normalized)
    return normalized


def _first_position(text: str, candidates: tuple[str, ...]) -> tuple[int, str | None]:
    best_position = -1
    best_keyword: str | None = None

    for keyword in candidates:
        position = text.find(keyword.casefold())
        if position >= 0 and (best_position < 0 or position < best_position):
            best_position = position
            best_keyword = keyword

    return best_position, best_keyword


def _score_signals(
    text: str,
    signals: tuple[tuple[str, int], ...],
    label: str,
) -> tuple[int, list[str]]:
    score = 0
    matches: list[str] = []

    for keyword, weight in signals:
        if keyword.casefold() in text:
            score += weight
            matches.append(f"{label}:{keyword}+{weight}")

    return score, matches


def classify_document_text(
    text: str,
    *,
    title_scan_characters: int = 2_000,
    minimum_support_score: int = 50,
) -> ClassificationResult:
    normalized = normalize_text(text)
    if not normalized:
        return ClassificationResult(
            kind=DocumentKind.UNKNOWN,
            reason="empty_text",
        )

    title_text = normalized[:title_scan_characters]
    quote_position, quote_keyword = _first_position(title_text, QUOTE_TITLES)
    transaction_position, transaction_keyword = _first_position(
        title_text,
        TRANSACTION_TITLES,
    )

    matches: list[str] = []
    if quote_keyword:
        matches.append(f"quote_title:{quote_keyword}")
    if transaction_keyword:
        matches.append(f"transaction_title:{transaction_keyword}")

    if quote_position >= 0 and transaction_position < 0:
        return ClassificationResult(
            kind=DocumentKind.QUOTE,
            quote_score=100,
            quote_title_position=quote_position,
            transaction_title_position=transaction_position,
            matches=matches,
            reason="quote_title",
        )

    if transaction_position >= 0 and quote_position < 0:
        return ClassificationResult(
            kind=DocumentKind.TRANSACTION,
            transaction_score=100,
            quote_title_position=quote_position,
            transaction_title_position=transaction_position,
            matches=matches,
            reason="transaction_title",
        )

    if quote_position >= 0 and transaction_position >= 0:
        if quote_position <= transaction_position:
            return ClassificationResult(
                kind=DocumentKind.QUOTE,
                quote_score=100,
                transaction_score=100,
                quote_title_position=quote_position,
                transaction_title_position=transaction_position,
                matches=matches,
                reason="earliest_title_quote",
            )

        return ClassificationResult(
            kind=DocumentKind.TRANSACTION,
            quote_score=100,
            transaction_score=100,
            quote_title_position=quote_position,
            transaction_title_position=transaction_position,
            matches=matches,
            reason="earliest_title_transaction",
        )

    quote_score, quote_matches = _score_signals(normalized, QUOTE_SIGNALS, "quote")
    transaction_score, transaction_matches = _score_signals(
        normalized,
        TRANSACTION_SIGNALS,
        "transaction",
    )
    matches.extend(quote_matches)
    matches.extend(transaction_matches)

    if quote_score >= minimum_support_score and quote_score > transaction_score:
        kind = DocumentKind.QUOTE
        reason = "quote_support_score"
    elif (
        transaction_score >= minimum_support_score
        and transaction_score > quote_score
    ):
        kind = DocumentKind.TRANSACTION
        reason = "transaction_support_score"
    else:
        kind = DocumentKind.UNKNOWN
        reason = "insufficient_or_tied_support"

    return ClassificationResult(
        kind=kind,
        quote_score=quote_score,
        transaction_score=transaction_score,
        quote_title_position=quote_position,
        transaction_title_position=transaction_position,
        matches=matches,
        reason=reason,
    )
