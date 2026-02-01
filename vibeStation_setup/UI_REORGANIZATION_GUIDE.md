# UI Module Reorganization - Migration Guide

## Overview

The vibeStation UI components have been reorganized by role to improve maintainability and separation of concerns. This document explains the new structure and how to migrate any existing code.

## New Module Structure

```
vibeStation_setup/
├── installer/                    # Installation & Setup Module
│   ├── __init__.py
│   └── main_window.py           # SetupWizardWidget, InstructionsEditorWidget
│
├── vibeStation_monitor/          # Monitoring Module
│   ├── __init__.py
│   ├── app.py                   # Monitor application entry point
│   └── main_window.py           # VibeStationMonitor, SettingsDialog
│
├── common/                       # Shared Components
│   ├── __init__.py
│   ├── dialogs.py               # GitHubTokenHelpDialog
│   ├── config_manager.py        # load_config(), save_config()
│   ├── log_display.py           # LogDisplayWidget
│   └── server_thread.py         # ServerThread (for monitoring)
│
├── mcp_suver/                    # MCP Server Core Engine
│   └── MCP_server.py            # ServerThread, GitHubRepositoryConfig
│                                # (UI components removed - now pure engine)
│
├── main_window.py               # Setup MainWindow (imports from installer/)
└── app.py                       # Setup application entry point
```

## Module Roles

### 1. Installer Module (`installer/`)
**Purpose**: Initial setup and configuration wizard

**Components**:
- `SetupWizardWidget`: Initial setup wizard for creating copilot-instructions.md
- `InstructionsEditorWidget`: Editor for modifying copilot-instructions.md

**Usage**:
```python
from ui.tab_dm import SetupWizardWidget, InstructionsEditorWidget
```

### 2. Monitor Module (`vibeStation_monitor/`)
**Purpose**: Real-time log monitoring and system control

**Components**:
- `VibeStationMonitor`: Main monitoring application window
- `SettingsDialog`: Configuration dialog for GitHub repos and server settings

**Usage**:
```python
from vibeStation_monitor.main_window import VibeStationMonitor, SettingsDialog
```

### 3. Common Module (`common/`)
**Purpose**: Shared utilities and UI components

**Components**:
- `GitHubTokenHelpDialog`: Help dialog for GitHub token generation
- `LogDisplayWidget`: Tier-based log display widget
- `ServerThread`: FastAPI server thread for log monitoring
- `load_config()`, `save_config()`: Configuration management functions

**Usage**:
```python
from common.dialogs import GitHubTokenHelpDialog
from common.log_display import LogDisplayWidget
from common.server_thread import ServerThread
from common.config_manager import load_config, save_config
```

### 4. MCP Server Core (`mcp_suver/MCP_server.py`)
**Purpose**: Core MCP server engine (NO UI)

**Components** (Core only):
- `ServerThread`: FastAPI + SSE + Redis server thread
- `GitHubRepositoryConfig`: Repository configuration utilities
- Helper functions: `find_available_port()`, `check_redis_connection()`, etc.

**Removed** (moved to other modules):
- ~~`GitHubTokenHelpDialog`~~ → `common/dialogs.py`
- ~~`SettingsDialog`~~ → `vibeStation_monitor/main_window.py`
- ~~`MCPServerApp`~~ → `vibeStation_monitor/main_window.py`

**Usage**:
```python
from mcp_suver.MCP_server import ServerThread, GitHubRepositoryConfig
```

## Migration Instructions

### If you were importing from `MCP_server.py`:

**Before:**
```python
from mcp_suver.MCP_server import (
    GitHubTokenHelpDialog,
    SettingsDialog,
    MCPServerApp
)
```

**After:**
```python
from common.dialogs import GitHubTokenHelpDialog
from vibeStation_monitor.main_window import SettingsDialog, VibeStationMonitor
```

### If you were importing from `vibeStation_monitor/main_window.py`:

**Before:**
```python
# Old duplicate classes
from vibeStation_monitor.main_window import (
    ServerThread,
    LogDisplayWidget,
    VibeStation
)
```

**After:**
```python
from common.server_thread import ServerThread
from common.log_display import LogDisplayWidget
from vibeStation_monitor.main_window import VibeStationMonitor
```

### If you were importing from `main_window.py`:

**Before:**
```python
from main_window import (
    InstructionsEditorWidget,
    SetupWizardWidget,
    MainWindow
)
```

**After:**
```python
from ui.tab_dm import InstructionsEditorWidget, SetupWizardWidget
from main_window import MainWindow  # Still in same location
```

## Benefits

1. **Clear Separation of Concerns**: Each module has a well-defined purpose
2. **Reduced Code Duplication**: Common components are now shared
3. **Improved Maintainability**: Changes to shared components only need to be made once
4. **Better Testability**: Modules can be tested independently
5. **Cleaner Dependencies**: UI and core engine are properly separated

## File Size Reductions

- `MCP_server.py`: 1,854 lines → 852 lines (54% reduction)
- `main_window.py`: 1,103 lines → 520 lines (53% reduction)
- `vibeStation_monitor/app.py`: 207 lines → 68 lines (67% reduction)

## Testing

Each module can now be tested independently:

```bash
# Test installer module
python -c "from ui.tab_dm import SetupWizardWidget"

# Test monitor module  
python -c "from vibeStation_monitor.main_window import VibeStationMonitor"

# Test common components
python -c "from common.dialogs import GitHubTokenHelpDialog"

# Test MCP server core
python -c "from mcp_suver.MCP_server import ServerThread"
```

## Notes

- All modules maintain backward compatibility where possible
- The `MainWindow` class in `vibeStation_setup/main_window.py` now imports components from the installer module
- No functionality has been removed, only reorganized
- UI components are now properly separated from core engine logic

## Questions or Issues?

If you encounter any import errors or issues after this reorganization, please check:
1. Update your import statements according to this guide
2. Ensure you're importing from the correct new module
3. Check that common components are imported from the `common/` module
