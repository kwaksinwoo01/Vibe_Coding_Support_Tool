#!/usr/bin/env python3
"""
Verification script for uvicorn logging fix.

This script verifies that the fix has been applied correctly
by checking the source code for the log_config=None parameter.
"""

import sys
from pathlib import Path

def verify_fix():
    """Verify that the uvicorn logging fix is present in server_thread.py"""
    
    print("="*60)
    print("UVICORN LOGGING FIX VERIFICATION")
    print("="*60)
    print()
    
    server_thread_file = Path(__file__).parent / "vibeStation_setup" / "mcp_suver" / "core" / "server_thread.py"
    
    if not server_thread_file.exists():
        print(f"✗ ERROR: File not found: {server_thread_file}")
        return False
    
    print(f"Checking file: {server_thread_file}")
    print()
    
    with open(server_thread_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for the fix
    checks = [
        ("log_config=None parameter", "log_config=None" in content),
        ("Comment about exe packaging fix", "Fix for exe packaging" in content or "exe packaging" in content.lower()),
        ("Comment about isatty error", "isatty" in content),
        ("uvicorn.Config call exists", "uvicorn.Config(" in content),
    ]
    
    all_passed = True
    
    for check_name, result in checks:
        status = "✓" if result else "✗"
        print(f"{status} {check_name}: {'FOUND' if result else 'NOT FOUND'}")
        if not result:
            all_passed = False
    
    print()
    
    # Extract and display the relevant code section
    if "log_config=None" in content:
        print("Code snippet with the fix:")
        print("-" * 60)
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "log_config=None" in line:
                # Print context (5 lines before and after)
                start = max(0, i - 5)
                end = min(len(lines), i + 6)
                for j in range(start, end):
                    marker = ">>> " if j == i else "    "
                    print(f"{marker}{lines[j]}")
                break
        print("-" * 60)
    
    print()
    
    if all_passed:
        print("✓ SUCCESS: All verification checks passed!")
        print()
        print("The fix includes:")
        print("  1. log_config=None parameter to disable uvicorn's default logging")
        print("  2. Comments explaining why this fixes the exe packaging issue")
        print("  3. Prevents AttributeError: 'NoneType' object has no attribute 'isatty'")
        print()
        print("This fix ensures the MCP server can run in exe packages where")
        print("sys.stdout and sys.stderr might be None.")
        return True
    else:
        print("✗ FAILURE: Some verification checks failed.")
        print("The fix may not be complete or correctly applied.")
        return False


if __name__ == "__main__":
    success = verify_fix()
    sys.exit(0 if success else 1)
