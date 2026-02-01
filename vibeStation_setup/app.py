"""
Main application entry point for vibeStation Setup.
Launches PyQt6 UI for copilot-instructions creation and editing.
"""
import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Add parent directory to path for imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

from ui.main_window import MainWindow


class VibeStationSetupApp:
    """Setup application class for copilot-instructions management."""

    def run(self):
        """Run the application."""
        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("vibeStation Setup")
        app.setOrganizationName("Vibe Coding Support Tool")

        # Create main window
        main_window = MainWindow()
        main_window.show()

        # Run Qt event loop
        sys.exit(app.exec())


def main():
    """Main entry point."""
    app = VibeStationSetupApp()
    app.run()


if __name__ == "__main__":
    main()