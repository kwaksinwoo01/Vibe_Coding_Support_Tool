#!/usr/bin/env python3
"""
Test script for vibeStation components.
Run this to verify the installation.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


def test_yaml_handler():
    """Test YAML handler functionality."""
    print("Testing YAML handler...")
    from vibeStation.yaml_handler import YAMLHandler
    
    handler = YAMLHandler('.github/instructions.yaml')
    
    # Test read
    data = handler.read()
    assert 'version' in data, "YAML read failed"
    print("  ✓ Read YAML file")
    
    # Test validation
    assert handler.validate_structure(), "YAML structure invalid"
    print("  ✓ Validate structure")
    
    print("✓ YAML handler tests passed\n")


def test_api_server():
    """Test API server functionality."""
    print("Testing API server...")
    from vibeStation.api import APIServer, LogEntry
    
    server = APIServer('vibeStation/config.yaml')
    assert server.auth_key, "Auth key not generated"
    print("  ✓ Server initialized")
    
    # Test log entry
    log = LogEntry(tier='A', message='Test message')
    assert log.tier == 'A', "Log entry creation failed"
    print("  ✓ Log entry creation")
    
    # Test log buffer
    server.log_buffer.append(log)
    logs = server.get_logs()
    assert len(logs) == 1, "Log buffer failed"
    print("  ✓ Log buffer")
    
    print("✓ API server tests passed\n")


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from vibeStation.yaml_handler import YAMLHandler
        print("  ✓ yaml_handler")
        
        from vibeStation.api import APIServer
        print("  ✓ api")
        
        # PyQt6 import might fail in headless environment
        try:
            from vibeStation.main_window import MainWindow
            print("  ✓ main_window")
            pyqt6_available = True
        except ImportError as e:
            print(f"  ⚠ main_window (PyQt6 not available: {e})")
            pyqt6_available = False
        
        try:
            from vibeStation.app import VibeStationApp
            print("  ✓ app")
        except ImportError as e:
            if not pyqt6_available:
                print(f"  ⚠ app (PyQt6 not available)")
            else:
                raise
        
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False
    
    print("✓ Import tests passed\n")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("vibeStation Component Tests")
    print("=" * 60)
    print()
    
    try:
        test_imports()
        test_yaml_handler()
        test_api_server()
        
        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        print()
        print("You can now run the application with:")
        print("  python run_vibestation.py")
        print()
        return 0
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ Tests failed: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
