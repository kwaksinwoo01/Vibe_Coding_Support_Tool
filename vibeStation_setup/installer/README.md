# Installer Module

Initial setup and configuration wizard for vibeStation.

## Purpose

This module contains UI components for the installation and setup process, helping users create and configure the `copilot-instructions.md` file that GitHub Copilot uses for project-specific guidance.

## Components

### InstructionsEditorWidget
Editor widget for viewing and modifying `copilot-instructions.md` files.

**Features**:
- Load and save instructions files
- Validate file format
- Format document structure
- Create backups automatically

**Usage**:
```python
from installer.main_window import InstructionsEditorWidget

editor = InstructionsEditorWidget(yaml_handler, parent=self)
layout.addWidget(editor)
```

### SetupWizardWidget
Interactive setup wizard that guides users through creating a `copilot-instructions.md` file.

**Sections**:
1. **Program Information**: Name, description, purpose
2. **Coding Settings**: Language, architecture patterns
3. **Document Settings**: Work plan paths
4. **Advanced Settings**: Compatibility rules, design patterns

**Features**:
- Step-by-step configuration
- Template-based file generation
- Input validation
- Default values based on project structure

**Usage**:
```python
from installer.main_window import SetupWizardWidget

wizard = SetupWizardWidget(parent=self)
wizard.setup_completed.connect(self.on_setup_completed)
layout.addWidget(wizard)
```

## Integration

This module is used by:
- `vibeStation_setup/main_window.py` - Main setup application window
- `vibeStation_setup/app.py` - Application entry point

## File Generation

The wizard generates `copilot-instructions.md` files using the template from:
- `vibeStation_setup/copilot-instructions.format.md`

Generated files are placed in:
- `.github/copilot-instructions.md`

## Dependencies

- PyQt6 (for UI widgets)
- yaml (for YAML handling)
- datetime, pathlib (for file operations)

## Workflow

1. User launches vibeStation Setup application
2. If no `copilot-instructions.md` exists:
   - SetupWizardWidget is displayed
   - User fills in project information
   - File is generated from template
3. If file exists:
   - User can choose to keep, modify, or recreate
   - InstructionsEditorWidget allows manual editing

## Notes

- Automatically creates backups before overwriting files
- Supports Korean and English interfaces
- Validates required sections in instructions files
- Generates project-specific configurations based on user input
