# Monitor Module

Real-time monitoring and control interface for vibeStation MCP agents.

## Purpose

This module provides a comprehensive monitoring and control interface for the MCP (Model Context Protocol) server and AI coding agents. It displays real-time logs, manages server settings, and provides GitHub repository integration.

## Components

### VibeStationMonitor
Main application window for monitoring AI coding agents.

**Features**:
- Real-time tier-based log display
- Status indicators for agent activities
- Server control and management
- GitHub repository configuration
- Redis command execution
- Terminal command interface

**Usage**:
```python
from vibeStation_monitor.main_window import VibeStationMonitor

app = QApplication(sys.argv)
monitor = VibeStationMonitor()
monitor.show()
sys.exit(app.exec())
```

### SettingsDialog
Configuration dialog for GitHub repository connections and server settings.

**Features**:
- GitHub repository configuration (HTTPS, SSH, CLI formats)
- GitHub Personal Access Token management
- Branch selection
- Main document path configuration
- Redis connection settings
- Agent path configuration

**Tabs**:
1. **GitHub Repository**: Repository connection and token settings
2. **Server Settings**: Redis, agent paths, and server configuration

**Usage**:
```python
from vibeStation_monitor.main_window import SettingsDialog
from common.config_manager import load_config

config_file = Path("config/monitor_config.json")
github_config = GitHubRepositoryConfig()

dialog = SettingsDialog(self, config_file, github_config, env_vars)
dialog.exec()
```

## Architecture

```
VibeStationMonitor (Main Window)
├── LogDisplayWidget (from common/)
│   ├── Tier filtering (A-F)
│   ├── Time-stamped entries
│   └── Color-coded display
├── SettingsDialog
│   ├── GitHub tab
│   └── Server tab
└── Status indicators
```

## Log Tiers

The monitor supports the following tier classification:
- **Tier A (기획)**: Planning - Red
- **Tier B (수행)**: Execution - Yellow  
- **Tier C (수정)**: Modification - Blue
- **Tier D (분석)**: Analysis - Green
- **Tier E (관리)**: Management - Gray
- **Tier F (기타)**: Other - Cyan

## Integration

### With Common Module
- `LogDisplayWidget`: Log display widget
- `ServerThread`: FastAPI server for receiving logs
- `GitHubTokenHelpDialog`: Token generation help
- `load_config`, `save_config`: Configuration management

### With MCP Server Core
- `GitHubRepositoryConfig`: Repository configuration utilities
- Server control and status monitoring

## Entry Points

### Main Application (`app.py`)
Simple monitoring interface with log display:
```bash
python vibeStation_monitor/app.py
```

### Full Application (`main_window.py` via MCP_server.py)
Complete monitoring and control interface:
```bash
python mcp_suver/MCP_server.py
```

## Configuration Files

- **Monitor Config**: `vibeStation_monitor/config/monitor_config.json`
  - GitHub token
  - Repository settings
  - Server configuration
  
- **Log Files**: `vibeStation_monitor/logs/monitor_YYYYMMDD_HHMMSS.log`

## Dependencies

- PyQt6 (for UI)
- Common module components
- MCP server core utilities
- httpx (for HTTP requests)
- subprocess, socket (for system operations)

## Features

### GitHub Repository Management
- Auto-detect repository type (HTTPS, SSH, CLI)
- Parse owner and repository name
- Fetch available branches
- Validate repository access
- Token-based authentication

### Server Control
- Start/stop MCP server
- Monitor server status
- View server logs
- Execute Redis commands
- Run terminal commands
- Test agent execution

### Log Monitoring
- Real-time log streaming via FastAPI
- Tier-based filtering
- Timestamp tracking
- Color-coded status
- Log persistence and export

## Notes

- Default monitor port: 18989 (configurable)
- Supports Korean and English interfaces
- Auto-saves configuration on changes
- Provides comprehensive error handling
- Includes GitHub token generation guide
