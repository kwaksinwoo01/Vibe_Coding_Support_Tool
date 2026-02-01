"""
Main application entry point for vibeStation Setup.
Launches PyQt6 UI for copilot-instructions creation and editing.
"""
import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from yaml_handler import YAMLHandler
import yaml
from ui.main_window import MainWindow

class VibeStationSetupApp:
    """Setup application class for copilot-instructions management."""

    def __init__(self):
        """Initialize the application."""
        # Load config
        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        # Initialize YAML handler
        github_dir = self.config.get('files', {}).get('github_dir', '.github')
        instructions_file = self.config.get('files', {}).get('instructions', 'instructions.yaml')
        instructions_path = Path(github_dir) / instructions_file
        self.yaml_handler = YAMLHandler(str(instructions_path))

    def run(self):
        """Run the application."""
        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("vibeStation Setup")
        app.setOrganizationName("Vibe Coding Support Tool")

        # Create main window (setup-only version)
        main_window = MainWindow(
            None,  # No API server for setup
            self.yaml_handler,
            self.config
        )
        main_window.show()

        # Run Qt event loop
        sys.exit(app.exec())


def main():
    """Main entry point."""
    app = VibeStationSetupApp()
    app.run()


if __name__ == "__main__":
    main()