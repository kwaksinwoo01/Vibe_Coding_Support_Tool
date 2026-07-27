from renamer_document_classifier.classification import (
    DocumentKind,
    classify_document_text,
)


def test_separated_korean_quote_title_is_detected() -> None:
    result = classify_document_text("견\n\n적\n\n서\n견적유효기간 14일")
    assert result.kind is DocumentKind.QUOTE
    assert result.reason == "quote_title"


def test_transaction_title_is_detected() -> None:
    result = classify_document_text("거 래 명 세 서\n거래일자\n인수자")
    assert result.kind is DocumentKind.TRANSACTION
    assert result.reason == "transaction_title"


def test_quote_support_signals_are_used_without_title() -> None:
    result = classify_document_text(
        "견적번호 2026-001\n견적일자 2026-01-05\n견적금액 일백만원"
    )
    assert result.kind is DocumentKind.QUOTE
    assert result.quote_score >= 50


def test_transaction_support_signals_are_used_without_title() -> None:
    result = classify_document_text("거래일자 2026-01-05\n인수자 홍길동\n미수금 0")
    assert result.kind is DocumentKind.TRANSACTION
    assert result.transaction_score >= 50


def test_common_table_fields_do_not_force_a_classification() -> None:
    result = classify_document_text("품명 수량 단가 공급가액 세액 합계")
    assert result.kind is DocumentKind.UNKNOWN


def test_earliest_title_wins_when_both_titles_exist() -> None:
    result = classify_document_text("거래명세서\n첨부 견적서 참조")
    assert result.kind is DocumentKind.TRANSACTION
    assert result.reason == "earliest_title_transaction"
