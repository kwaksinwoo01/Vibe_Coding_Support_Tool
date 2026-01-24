"""
Integration test for Tier A complete workflow - L0→L1→L2→L3 hierarchy creation.

Tests the complete flow from Untitled-1.md specification.
"""

import sys
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from A_Working_Document_Progress import WorkPlanCreationEngine, main
from models.core import AgentState


class TestTierACompleteWorkflow:
    """Integration tests for complete Tier A workflow"""
    
    def test_step_1_3_0_create_l1_from_main_document(self):
        """
        Test Step 1.3.0: Create L1 WPD from main document when Three-Tier Documentation is missing
        """
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create main document with task but no Three-Tier Documentation
            docs_dir = workspace_root / "docs_2"
            docs_dir.mkdir(parents=True, exist_ok=True)
            main_doc = docs_dir / "NextTask-2.md"
            main_doc.write_text("""
# Main Progress Document

**WPD_grade**: L0

## 🟢 step 5: Implement Feature X

### Goal: Add new feature to the system
**Status**: 📋 PENDING

## Other sections
Content here
""", encoding='utf-8')
            
            # Execute Tier A
            engine = WorkPlanCreationEngine(str(workspace_root))
            state = engine.execute("Create a work plan for step 5")
            
            # Verify L1 was created
            assert state.status == "SUCCESS"
            assert len(engine.created_documents) > 0
            
            # Check that L1 document exists
            l1_path = workspace_root / "docs_2" / "P5" / "P5-Implement Feature X.md"
            assert l1_path.exists(), f"L1 document should be created at {l1_path}"
            
            # Verify content
            content = l1_path.read_text(encoding='utf-8')
            assert "WPD" in content or "Document Metadata" in content
    
    def test_step_2_1_create_l2_from_l1_with_phases(self):
        """
        Test Step 2.1 & 3.3-3.4: Create multiple L2 documents from L1 phases
        """
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create L1 document with multiple phases
            l1_dir = workspace_root / "docs_2" / "P5"
            l1_dir.mkdir(parents=True, exist_ok=True)
            l1_doc = l1_dir / "P5-Feature.md"
            l1_doc.write_text("""
# Feature Implementation

**WPD_grade**: L1

## 📋 Executive Summary
Feature implementation plan

## 🎯 Goals and Success Criteria
Complete feature

## 🔧 Execution Plan

### Phase 5.1: Setup Environment
Setup dependencies and configuration

**Action**: Install tools
**Files to Update**: requirements.txt
**Checklist**:
- [ ] Install Python packages
- [ ] Configure environment

### Phase 5.2: Implement Core Logic
Implement main functionality

**Action**: Write code
**Files to Update**: src/main.py
**Checklist**:
- [ ] Write functions
- [ ] Add tests

### Phase 5.3: Documentation
Write documentation

**Action**: Update docs
**Files to Update**: docs/README.md

## 📚 References
Parent: docs_2/NextTask-2.md
""", encoding='utf-8')
            
            # Execute Tier A with user-specified L1 document
            engine = WorkPlanCreationEngine(str(workspace_root))
            state = engine.execute(f"Create work plan from {l1_doc.relative_to(workspace_root)}")
            
            # Verify multiple L2 documents were created (one per phase)
            assert state.status == "SUCCESS"
            created = engine.created_documents
            
            # Should create L2 for each of the 3 phases
            l2_docs = [d for d in created if '.1-' in d or '.2-' in d or '.3-' in d]
            assert len(l2_docs) >= 3, f"Should create 3 L2 docs, created: {created}"
            
            # Verify L2 files exist
            l2_1 = l1_dir / "P5.1-Setup Environment.md"
            l2_2 = l1_dir / "P5.2-Implement Core Logic.md"
            l2_3 = l1_dir / "P5.3-Documentation.md"
            
            assert l2_1.exists(), f"L2 Phase 1 should exist: {l2_1}"
            assert l2_2.exists(), f"L2 Phase 2 should exist: {l2_2}"
            assert l2_3.exists(), f"L2 Phase 3 should exist: {l2_3}"
    
    def test_step_3_5_no_l3_when_under_300_lines(self):
        """
        Test Step 3.5.0: Do not create L3 when subphases are under 300 lines
        """
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create L2 document with small subphases (under 300 lines)
            l2_dir = workspace_root / "docs_2" / "P5"
            l2_dir.mkdir(parents=True, exist_ok=True)
            l2_doc = l2_dir / "P5.1-Setup.md"
            
            # Create small subphases
            subphase_content = """
**Action**: Short action
**Files to Update**: file.txt
**Checklist**:
- [ ] Item 1
- [ ] Item 2
"""
            
            l2_doc.write_text(f"""
# Setup Phase

**WPD_grade**: L2

## 📋 Overview
Setup overview

## Implementation Plan

### Subphase 5.1.1: Install Tools
{subphase_content}

### Subphase 5.1.2: Configure Settings
{subphase_content}

## 📚 References
Parent: docs_2/P5/P5-Feature.md
""", encoding='utf-8')
            
            # Execute Tier A with L2 document
            engine = WorkPlanCreationEngine(str(workspace_root))
            state = engine.execute(f"Create work plan from {l2_doc.relative_to(workspace_root)}")
            
            # Verify NO L3 documents were created (subphases are small)
            created = engine.created_documents
            l3_docs = [d for d in created if l2_doc.stem in d and d.count('.') == 2]
            
            # Should not create L3 since subphases are under 300 lines
            assert len(l3_docs) == 0, f"Should NOT create L3 docs for small subphases, but created: {l3_docs}"
    
    def test_step_3_5_1_create_l3_when_over_300_lines(self):
        """
        Test Step 3.5.1: Create L3 when subphases exceed 300 lines
        """
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create L2 document with large subphase (over 300 lines)
            l2_dir = workspace_root / "docs_2" / "P5"
            l2_dir.mkdir(parents=True, exist_ok=True)
            l2_doc = l2_dir / "P5.1-Setup.md"
            
            # Create large subphase content (>300 lines)
            large_content = "\n".join([f"Line {i}: Implementation detail" for i in range(350)])
            
            l2_doc.write_text(f"""
# Setup Phase

**WPD_grade**: L2

## 📋 Overview
Setup overview

## Implementation Plan

### Subphase 5.1.1: Complex Installation
{large_content}

**Action**: Complex action
**Files to Update**: many_files.txt

### Subphase 5.1.2: Simple Config
Small configuration step

## 📚 References
Parent: docs_2/P5/P5-Feature.md
""", encoding='utf-8')
            
            # Execute Tier A with L2 document
            engine = WorkPlanCreationEngine(str(workspace_root))
            state = engine.execute(f"Create work plan from {l2_doc.relative_to(workspace_root)}")
            
            # Verify L3 documents were created for large subphase
            created = engine.created_documents
            l3_docs = [d for d in created if '.1.' in d]  # L3 pattern: P5.1.1-
            
            # Should create at least one L3 doc for the large subphase
            assert len(l3_docs) > 0, f"Should create L3 docs for large subphases (>300 lines), created: {created}"
    
    def test_complete_l0_l1_l2_hierarchy(self):
        """
        Integration test: Complete L0→L1→L2 hierarchy creation from main document
        """
        with TemporaryDirectory() as tmpdir:
            workspace_root = Path(tmpdir)
            
            # Create main document (L0)
            docs_dir = workspace_root / "docs_2"
            docs_dir.mkdir(parents=True, exist_ok=True)
            main_doc = docs_dir / "NextTask-2.md"
            main_doc.write_text("""
# Main Progress Document

**WPD_grade**: L0

## 🟢 step 10: Complete Integration Test

### Goal: Test complete workflow
**Status**: 📋 PENDING

### Three-Tier Documentation
1. **WPD** (`docs_2/P10/P10-Complete Integration Test.md`) - Implementation plans
2. **PRD** (`docs_2/prd/PRD-P10.md`) - Progress tracking

""", encoding='utf-8')
            
            # Create L1 document with phases
            l1_dir = docs_dir / "P10"
            l1_dir.mkdir(parents=True, exist_ok=True)
            l1_doc = l1_dir / "P10-Complete Integration Test.md"
            l1_doc.write_text("""
# Complete Integration Test

**WPD_grade**: L1

## 🔧 Execution Plan

### Phase 10.1: Preparation
Prepare test environment

### Phase 10.2: Execution
Run integration tests

## 📚 References
Parent: docs_2/NextTask-2.md
""", encoding='utf-8')
            
            # Execute Tier A - should read existing L1 and create L2 documents
            engine = WorkPlanCreationEngine(str(workspace_root))
            state = engine.execute("Create work plan from existing WPD")
            
            # Verify success
            assert state.status == "SUCCESS"
            
            # Verify L2 documents created
            l2_1 = l1_dir / "P10.1-Preparation.md"
            l2_2 = l1_dir / "P10.2-Execution.md"
            
            assert l2_1.exists() or any('10.1-' in d for d in engine.created_documents), \
                f"L2 Phase 1 should be created, created: {engine.created_documents}"
            assert l2_2.exists() or any('10.2-' in d for d in engine.created_documents), \
                f"L2 Phase 2 should be created, created: {engine.created_documents}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
