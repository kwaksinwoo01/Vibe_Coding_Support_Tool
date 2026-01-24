"""
vibeStation - Vibe Coding Support Tool
A PyQt6+FastAPI application for editing and monitoring .github instructions.
"""

__version__ = "1.0.0"
__author__ = "Vibe Coding Support Tool"

# Lazy imports to avoid PyQt6 dependency issues
__all__ = [
    'VibeStationApp',
    'main',
    'APIServer',
    'LogEntry',
    'YAMLHandler',
    'MainWindow'
]

def __getattr__(name):
    """Lazy import to avoid loading PyQt6 unless needed."""
    if name == 'VibeStationApp' or name == 'main':
        from .app import VibeStationApp, main
        return VibeStationApp if name == 'VibeStationApp' else main
    elif name == 'APIServer' or name == 'LogEntry':
        from .api import APIServer, LogEntry
        return APIServer if name == 'APIServer' else LogEntry
    elif name == 'YAMLHandler':
        from .yaml_handler import YAMLHandler
        return YAMLHandler
    elif name == 'MainWindow':
        from .main_window import MainWindow
        return MainWindow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
