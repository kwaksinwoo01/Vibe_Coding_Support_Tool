# Common Module

Shared UI components and utilities used across the vibeStation application.

## Components

### Dialogs (`dialogs.py`)
- **GitHubTokenHelpDialog**: Help dialog showing instructions for creating GitHub Personal Access Tokens

### Configuration Management (`config_manager.py`)
- **load_env_config()**: Load configuration from environment variables
- **save_env_config()**: Save configuration to .env file
- **load_config()**: Load configuration from JSON file
- **save_config()**: Save configuration to JSON file

### Log Display (`log_display.py`)
- **LogDisplayWidget**: PyQt6 widget for displaying tier-based logs with filtering capabilities

### Server Thread (`server_thread.py`)
- **ServerThread**: FastAPI server thread for receiving log data via HTTP POST
- Runs on port 18989 by default
- Receives logs from MCP agents and emits signals to UI

## Usage Examples

### Using the Log Display Widget
```python
from common.log_display import LogDisplayWidget

# In your PyQt6 window
self.log_display = LogDisplayWidget()
layout.addWidget(self.log_display)

# Add logs
self.log_display.add_log("A", "Planning task started")
self.log_display.add_log("B", "Executing subtask 1")
```

### Using the Server Thread
```python
from common.server_thread import ServerThread

# Create and start server
self.server_thread = ServerThread()
self.server_thread.received.connect(self.handle_log)
self.server_thread.start()

def handle_log(self, data):
    # data contains: {'tier': 'A', 'msg': '...', 'status': '...'}
    self.log_display.add_log(data['tier'], data['msg'])
```

### Using Configuration Functions
```python
from common.config_manager import load_config, save_config
from pathlib import Path

# Load from JSON
config_file = Path("config/settings.json")
config = load_config(config_file)

# Save to JSON
save_config(config, config_file)
```

### Using the GitHub Token Help Dialog
```python
from common.dialogs import GitHubTokenHelpDialog

# Show help dialog
help_dialog = GitHubTokenHelpDialog(parent=self)
help_dialog.exec()
```

## Dependencies

- PyQt6 (for UI components)
- FastAPI (for ServerThread)
- uvicorn (for ServerThread)
- pydantic (for ServerThread)
- python-dotenv (for config_manager)

## Integration

This module is designed to be imported by:
- `installer/` - Setup and installation wizards
- `vibeStation_monitor/` - Monitoring and control interfaces
- Any other modules that need shared UI components

## Notes

- The ServerThread uses port 18989 for receiving logs
- LogDisplayWidget supports tiers: A, B, C, D, E, F with color coding
- All configuration functions handle errors gracefully and return empty dict on failure
