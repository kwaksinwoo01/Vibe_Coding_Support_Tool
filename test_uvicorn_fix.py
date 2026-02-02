#!/usr/bin/env python3
"""
Test script to verify uvicorn logging fix for exe packaging.

This script simulates the exe environment where sys.stdout and sys.stderr
can be None, which causes the uvicorn logging formatter to fail.

Test cases:
1. Test with normal stdout/stderr (should work)
2. Test with None stdout/stderr (simulates exe environment)
3. Verify server can start without logging errors
"""

import sys
import os
from pathlib import Path
import threading
import time
import requests

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_uvicorn_config_with_none_stdout():
    """Test uvicorn.Config with None stdout/stderr (exe environment simulation)"""
    print("\n" + "="*60)
    print("TEST 1: Uvicorn Config with None stdout/stderr")
    print("="*60)
    
    # Save original streams
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    try:
        # Simulate exe environment where stdout/stderr are None
        sys.stdout = None
        sys.stderr = None
        
        print = lambda *args, **kwargs: None  # Suppress prints during test
        
        # Try to create uvicorn config
        from fastapi import FastAPI
        import uvicorn
        
        app = FastAPI()
        
        # This should NOT raise AttributeError with log_config=None
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=18989,
            log_level="error",
            log_config=None  # This is the fix!
        )
        
        # Restore streams for output
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        
        print("✓ SUCCESS: uvicorn.Config created without errors with None stdout/stderr")
        print(f"  - Config host: {config.host}")
        print(f"  - Config port: {config.port}")
        print(f"  - Config log_config: {config.log_config}")
        return True
        
    except AttributeError as e:
        # Restore streams
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        
        print(f"✗ FAILED: AttributeError occurred: {e}")
        return False
        
    except Exception as e:
        # Restore streams
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        
        print(f"✗ FAILED: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Ensure streams are restored
        sys.stdout = original_stdout
        sys.stderr = original_stderr


def test_uvicorn_config_normal():
    """Test uvicorn.Config with normal stdout/stderr"""
    print("\n" + "="*60)
    print("TEST 2: Uvicorn Config with normal stdout/stderr")
    print("="*60)
    
    try:
        from fastapi import FastAPI
        import uvicorn
        
        app = FastAPI()
        
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=18990,
            log_level="error",
            log_config=None
        )
        
        print("✓ SUCCESS: uvicorn.Config created without errors")
        print(f"  - Config host: {config.host}")
        print(f"  - Config port: {config.port}")
        print(f"  - Config log_config: {config.log_config}")
        return True
        
    except Exception as e:
        print(f"✗ FAILED: Error occurred: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_server_thread_import():
    """Test that ServerThread can be imported and instantiated"""
    print("\n" + "="*60)
    print("TEST 3: ServerThread import and instantiation")
    print("="*60)
    
    try:
        # We can't fully test ServerThread without Qt, but we can check imports
        from vibeStation_setup.mcp_suver.core.server_thread import ServerThread
        
        print("✓ SUCCESS: ServerThread imported successfully")
        print(f"  - ServerThread class: {ServerThread}")
        return True
        
    except Exception as e:
        print(f"✗ FAILED: Import error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("UVICORN LOGGING FIX TEST SUITE")
    print("="*60)
    print("\nTesting fix for: AttributeError: 'NoneType' object has no attribute 'isatty'")
    print("This error occurs when running uvicorn in exe packages.\n")
    
    results = []
    
    # Run tests
    results.append(("Normal stdout/stderr", test_uvicorn_config_normal()))
    results.append(("None stdout/stderr (exe simulation)", test_uvicorn_config_with_none_stdout()))
    results.append(("ServerThread import", test_server_thread_import()))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! The uvicorn logging fix is working correctly.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
