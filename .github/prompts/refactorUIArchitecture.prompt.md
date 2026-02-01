---
name: refactorUIArchitecture
description: Refactor UI components to establish clear separation of concerns and eliminate responsibility duplication between main window and tab modules
argument-hint: Target files and their current inappropriate responsibilities (e.g., "TepMCP inherits from QMainWindow but should be a QWidget tab")
---

# UI Architecture Refactoring: Establish Clear Component Separation

## Problem Statement
The current UI architecture has responsibility overlaps and violations of single responsibility principle:
- `MainWindow` (parent window) and `TepMCP` (child component) both define menubar creation
- `TepMCP`, `TepDM`, and `MCPLogTab` inherit from `QMainWindow` but are embedded as tab contents in `MainWindow`
- Tab components create window-level UI elements instead of focusing on tab-specific content

## Objective
Establish a clear hierarchical architecture where:
1. **MainWindow** (sole QMainWindow): Owns all application-level concerns (menubar, window title, geometry, application lifecycle)
2. **Tab Components** (QWidget-based): Contain only tab-specific UI and logic without window-level responsibilities
3. **Clear Signal/Slot Flow**: Parent-child communication through well-defined signals and slots

## Architecture Overview

### Current (Problematic) Structure
```
MainWindow (QMainWindow)
├── TepMCP (QMainWindow) - DUPLICATE MENUBAR CREATION ❌
├── TepDM (QMainWindow) - WRONG BASE CLASS ❌
└── MCPLogTab (QWidget)
```

### Target (Correct) Structure
```
MainWindow (QMainWindow)
├── Central TabWidget (QTabWidget)
│   ├── MCPLogTab (QWidget) - Tab component
│   ├── TepMCPTab (QWidget) - Refactored from TepMCP, no menubar
│   └── TepDMTab (QWidget) - Refactored from TepDM, no menubar
├── MenuBar (owned by MainWindow only)
│   └── Settings menu with dialogs
└── Server Thread (lifecycle managed by MainWindow)
```

## Implementation Requirements

### 1. Identify and Consolidate MenuBar Definitions
- **Location**: `MainWindow.initUI()` - Currently creates Settings menu
- **Action**: Verify this is the ONLY menubar creation point
- **Remove**: Any menubar creation from `TepMCP.initUI()` or other child components
- **Consolidate**: All application-level menu items into `MainWindow.initUI()`

### 2. Refactor Component Base Classes
- **TepMCP** (currently `QMainWindow`): Change to inherit from `QWidget`
  - Remove `setWindowTitle()`, `setGeometry()`, `menuBar()` calls
  - Rename class to `TepMCPTab` or keep as `TepMCP` but clearly as a widget
  - Remove window initialization code
  
- **TepDM** (currently `QMainWindow`): Change to inherit from `QWidget`
  - Same refactoring as TepMCP
  - Rename class to `TepDMTab` if necessary for clarity
  
- **MCPLogTab**: Already `QWidget` - verify it contains only tab-specific logic

### 3. Update Constructors and Initialization
- **Tab Components**: Accept parent reference and configuration objects, NOT window-level parameters
  - Old: `TepMCP(self)` where self is MainWindow
  - New: `TepMCP(parent=None, config_file=None, github_repo_config=None, env_vars=None)`
  
- **Remove Window Management**: No `closeEvent()`, window geometry, or lifecycle management in tabs

### 4. Establish Parent-Child Communication
- **Signal Definitions**: Tab components emit signals for events that affect parent window behavior
  - Example: `server_status_changed = pyqtSignal(str)` instead of directly calling parent methods
  
- **Slot Definitions**: MainWindow provides slots to handle tab component signals
  - Example: `@pyqtSlot(str) def on_server_status_changed(self, status: str)`
  
- **Connection Points**: MainWindow.initUI() connects all signals/slots after creating tab components

### 5. Refactor ServerThread Management
- **Current Issue**: Multiple components may try to manage server lifecycle
- **Solution**: 
  - MainWindow owns ServerThread instance
  - Tab components access server state through parent signals/slots or shared reference
  - Server thread creation/destruction only in MainWindow

### 6. Configuration and Environment Variables
- **Passing Objects**: Instead of each component loading independently
  - Pass `config_file`, `github_repo_config`, `env_vars` from MainWindow to tabs
  - Reduce file I/O and configuration duplication
  
- **Storage**: Keep these as instance variables in MainWindow, accessible to tabs via `self.parent()` pattern or direct references

## Code Structure Template

### MainWindow Structure
```python
class MainWindow(QMainWindow):
    # Signals for child components to emit
    settings_changed = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        # Load configurations once
        self.config = load_config()
        self.env_vars = load_env_vars()
        self.github_config = GitHubRepositoryConfig()
        
        # Create server thread (only place)
        self.server_thread = ServerThread()
        
        self.initUI()
        self.setup_connections()
    
    def initUI(self):
        """Initialize ALL menubar and window-level UI"""
        # Create menubar here
        self.create_menubar()
        
        # Create tab widget and tabs
        self.tabs = QTabWidget()
        self.mcp_log_tab = MCPLogTab(parent=self, config=self.config)
        self.mcp_server_tab = TepMCP(parent=self, config=self.config)
        self.dm_tab = TepDM(parent=self, config=self.config)
        
        # Add to tabs
        self.tabs.addTab(self.mcp_log_tab, "Logs & Plans")
        self.tabs.addTab(self.mcp_server_tab, "Server Control")
        self.tabs.addTab(self.dm_tab, "Document Management")
    
    def create_menubar(self):
        """Single point of menubar creation"""
        menu_bar = self.menuBar()
        settings_menu = menu_bar.addMenu("Settings")
        # Add all menu items here
    
    def setup_connections(self):
        """Connect all inter-component signals/slots"""
        self.mcp_server_tab.server_started.connect(self.on_server_started)
        self.mcp_log_tab.status_changed.connect(self.on_status_changed)
```

### Tab Component Structure
```python
class TepMCP(QWidget):
    # Signals - NO window-level signals
    server_started = pyqtSignal(str)  # Emit port info to parent
    status_changed = pyqtSignal(str)
    
    def __init__(self, parent=None, config_file=None):
        super().__init__(parent)
        # NO window initialization
        self.config_file = config_file
        self.initUI()
    
    def initUI(self):
        """Create ONLY tab-specific UI"""
        layout = QVBoxLayout(self)
        # Add tab-specific widgets
        # NO menubar, NO window title, NO geometry
    
    # NO closeEvent() - parent window handles lifecycle
```

## Validation Checklist
- [ ] MainWindow is the only `QMainWindow` subclass
- [ ] All tab components inherit from `QWidget`
- [ ] Menubar created only in `MainWindow.create_menubar()` or similar
- [ ] Tab components don't call window-level methods (`setWindowTitle()`, `setGeometry()`, etc.)
- [ ] Configuration objects loaded once in MainWindow and passed to tabs
- [ ] All inter-component communication uses signals/slots
- [ ] No tab component manages server lifecycle directly
- [ ] Parent-child relationships clearly established through constructor parameters

## Testing Strategy
1. Launch MainWindow - verify menubar appears only once
2. Verify each tab initializes correctly without duplicate window decorations
3. Test signal connections between components
4. Verify server lifecycle management from MainWindow only
5. Test configuration changes propagate to all tabs correctly

---

**Keywords**: UI refactoring, separation of concerns, single responsibility principle, PyQt6 architecture, parent-child components, signal-slot pattern
