"""
Main application entry point for vibeStation.
Launches FastAPI server and PyQt6 UI.
"""
import sys
import threading
import uvicorn
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from vibeStation.api import APIServer
from vibeStation.yaml_handler import YAMLHandler
from vibeStation.main_window import MainWindow
import yaml


class VibeStationApp:
    """Main application class."""
    
    def __init__(self):
        """Initialize the application."""
        # Load config
        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize API server
        self.api_server = APIServer(str(config_path))
        
        # Initialize YAML handler
        github_dir = self.config.get('files', {}).get('github_dir', '.github')
        instructions_file = self.config.get('files', {}).get('instructions', 'instructions.yaml')
        instructions_path = Path(github_dir) / instructions_file
        self.yaml_handler = YAMLHandler(str(instructions_path))
        
        # Server thread
        self.server_thread = None
        
    def start_api_server(self):
        """Start FastAPI server in background thread."""
        host = self.config.get('server', {}).get('host', '127.0.0.1')
        port = self.config.get('server', {}).get('port', 8765)
        
        config = uvicorn.Config(
            self.api_server.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        def run_server():
            """Run the server."""
            server.run()
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        print(f"FastAPI server started at http://{host}:{port}")
        print(f"Auth key: {self.api_server.auth_key}")
    
    def run(self):
        """Run the application."""
        # Start API server
        self.start_api_server()
        
        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("vibeStation")
        app.setOrganizationName("Vibe Coding Support Tool")
        
        # Create main window
        main_window = MainWindow(
            self.api_server,
            self.yaml_handler,
            self.config
        )
        main_window.show()
        
        # Run Qt event loop
        sys.exit(app.exec())


def main():
    """Main entry point."""
    app = VibeStationApp()
    app.run()


if __name__ == "__main__":
    main()
