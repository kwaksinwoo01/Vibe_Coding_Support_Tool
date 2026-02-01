# Module Architecture

## Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│                      User Entry Points                       │
└─────────────────────────────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │ Monitoring  │  │   Setup     │  │  Monitor    │
    │    .py      │  │   Wizard    │  │   Window    │
    │  (Legacy)   │  │             │  │   (Main)    │
    └─────────────┘  └─────────────┘  └─────────────┘
          │                │                 │
          └────────────────┴─────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │  vibeStation_monitor/  │
              │    main_window.py      │
              │   (VibeStation UI)     │
              └────────────────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
                ▼                     ▼
       ┌────────────────┐    ┌────────────────┐
       │   mcp_suver/   │    │    common/     │
       │ MCP_server.py  │    │config_manager  │
       │ (ServerThread) │    │   dialogs      │
       └────────────────┘    └────────────────┘
                │                     │
                ▼                     ▼
        ┌──────────────┐      ┌──────────────┐
        │   FastAPI    │      │   Settings   │
        │   Server     │      │   Storage    │
        └──────────────┘      └──────────────┘
```

## Module Dependencies

### vibeStation_monitor/main_window.py
- **Imports from**:
  - `mcp_suver.MCP_server` (ServerThread)
  - `common.config_manager` (save_instruction)
  - `PyQt6.QtWidgets`, `PyQt6.QtCore`
- **Provides**: VibeStation (main monitoring UI)
- **No dependencies on**: vibeStation_setup

### mcp_suver/MCP_server.py
- **Imports from**:
  - `fastapi`, `uvicorn`, `pydantic`
  - `PyQt6.QtCore` (QThread, pyqtSignal)
- **Provides**: ServerThread, FastAPI app, CommSignal
- **No dependencies on**: UI modules (clean separation)

### common/config_manager.py
- **Imports from**: `pathlib`, `typing`
- **Provides**: Configuration utilities
- **No dependencies on**: Any other project modules (pure utility)

### common/dialogs.py
- **Imports from**: `PyQt6.QtWidgets`
- **Provides**: GitHubTokenHelpDialog, SettingsDialog
- **No dependencies on**: Other project modules

### vibeStation_setup/installer/main_window.py
- **Imports from**: `PyQt6.QtWidgets`
- **Provides**: SetupWizardWidget
- **No dependencies on**: Other modules (independent setup flow)

## Circular Import Prevention

✅ **No circular dependencies detected**

- Server module has no UI dependencies
- Common utilities are independent
- UI modules only import from server/common (one-way dependency)
- Setup module is completely independent

## Key Design Decisions

1. **Unidirectional Data Flow**
   - UI → Server (imports and uses)
   - Server ← UI (signals/events only)

2. **Clean Separation**
   - Server engine has no UI code
   - UI code isolated in monitor/setup modules
   - Common utilities are pure functions

3. **Backward Compatibility**
   - Legacy Monitoring.py maintained as wrapper
   - Old import paths still work

4. **Module Independence**
   - Each module can be tested independently
   - Setup wizard doesn't depend on monitor
   - Common utilities are reusable
