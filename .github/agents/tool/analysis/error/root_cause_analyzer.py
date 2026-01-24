"""
Root Cause Analyzer - 근본원인 분석 엔진

책임:
- 이슈의 근본원인 파악
- 영향받는 컴포넌트 식별
- 분석 근거 수집
"""

from typing import Dict, Any, Optional, List
from ...models.core.reporting_models import IssueClassification, RootCauseAnalysis


class RootCauseAnalyzer:
    """근본원인 분석 엔진"""
    
    def analyze(
        self,
        issue_description: str,
        classification: IssueClassification,
        error_context: Optional[Dict[str, Any]] = None
    ) -> RootCauseAnalysis:
        """
        이슈의 근본원인을 분석
        
        Args:
            issue_description: 사용자의 이슈 설명
            classification: IssueClassification 결과
            error_context: 추가 오류 컨텍스트 (로그, traceback 등)
            
        Returns:
            RootCauseAnalysis 객체
        """
        error_context = error_context or {}
        
        # Step 1: 이슈 타입별 근본원인 분석
        root_cause = self._analyze_by_type(
            issue_description,
            classification.issue_type,
            classification.category,
            error_context
        )
        
        # Step 2: 영향받는 컴포넌트 식별
        affected_components = self._identify_components(
            issue_description,
            error_context
        )
        
        # Step 3: 분석 근거 수집
        evidence = self._collect_evidence(
            issue_description,
            error_context,
            classification
        )
        
        # Step 4: 신뢰도 결정
        confidence = self._determine_confidence(evidence, error_context)
        
        return RootCauseAnalysis(
            root_cause=root_cause,
            affected_components=affected_components,
            error_context=error_context,
            evidence=evidence,
            confidence_level=confidence
        )
    
    def _analyze_by_type(
        self,
        issue_desc: str,
        issue_type: str,
        category: str,
        error_context: Dict[str, Any]
    ) -> str:
        """이슈 타입별 근본원인 분석"""
        analysis_map = {
            "bug": self._analyze_bug,
            "design_flaw": self._analyze_design_flaw,
            "implementation": self._analyze_implementation,
            "documentation": self._analyze_documentation,
        }
        
        analyzer = analysis_map.get(issue_type, self._analyze_unknown)
        return analyzer(issue_desc, category, error_context)
    
    def _analyze_bug(self, issue_desc: str, category: str, context: Dict[str, Any]) -> str:
        """버그 분석"""
        if category == "implementation_error":
            return "Missing input validation or type checking in the implementation"
        elif category == "environment_error":
            return "Environment configuration or dependency issue"
        elif category == "data_error":
            return "Invalid or corrupted data being processed"
        else:
            return f"Bug in {category or 'implementation'} - requires investigation"
    
    def _analyze_design_flaw(self, issue_desc: str, category: str, context: Dict[str, Any]) -> str:
        """설계 오류 분석"""
        if category == "architecture":
            return "Architectural design does not meet current requirements"
        elif category == "algorithm":
            return "Algorithm inefficiency or incorrect logic"
        elif category == "interface":
            return "Interface design issue or API contract violation"
        else:
            return "Design issue requiring architectural review"
    
    def _analyze_implementation(self, issue_desc: str, category: str, context: Dict[str, Any]) -> str:
        """구현 오류 분석"""
        return "Implementation does not follow specifications or best practices"
    
    def _analyze_documentation(self, issue_desc: str, category: str, context: Dict[str, Any]) -> str:
        """문서화 부족 분석"""
        return "Documentation is incomplete or unclear"
    
    def _analyze_unknown(self, issue_desc: str, category: str, context: Dict[str, Any]) -> str:
        """미분류 분석"""
        return "Issue type unclear - requires further investigation"
    
    def _identify_components(self, issue_desc: str, context: Dict[str, Any]) -> List[str]:
        """영향받는 컴포넌트 식별"""
        components = []
        
        # 파일 경로 추출
        if "file" in context:
            components.append(context["file"])
        
        # 함수/메서드 추출
        if "function" in context:
            components.append(f"{context['function']}()")
        
        # 모듈 추출
        if "module" in context:
            components.append(context["module"])
        
        # 키워드 기반 추출
        keywords = ["module", "package", "class", "service", "handler"]
        issue_lower = issue_desc.lower()
        for keyword in keywords:
            if keyword in issue_lower:
                components.append(keyword)
        
        return list(set(components))
    
    def _collect_evidence(
        self,
        issue_desc: str,
        context: Dict[str, Any],
        classification: IssueClassification
    ) -> List[str]:
        """분석 근거 수집"""
        evidence = []
        
        # 원본 설명
        evidence.append(f"Original issue: {issue_desc[:100]}...")
        
        # 분류 정보
        evidence.append(f"Classification: {classification.issue_type} ({classification.severity})")
        
        # 컨텍스트
        if "error_message" in context:
            evidence.append(f"Error: {context['error_message']}")
        
        if "traceback" in context:
            evidence.append("Traceback available for analysis")
        
        if "log" in context:
            evidence.append("Log information available")
        
        return evidence
    
    def _determine_confidence(self, evidence: List[str], context: Dict[str, Any]) -> str:
        """신뢰도 결정"""
        if len(evidence) >= 4:
            return "high"
        elif len(evidence) >= 2:
            return "medium"
        else:
            return "low"


__all__ = ["RootCauseAnalyzer"]
