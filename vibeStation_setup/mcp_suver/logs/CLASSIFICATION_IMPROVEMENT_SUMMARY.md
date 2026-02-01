# 신뢰도 평가 방식 개선 요약

**날짜**: 2026-01-30
**버전**: main_agent.py v2.5.0
**목적**: 경쟁 기반 신뢰도 평가에서 독립 평가 방식으로 전환

---

## 문제 분석

### 기존 방식 (경쟁 기반)
```python
# 총점을 1.0으로 정규화
total_score = sum(scores.values())
confidence_scores = {tier: score / total_score for tier, score in scores.items()}
```

**문제점**:
- Tier 간 경쟁으로 신뢰도가 1.0을 나눠가짐
- 예: C=0.278, D=0.667, E=0.056 → 평균 신뢰도가 낮음
- "잘못된 문서 생성"이라는 명확한 Tier C 작업도 낮은 신뢰도(0.278)
- 유효한 복수 후보를 식별하지 못함

### 로그 사례 (#file:mcp_server_20260130_194123.log)
```
[CLASSIFY] Scores: {'C': 0.278, 'D': 0.667, 'E': 0.056}
```
→ 문서가 "incorrectly generated"라는 명확한 수정 작업인데 Tier C가 0.278에 불과

---

## 개선 방식 (독립 평가)

### 핵심 변경사항

#### 1. 독립 점수 평가
```python
# 각 tier가 독립적으로 0.0~1.0 평가
tier_keywords = {
    "C": {
        "max_score": 12.0,  # 문서 수정은 더 높은 max_score
        "keywords": [
            "incorrectly created", "wrong document", "should merge",
            "잘못 생성", "문서 병합", "incorrectly generated"
        ]
    },
    "D": {
        "max_score": 10.0,  # 문서 분석은 일반 max_score
        "keywords": [
            "analyze document", "check document", "validate"
        ]
    }
}

# 정규화: tier별 max_score 사용
normalized_score = min(1.0, max(0.0, raw_score / max_score))
```

#### 2. 문맥 기반 보너스 강화
```python
if tier == "C":
    # 문서 수정 강력 시그널
    if ("incorrectly" or "잘못") and ("document" or "generated" or "created"):
        raw_score += 4.0  # STRONG bonus
    if ("merge" or "병합") and ("document" or "문서"):
        raw_score += 3.0
    if "wrong directory" or "wrong path":
        raw_score += 3.0
```

#### 3. 유효한 복수 tier 추적
```python
# 절대값 0.4 이상인 모든 tier 저장
VALID_THRESHOLD = 0.4
valid_tiers = [
    (tier, conf) for tier, conf in independent_scores.items()
    if conf >= VALID_THRESHOLD and tier != primary_tier
]

# 신뢰도 순 정렬
valid_tiers.sort(key=lambda x: x[1], reverse=True)
self._alternative_tiers = valid_tiers
```

#### 4. 대안 tier 연속 라우팅
```python
def _find_system_manageable_tiers(self, current_tier, context):
    # PRIORITY 1: 분류 기반 대안 (독립 평가에서 유효한 tier들)
    if hasattr(self, '_alternative_tiers') and self._alternative_tiers:
        classification_alternatives = [tier for tier, conf in self._alternative_tiers]
    
    # PRIORITY 2: 의존성 기반 대안 (기존 fallback)
    dependency_alternatives = tier_alternatives.get(current_tier, [])
    
    # 결합: 분류 우선, 중복 제거
    combined = classification_alternatives + [t for t in dependency_alternatives if t not in classification_alternatives]
```

---

## 예상 결과

### 기존 (#file:mcp_server_20260130_194123.log 재처리 시)
```
Input: "docs_2\MIGRATION_GUIDE_v3.1.0.md is an incorrectly generated document..."

[CLASSIFY] Independent Scores: {
  'A': 0.0,
  'B': 0.0,
  'C': 0.75,  # ← 독립 평가: 0.75 (9.0 / 12.0)
  'D': 0.25,  # ← 독립 평가: 0.25 (2.5 / 10.0)
  'E': 0.05,
  'F': 0.0
}

[CLASSIFY] Alternative Tiers (>=0.4): (없음, D도 0.4 미만)

Primary: Tier C (confidence: 0.75)
```

**개선 효과**:
- Tier C가 우선 실행 (올바른 선택)
- 신뢰도 0.75로 자동 승인 가능 (기존: 0.278)
- Tier D는 대안 목록에서 제외 (절대값 0.25 < 0.4)

---

## 추가 개선사항

### Credit 최적화
1. **높은 신뢰도 자동 승인**: 0.75 → 사람 개입 불필요
2. **대안 tier 우선순위**: 분류 기반 > 의존성 기반
3. **Circuit breaker 필터**: 실패 이력 tier 제외

### 로깅 강화
```python
print(f"[CLASSIFY] Independent Scores: {independent_scores}")
print(f"[CLASSIFY] Alternative Tiers (>=0.4): {alt_str}")
print(f"[ALTERNATIVE_ROUTING] Using classification-based alternatives: {classification_alternatives}")
```

---

## 검증 체크리스트

- [x] 독립 평가 방식 구현 (max_score 기반)
- [x] Tier C 문서 수정 키워드 강화
- [x] Tier D 문서 분석과 차별화
- [x] 대안 tier 추적 (`self._alternative_tiers`)
- [x] 대안 tier 우선순위 적용
- [x] 로깅 출력 추가
- [ ] 실제 테스트 실행 필요
- [ ] 메트릭 수집 및 분석

---

## 다음 단계

1. **테스트 실행**:
   ```bash
   python .github/agents/tool/main_agent.py "docs_2\MIGRATION_GUIDE_v3.1.0.md is an incorrectly generated document..."
   ```

2. **로그 확인**:
   - `[CLASSIFY] Independent Scores`
   - `[CLASSIFY] Alternative Tiers`
   - `[ALTERNATIVE_ROUTING]` 메시지

3. **메트릭 검증**:
   - Tier C 실행 여부
   - 신뢰도 점수 개선
   - 대안 tier 활용도

---

**결론**: 경쟁 방식(1.0 분배) → 독립 평가 방식(각 tier 독립 0.0~1.0)으로 전환 완료. 문서 수정 작업(Tier C)의 신뢰도가 크게 향상될 것으로 예상.
