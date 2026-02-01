# Document Merger - Semantic Document Merging

## Overview

The `DocumentMerger` module provides intelligent, semantic document merging capabilities that comply with the Agent Document Modification Policy (ADMP). It analyzes documents, identifies related sections through semantic similarity, and merges content by integrating related paragraphs rather than performing simple appends.

## Key Features

### 1. Semantic Analysis
- **Keyword Extraction**: Automatically extracts significant keywords from document content
- **Category Identification**: Classifies sections into categories (testing, implementation, security, etc.)
- **Similarity Calculation**: Computes semantic similarity between sections (0.0-1.0 score)

### 2. Intelligent Merging
- **Section Matching**: Finds matching sections across documents based on title and content similarity
- **Content Integration**: Merges related content intelligently, avoiding duplicate sections
- **Paragraph Deduplication**: Prevents adding duplicate content when merging

### 3. ADMP Compliance
- **Version Increment**: Automatically increments version (e.g., v2.0.3 → v2.1.0)
- **Changelog Generation**: Adds changelog entries for all merges
- **Consolidation**: Merges into existing documents instead of creating separate files
- **Justification Tracking**: Records rationale for merge decisions

## Usage

### Basic Usage

```python
from doc_management.document_merger import DocumentMerger
from pathlib import Path

# Initialize merger
workspace = Path(".")
merger = DocumentMerger(workspace)

# Merge enhancements into existing report
result = merger.merge_documents(
    source_path=Path("enhancements.md"),
    target_path=Path("implementation_report.md"),
    merge_justification="Consolidating enhancements per ADMP Scenario D"
)

# Check results
print(f"Version: {result['old_version']} → {result['new_version']}")
print(f"Sections processed: {result['merge_decisions']}")
print(f"Integrated: {result['integrated']}")
print(f"Appended: {result['appended']}")
print(f"New sections: {result['new_sections']}")
```

### Integration with E_Document_Management

```python
from doc_management import DocumentManagementEngine
from models.core import TaskContext

# Create context
context = TaskContext(
    user_input="Merge enhancements into main report",
    current_tier="E",
    workspace_root="."
)

# Initialize engine
engine = DocumentManagementEngine(context, previous_payload)

# Perform merge
result = engine.manage_document_merge(
    source_path=Path("enhancements.md"),
    target_path=Path("main_report.md"),
    justification="Adding new features per ADMP policy"
)
```

## Merge Decision Logic

The merger uses a three-tier decision system based on similarity scores:

### 1. High Similarity (≥ 0.6): INTEGRATE
- Sections are very similar (same topic/category)
- Content is merged by integrating paragraphs
- Duplicate content is detected and excluded
- **Example**: "Testing Framework" + "Testing Implementation" → Merged section

### 2. Medium Similarity (0.3-0.6): APPEND
- Sections are related but distinct
- Content is appended to the related section
- Section header is not duplicated
- **Example**: "Security" + "Authentication" → Appended under Security

### 3. Low Similarity (< 0.3): NEW_SECTION
- No similar section found
- Creates a new section in the target document
- Added before changelog if it exists
- **Example**: "Performance Metrics" → New section added

## Semantic Categories

The analyzer recognizes these categories automatically:

- **Implementation**: Code, development, building
- **Testing**: Tests, validation, verification
- **Documentation**: Docs, guides, manuals
- **Architecture**: Design, patterns, structure
- **Configuration**: Setup, install, environment
- **Performance**: Optimization, speed, benchmarks
- **Security**: Authentication, encryption, vulnerabilities
- **Enhancement**: Features, improvements, upgrades
- **Bugfix**: Issues, errors, problems
- **Refactoring**: Cleanup, reorganization

## Output Format

The merge operation returns a detailed result dictionary:

```python
{
    "success": True,
    "source": "path/to/source.md",
    "target": "path/to/target.md",
    "old_version": "2.0.3",
    "new_version": "2.1.0",
    "merge_decisions": 3,
    "integrated": 1,
    "appended": 1,
    "new_sections": 1,
    "decisions": [
        {
            "source_title": "Testing Enhancements",
            "target_title": "Testing Framework",
            "action": "integrate",
            "similarity": 0.75,
            "justification": "Merging 'Testing Enhancements' into 'Testing Framework' (similarity: 0.75)"
        },
        # ... more decisions
    ]
}
```

## ADMP Scenario D: Consolidation Rule

Per ADMP policy, when enhancements or new features are implemented:

### ❌ WRONG: Creating Separate Documents
```
docs/
├── IMPLEMENTATION_REPORT.md
├── ENHANCED_FEATURES.md          # ❌ Separate document
└── SECURITY_UPDATES.md           # ❌ Document fragmentation
```

### ✅ CORRECT: Merge into Existing Report
```python
merger.merge_documents(
    source_path=Path("ENHANCED_FEATURES.md"),
    target_path=Path("IMPLEMENTATION_REPORT.md"),
    justification="Consolidating per ADMP Scenario D"
)
```

Result:
- Version incremented: v2.0.3 → v2.1.0
- Changelog entry added
- Content semantically merged
- Source document can be removed after merge

## Examples

See `example_merge_usage.py` for complete working examples:

```bash
cd .github/agents/tool/doc_management
python example_merge_usage.py
```

## Testing

Comprehensive test suite with 26 tests covering:

- Semantic analysis (keyword extraction, categorization, similarity)
- Document parsing and section detection
- Merge decisions and content integration
- Version management and changelog generation
- ADMP compliance enforcement

Run tests:
```bash
cd /home/runner/work/turbo-system/turbo-system
python -m pytest .github/agents/tool/tests/test_document_merger.py -v
python -m pytest .github/agents/tool/tests/test_document_merge_integration.py -v
```

## API Reference

### DocumentMerger

#### `__init__(workspace_root: Path)`
Initialize the document merger.

#### `merge_documents(source_path: Path, target_path: Path, merge_justification: str = "Automated semantic merge") -> Dict`
Merge source document into target document.

**Returns**: Result dictionary with merge details.

#### `parse_document(doc_path: Path) -> Tuple[Dict, List[DocumentSection]]`
Parse document into metadata and sections.

#### `increment_version(version_str: str) -> str`
Increment version number for merge (N.N.N → N.N+1.0).

#### `add_changelog_entry(content: str, change_description: str, version: str) -> str`
Add changelog entry to document.

### SemanticAnalyzer

#### `extract_keywords(text: str) -> Set[str]`
Extract significant keywords from text.

#### `identify_category(section: DocumentSection) -> str`
Identify category of a section.

#### `calculate_similarity(section1: DocumentSection, section2: DocumentSection) -> float`
Calculate semantic similarity between sections (0.0-1.0).

## Configuration

### Similarity Thresholds

```python
class DocumentMerger:
    MERGE_THRESHOLD = 0.6      # High similarity: integrate
    APPEND_THRESHOLD = 0.3     # Medium similarity: append
```

Adjust these constants to control merge behavior:
- Higher MERGE_THRESHOLD → More conservative merging
- Lower APPEND_THRESHOLD → More aggressive appending

## Troubleshooting

### Issue: Sections not merging (creating duplicates)

**Cause**: Similarity score below MERGE_THRESHOLD  
**Solution**: Check section titles and content similarity. Sections with identical titles get 0.95 similarity automatically.

### Issue: Version not incrementing

**Cause**: No **Version**: field in target document  
**Solution**: Add version metadata at document top:
```markdown
**Version**: 1.0.0
```

### Issue: Changelog not found

**Cause**: No changelog section exists  
**Solution**: Merger automatically creates changelog section if missing.

## Best Practices

1. **Always provide justification**: Helps with ADMP traceability
2. **Review merge decisions**: Check the returned `decisions` array
3. **Backup important documents**: Merge modifies target in-place
4. **Use semantic titles**: Clear, descriptive section titles improve matching
5. **Maintain version metadata**: Include **Version**: field in documents

## Related Documentation

- [ADMP Policy](../../docs_2/guidelines/agent-document-modification-policy.md)
- [E_Document_Management.py](../E_Document_Management.py)
- [Documentation Guidelines](../../docs_2/guidelines/documentation-guidelines.md)

## Version History

- **1.0.0** (2026-01-23): Initial implementation with semantic merging and ADMP compliance
