#!/usr/bin/env python3
"""
Example script demonstrating semantic document merging

This shows how to use the DocumentMerger to consolidate enhancements
into an existing Implementation Report per ADMP policy.

Usage:
    python example_merge_usage.py

Note: Uses sys.path.insert() for standalone script execution.
In production code, use proper imports from the doc_management package.
"""

import sys
from pathlib import Path

# Direct import for standalone script execution
# In production: from doc_management.document_merger import DocumentMerger
sys.path.insert(0, str(Path(__file__).parent))

from document_merger import DocumentMerger


def example_basic_merge():
    """Basic example: merge enhancements into report"""
    print("=" * 60)
    print("Example 1: Basic Merge")
    print("=" * 60)
    
    workspace = Path(".")
    merger = DocumentMerger(workspace)
    
    # Create example documents
    enhancements_path = Path("/tmp/enhancements.md")
    report_path = Path("/tmp/implementation_report.md")
    
    enhancements_content = """# Feature Enhancements

## Circuit Breaker Pattern

Implemented advanced fault tolerance:
- Automatic failure detection
- Exponential backoff
- Redis-based state persistence

## Decision Engine

Enhanced routing logic:
- Confidence scoring (0.0-1.0)
- Policy-based decisions
- Metrics collection
"""
    
    report_content = """# Implementation Report

**Version**: 2.0.3
**Status**: ACTIVE

## Overview

System implementation status and progress.

## Circuit Breaker

Basic circuit breaker with local state.

## Routing Logic

Simple keyword-based tier classification.
"""
    
    enhancements_path.write_text(enhancements_content, encoding='utf-8')
    report_path.write_text(report_content, encoding='utf-8')
    
    # Perform merge
    print("\nMerging enhancements into implementation report...")
    result = merger.merge_documents(
        enhancements_path,
        report_path,
        "Consolidating enhancements per ADMP Scenario D"
    )
    
    # Display results
    print(f"\n[SUCCESS] Merge completed successfully!")
    print(f"   Old version: {result['old_version']}")
    print(f"   New version: {result['new_version']}")
    print(f"   Sections processed: {result['merge_decisions']}")
    print(f"   - Integrated: {result['integrated']}")
    print(f"   - Appended: {result['appended']}")
    print(f"   - New sections: {result['new_sections']}")

    print("\nMerge decisions:")
    for decision in result['decisions']:
        print(f"   * {decision['action'].upper()}: '{decision['source_title']}' "
              f"(similarity: {decision['similarity']:.2f})")
    
    print("\nMerged content preview:")
    merged_content = report_path.read_text(encoding='utf-8')
    print("-" * 60)
    print(merged_content[:500] + "...")
    print("-" * 60)


def example_admp_compliance():
    """Example showing ADMP compliance features"""
    print("\n" + "=" * 60)
    print("Example 2: ADMP Compliance Features")
    print("=" * 60)
    
    workspace = Path(".")
    merger = DocumentMerger(workspace)
    
    source_path = Path("/tmp/new_features.md")
    target_path = Path("/tmp/main_report.md")
    
    source_path.write_text("# New Features\n## Feature 1\nDescription", encoding='utf-8')
    target_path.write_text("# Report\n**Version**: 1.5.0\n## Overview\nContent", encoding='utf-8')
    
    result = merger.merge_documents(source_path, target_path)
    
    merged = target_path.read_text(encoding='utf-8')
    
    print("\n[SUCCESS] ADMP Compliance Checks:")
    print(f"   [OK] Version incremented: {result['old_version']} -> {result['new_version']}")
    print(f"   [OK] Changelog added: {'## Changelog' in merged}")
    print(f"   [OK] No new files created (merged into existing)")
    print(f"   [OK] Justification tracked in changelog")


def example_semantic_matching():
    """Example showing semantic section matching"""
    print("\n" + "=" * 60)
    print("Example 3: Semantic Section Matching")
    print("=" * 60)
    
    workspace = Path(".")
    merger = DocumentMerger(workspace)
    
    source_path = Path("/tmp/security_updates.md")
    target_path = Path("/tmp/system_doc.md")
    
    source_content = """# Security Updates

## Authentication & Authorization

Added JWT token validation with RBAC support.
"""
    
    target_content = """# System Documentation

**Version**: 1.0.0

## Security Features

Basic authentication using session cookies.
"""
    
    source_path.write_text(source_content, encoding='utf-8')
    target_path.write_text(target_content, encoding='utf-8')
    
    result = merger.merge_documents(source_path, target_path)
    
    print("\n[SUCCESS] Semantic Matching Results:")
    for decision in result['decisions']:
        print(f"\n   Source: '{decision['source_title']}'")
        print(f"   Matched to: '{decision.get('target_title', 'N/A')}'")
        print(f"   Similarity score: {decision['similarity']:.2f}")
        print(f"   Action: {decision['action'].upper()}")
        print(f"   Reason: {decision['justification']}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SEMANTIC DOCUMENT MERGER - USAGE EXAMPLES")
    print("=" * 60)

    try:
        example_basic_merge()
        example_admp_compliance()
        example_semantic_matching()

        print("\n" + "=" * 60)
        print("[SUCCESS] All examples completed successfully!")
        print("=" * 60)
        print("\nKey Features Demonstrated:")
        print("  * Semantic section matching with similarity scoring")
        print("  * Content integration (not simple append)")
        print("  * Automatic version increment")
        print("  * Changelog generation")
        print("  * ADMP policy compliance")
        print("  * Category-based associations")
        print("\n")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
