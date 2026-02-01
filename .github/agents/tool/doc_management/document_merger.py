"""
Document Merger - Semantic Document Merging with ADMP Compliance

Handles:
- Semantic analysis of document sections and categories
- Content integration based on similarity and relevance
- Category-based section matching
- Version increment and changelog generation
- ADMP policy enforcement for merges

Key Features:
- Identifies related sections by semantic similarity
- Merges content by integrating related paragraphs (not simple append)
- Ensures merges happen within existing documents
- Increments version numbers and adds changelog entries
- Prevents creation of separate documents for enhancements

ADMP Compliance:
- Consolidation Rule: Merges into existing Implementation Reports
- Version Updates: Increments version (e.g., v2.0.3 → v2.1.0)
- Changelog: Adds changelog entries for all merges
- Justification: Includes agent rationale for merge decisions
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class DocumentSection:
    """Represents a document section with metadata"""
    title: str
    content: str
    level: int  # Header level (1-6)
    line_start: int
    line_end: int
    category: Optional[str] = None  # Extracted category/topic
    keywords: Set[str] = None  # Extracted keywords


@dataclass
class MergeDecision:
    """Represents a decision about merging sections"""
    source_section: DocumentSection
    target_section: Optional[DocumentSection]
    action: str  # "integrate", "append", "new_section"
    similarity_score: float
    justification: str


class SemanticAnalyzer:
    """
    Analyzes document content for semantic similarity and categories
    
    Provides:
    - Keyword extraction from sections
    - Category identification from headers and content
    - Similarity scoring between sections
    - Topic detection
    """
    
    # Stop words to filter out from keyword extraction
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'be', 'this',
        'that', 'it', 'will', 'can', 'has', 'have', 'had'
    }
    
    # Common category keywords for matching
    CATEGORY_KEYWORDS = {
        "implementation": ["implement", "code", "develop", "build", "create"],
        "testing": ["test", "validation", "verify", "check", "assert"],
        "documentation": ["doc", "guide", "readme", "manual", "reference"],
        "architecture": ["design", "pattern", "structure", "architecture", "diagram"],
        "configuration": ["config", "setup", "install", "env", "settings"],
        "performance": ["performance", "optimize", "speed", "efficiency", "benchmark"],
        "security": ["security", "auth", "permission", "vulnerability", "encrypt"],
        "enhancement": ["enhance", "improve", "feature", "upgrade", "extend"],
        "bugfix": ["bug", "fix", "issue", "error", "problem"],
        "refactoring": ["refactor", "cleanup", "reorganize", "restructure"],
    }
    
    @staticmethod
    def extract_keywords(text: str) -> Set[str]:
        """Extract significant keywords from text"""
        # Convert to lowercase and split
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common words and short words
        keywords = {
            w for w in words 
            if len(w) > 3 and w not in SemanticAnalyzer.STOP_WORDS
        }
        return keywords
    
    @staticmethod
    def identify_category(section: DocumentSection) -> str:
        """Identify category of a section based on title and content"""
        combined_text = f"{section.title} {section.content}".lower()
        
        # Check against category keywords
        category_scores = {}
        for category, keywords in SemanticAnalyzer.CATEGORY_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            # Return category with highest score
            return max(category_scores.items(), key=lambda x: x[1])[0]
        
        return "general"
    
    @staticmethod
    def calculate_similarity(section1: DocumentSection, section2: DocumentSection) -> float:
        """
        Calculate semantic similarity between two sections
        
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Exact title match gets high score
        if section1.title.lower() == section2.title.lower():
            return 0.95  # Very high similarity for exact title match
        
        # Title similarity (weighted more heavily)
        title_sim = SequenceMatcher(None, section1.title.lower(), section2.title.lower()).ratio()
        
        # Keyword overlap
        keywords1 = section1.keywords or SemanticAnalyzer.extract_keywords(section1.content)
        keywords2 = section2.keywords or SemanticAnalyzer.extract_keywords(section2.content)
        
        if keywords1 and keywords2:
            common_keywords = keywords1.intersection(keywords2)
            total_keywords = keywords1.union(keywords2)
            keyword_sim = len(common_keywords) / len(total_keywords) if total_keywords else 0.0
        else:
            keyword_sim = 0.0
        
        # Category match
        category_match = 1.0 if section1.category == section2.category else 0.0
        
        # Combined score (weighted average)
        similarity = (title_sim * 0.4 + keyword_sim * 0.4 + category_match * 0.2)
        
        return similarity


class DocumentMerger:
    """
    Semantic document merger with ADMP compliance
    
    Features:
    - Parses documents into sections
    - Identifies related sections through semantic analysis
    - Merges content by integrating related paragraphs
    - Updates version numbers
    - Adds changelog entries
    - Enforces ADMP consolidation rule
    """
    
    # Similarity thresholds for merging (empirically determined)
    # These values balance precision (avoiding false merges) with recall (finding related content)
    # 
    # MERGE_THRESHOLD = 0.6: Sections with ≥60% similarity are integrated
    #   - Rationale: High confidence that sections discuss the same topic
    #   - Impact: Lower values may cause unrelated content to merge; higher may miss valid merges
    #   - Typical matches: Same section titles, high keyword overlap, matching categories
    # 
    # APPEND_THRESHOLD = 0.3: Sections with 30-60% similarity are appended
    #   - Rationale: Related but distinct content (e.g., "Security" and "Authentication")
    #   - Impact: Lower values add more tangential content; higher may miss related sections
    #   - Typical matches: Related categories, some keyword overlap, similar context
    # 
    # Below 0.3: Creates new sections (content is unrelated)
    MERGE_THRESHOLD = 0.6  # Sections with similarity >= 0.6 will be merged
    APPEND_THRESHOLD = 0.3  # Sections with similarity >= 0.3 will be appended to related section
    
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.analyzer = SemanticAnalyzer()
    
    def parse_document(self, doc_path: Path) -> Tuple[Dict[str, str], List[DocumentSection]]:
        """
        Parse document into metadata and sections
        
        Returns:
            Tuple of (metadata_dict, sections_list)
        """
        if not doc_path.exists():
            return {}, []
        
        content = doc_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        sections = []
        current_section = None
        metadata = {}
        
        for i, line in enumerate(lines):
            # Extract metadata from header (e.g., **Version**: 1.0.0)
            # Do this before checking for headers
            metadata_match = re.match(r'\*\*(.+?)\*\*:\s*(.+)$', line.strip())
            if metadata_match:
                key = metadata_match.group(1).strip()
                value = metadata_match.group(2).strip()
                metadata[key] = value
            
            # Check for header
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            
            if header_match:
                # Save previous section
                if current_section:
                    current_section.line_end = i - 1
                    current_section.content = '\n'.join(lines[current_section.line_start:current_section.line_end + 1])
                    current_section.keywords = self.analyzer.extract_keywords(current_section.content)
                    current_section.category = self.analyzer.identify_category(current_section)
                    sections.append(current_section)
                
                # Start new section
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                
                current_section = DocumentSection(
                    title=title,
                    content="",
                    level=level,
                    line_start=i,
                    line_end=i
                )
        
        # Save last section
        if current_section:
            current_section.line_end = len(lines) - 1
            current_section.content = '\n'.join(lines[current_section.line_start:current_section.line_end + 1])
            current_section.keywords = self.analyzer.extract_keywords(current_section.content)
            current_section.category = self.analyzer.identify_category(current_section)
            sections.append(current_section)
        
        return metadata, sections
    
    def find_matching_section(
        self, 
        source_section: DocumentSection, 
        target_sections: List[DocumentSection]
    ) -> Tuple[Optional[DocumentSection], float]:
        """
        Find best matching section in target document
        
        Returns:
            Tuple of (matching_section, similarity_score)
        """
        best_match = None
        best_score = 0.0
        
        for target_section in target_sections:
            # Skip if different header levels (don't merge different hierarchy levels)
            if abs(source_section.level - target_section.level) > 1:
                continue
            
            similarity = self.analyzer.calculate_similarity(source_section, target_section)
            
            if similarity > best_score:
                best_score = similarity
                best_match = target_section
        
        return best_match, best_score
    
    def merge_sections(
        self, 
        source_section: DocumentSection, 
        target_section: DocumentSection
    ) -> str:
        """
        Merge source section content into target section
        
        Intelligently integrates related paragraphs instead of simple append
        """
        # Extract paragraphs from both sections
        source_paragraphs = [p.strip() for p in source_section.content.split('\n\n') if p.strip()]
        target_content = target_section.content
        
        # Add merge header
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        merge_header = f"\n\n**[Merged Content - {timestamp}]**\n"
        
        # Integrate paragraphs that are not duplicates
        merged_content = target_content + merge_header
        
        for para in source_paragraphs:
            # Skip if paragraph already exists in target (similarity check)
            is_duplicate = False
            for existing_para in target_content.split('\n\n'):
                similarity = SequenceMatcher(None, para.lower(), existing_para.lower()).ratio()
                if similarity > 0.8:  # 80% similar = duplicate
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                merged_content += f"\n{para}\n"
        
        return merged_content
    
    def increment_version(self, version_str: str) -> str:
        """
        Increment version number for merge
        
        Follows semantic versioning: v2.0.3 → v2.1.0
        """
        # Parse version
        version_match = re.match(r'v?(\d+)\.(\d+)\.(\d+)', version_str)
        if version_match:
            major, minor, patch = map(int, version_match.groups())
            # Increment minor version for merge, reset patch
            new_version = f"{major}.{minor + 1}.0"
            return new_version
        
        # Default if can't parse
        return "1.0.0"
    
    def add_changelog_entry(
        self, 
        content: str, 
        change_description: str,
        version: str
    ) -> str:
        """
        Add changelog entry to document
        
        Creates changelog section if not exists
        """
        timestamp = datetime.now().strftime("%Y-%m-%d")
        changelog_entry = f"\n### Version {version} ({timestamp})\n- {change_description}\n"
        
        # Find changelog section
        changelog_pattern = r'(## Changelog|## 📝 Changelog|## Change Log)'
        if re.search(changelog_pattern, content):
            # Insert after changelog header
            content = re.sub(
                changelog_pattern,
                rf'\1\n{changelog_entry}',
                content
            )
        else:
            # Add changelog section at end
            content += f"\n\n## 📝 Changelog{changelog_entry}"
        
        return content
    
    def merge_documents(
        self,
        source_path: Path,
        target_path: Path,
        merge_justification: str = "Automated semantic merge"
    ) -> Dict[str, any]:
        """
        Merge source document into target document with semantic analysis
        
        Args:
            source_path: Source document to merge from
            target_path: Target document to merge into
            merge_justification: Justification for merge (ADMP requirement)
        
        Returns:
            Result dict with merge details
        """
        if not source_path.exists():
            return {"success": False, "error": "Source document not found"}
        
        if not target_path.exists():
            return {"success": False, "error": "Target document not found"}
        
        # Parse both documents
        source_metadata, source_sections = self.parse_document(source_path)
        target_metadata, target_sections = self.parse_document(target_path)
        
        # Analyze merge decisions
        merge_decisions: List[MergeDecision] = []
        
        for source_section in source_sections:
            # Skip top-level title
            if source_section.level == 1:
                continue
            
            # Find matching section
            matching_section, similarity = self.find_matching_section(source_section, target_sections)
            
            if matching_section and similarity >= self.MERGE_THRESHOLD:
                # High similarity - integrate content
                decision = MergeDecision(
                    source_section=source_section,
                    target_section=matching_section,
                    action="integrate",
                    similarity_score=similarity,
                    justification=f"Merging '{source_section.title}' into '{matching_section.title}' (similarity: {similarity:.2f})"
                )
            elif matching_section and similarity >= self.APPEND_THRESHOLD:
                # Medium similarity - append to related section
                decision = MergeDecision(
                    source_section=source_section,
                    target_section=matching_section,
                    action="append",
                    similarity_score=similarity,
                    justification=f"Appending '{source_section.title}' to related section '{matching_section.title}' (similarity: {similarity:.2f})"
                )
            else:
                # Low similarity - create new section
                decision = MergeDecision(
                    source_section=source_section,
                    target_section=None,
                    action="new_section",
                    similarity_score=similarity,
                    justification=f"Adding '{source_section.title}' as new section (no similar section found)"
                )
            
            merge_decisions.append(decision)
        
        # Execute merge
        target_content = target_path.read_text(encoding='utf-8')
        
        for decision in merge_decisions:
            if decision.action == "integrate":
                # Replace target section with merged content
                merged_content = self.merge_sections(decision.source_section, decision.target_section)
                target_content = target_content.replace(
                    decision.target_section.content,
                    merged_content
                )
            elif decision.action == "append":
                # Append to target section
                # Extract just the body content (skip the header line)
                section_lines = decision.source_section.content.split('\n')
                # Skip first line (the header) and any empty lines after it
                body_start = 1
                while body_start < len(section_lines) and not section_lines[body_start].strip():
                    body_start += 1
                body_lines = section_lines[body_start:] if body_start < len(section_lines) else []
                section_body = '\n'.join(body_lines).strip()
                
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                append_content = f"\n\n**[Related Content - {timestamp}]**\n\n{section_body}\n"
                target_content = target_content.replace(
                    decision.target_section.content,
                    decision.target_section.content + append_content
                )
            else:  # new_section
                # Add as new section at end (before changelog if exists)
                # Extract just the body content (skip the header line)
                section_lines = decision.source_section.content.split('\n')
                # Skip first line (the header)
                body_lines = section_lines[1:] if len(section_lines) > 1 else section_lines
                section_body = '\n'.join(body_lines).strip()
                
                new_section = f"\n\n## {decision.source_section.title}\n\n{section_body}\n"
                if "## Changelog" in target_content or "## 📝 Changelog" in target_content:
                    target_content = re.sub(
                        r'(## (?:📝 )?Changelog)',
                        f'{new_section}\\1',
                        target_content
                    )
                else:
                    target_content += new_section
        
        # Update version
        current_version = target_metadata.get("Version", "1.0.0")
        new_version = self.increment_version(current_version)
        
        # Update version in content
        target_content = re.sub(
            r'\*\*Version\*\*:\s*[\d.]+',
            f'**Version**: {new_version}',
            target_content
        )
        
        # Add changelog entry
        change_desc = f"Merged content from {source_path.name}. {merge_justification}. Decisions: {len(merge_decisions)} sections processed."
        target_content = self.add_changelog_entry(target_content, change_desc, new_version)
        
        # Write merged content
        target_path.write_text(target_content, encoding='utf-8')
        
        return {
            "success": True,
            "source": str(source_path),
            "target": str(target_path),
            "old_version": current_version,
            "new_version": new_version,
            "merge_decisions": len(merge_decisions),
            "integrated": sum(1 for d in merge_decisions if d.action == "integrate"),
            "appended": sum(1 for d in merge_decisions if d.action == "append"),
            "new_sections": sum(1 for d in merge_decisions if d.action == "new_section"),
            "decisions": [
                {
                    "source_title": d.source_section.title,
                    "target_title": d.target_section.title if d.target_section else None,
                    "action": d.action,
                    "similarity": d.similarity_score,
                    "justification": d.justification
                }
                for d in merge_decisions
            ]
        }


    def analyze_merge_strategy(
        self,
        source_path: Path,
        related_docs: List[Path],
        keywords: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        신뢰도 기반 병합 전략 분석
        
        Args:
            source_path: 신규 문서 경로
            related_docs: 관련 문서 목록 (관련성 순)
            keywords: 검색 키워드 (선택)
            
        Returns:
            분석 결과 및 전략 권장사항
        """
        if not source_path.exists():
            return {
                "success": False,
                "error": "Source document not found"
            }
        
        # 신규 문서 분석
        source_content = source_path.read_text(encoding='utf-8')
        source_word_count = len(source_content.split())
        source_metadata, source_sections = self.parse_document(source_path)
        
        # 관련 문서 분석
        related_analyses = []
        total_existing_words = 0
        
        for doc_path in related_docs[:5]:  # Top 5만 분석
            if not doc_path.exists():
                continue
            
            content = doc_path.read_text(encoding='utf-8')
            word_count = len(content.split())
            total_existing_words += word_count
            
            metadata, sections = self.parse_document(doc_path)
            
            # 키워드 매칭 점수
            if keywords:
                doc_keywords = self.analyzer.extract_keywords(content)
                match_count = len(keywords.intersection(doc_keywords))
                relevance_score = match_count / len(keywords) if keywords else 0.0
            else:
                relevance_score = 1.0 / (related_docs.index(doc_path) + 1)  # 순위 기반
            
            related_analyses.append({
                "path": doc_path,
                "word_count": word_count,
                "section_count": len(sections),
                "relevance_score": relevance_score,
                "metadata": metadata
            })
        
        # 전략 결정 (신뢰도 기반 작업 규칙)
        if len(related_analyses) == 0:
            # 관련 문서 없음 → 새로 생성
            strategy = "UNIFIED_CREATION"
            confidence = 0.6
            reasoning = "No related documents found. New document should be created."
            target_doc = None
            recommendations = [
                f"Create new document: {source_path.name}",
                "Ensure proper directory structure (docs_2/P?/)",
                "Link to related documents if discovered later"
            ]
        
        elif len(related_analyses) > 1:
            # 여러 문서 존재
            if total_existing_words > source_word_count:
                # 규칙 1: 여러 문서 분산 + 기존 > 신규
                strategy = "DISTRIBUTED_EDIT"
                confidence = 0.85
                top_doc = related_analyses[0]["path"]
                reasoning = (
                    f"Multiple related documents ({len(related_analyses)}) with total content "
                    f"({total_existing_words} words) larger than new content ({source_word_count} words). "
                    f"Content should be distributed across existing documents."
                )
                target_doc = top_doc
                recommendations = [
                    f"Primary target: {top_doc.name}",
                    f"Distribute content across {len(related_analyses)} related documents",
                    "Keep existing document structure intact",
                    "Add cross-references between affected documents",
                    f"Delete {source_path.name} after merging"
                ]
            else:
                # 규칙 3: 여러 문서 + 기존 < 신규 → 통합 생성
                strategy = "UNIFIED_CREATION"
                confidence = 0.75
                top_doc = related_analyses[0]["path"]
                reasoning = (
                    f"Multiple related documents exist, but total content "
                    f"({total_existing_words} words) is less than new content ({source_word_count} words). "
                    f"Create consolidated document."
                )
                target_doc = None
                recommendations = [
                    f"Create consolidated document in same directory as {top_doc.name}",
                    f"Merge content from {len(related_analyses)} related documents",
                    "Update cross-references in original documents",
                    "Consider deleting scattered documents after consolidation"
                ]
        
        else:
            # 단일 문서 존재
            top_doc = related_analyses[0]["path"]
            existing_words = related_analyses[0]["word_count"]
            
            if existing_words > source_word_count:
                # 규칙 2: 단일 문서 + 기존 > 신규
                strategy = "SINGLE_DOC_MODIFY"
                confidence = 0.9
                reasoning = (
                    f"Single most relevant document ({top_doc.name}) exists with "
                    f"substantial content ({existing_words} words) that exceeds new content "
                    f"({source_word_count} words). Merge by modifying target document."
                )
                target_doc = top_doc
                recommendations = [
                    f"Target document: {top_doc.name}",
                    "Use merge_documents() to integrate content semantically",
                    "Update document version number",
                    "Add changelog entry",
                    f"Delete {source_path.name} after merging"
                ]
            else:
                # 규칙 3: 단일 문서 + 기존 < 신규 → 통합 생성
                strategy = "UNIFIED_CREATION"
                confidence = 0.8
                reasoning = (
                    f"Single related document found, but new content "
                    f"({source_word_count} words) exceeds existing document ({existing_words} words). "
                    f"Create new consolidated document."
                )
                target_doc = None
                recommendations = [
                    f"Create new document in same directory as {top_doc.name}",
                    f"Move content from {top_doc.name} into new document",
                    "Consolidate all related information",
                    "Update references in original location"
                ]
        
        return {
            "success": True,
            "strategy": strategy,
            "confidence": confidence,
            "reasoning": reasoning,
            "target_document": str(target_doc) if target_doc else None,
            "related_documents": [str(a["path"]) for a in related_analyses],
            "source_word_count": source_word_count,
            "total_existing_words": total_existing_words,
            "recommendations": recommendations,
            "analysis_details": related_analyses
        }


__all__ = ["DocumentMerger", "SemanticAnalyzer", "DocumentSection", "MergeDecision"]
