"""
PyQt6 Main Window for vibeStation Setup.
Provides UI for creating and editing copilot-instructions.md files.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QPushButton, QTabWidget,
    QMessageBox, QFileDialog, QSplitter, QLineEdit,QComboBox,
    QScrollArea, QGroupBox, QFormLayout, QDialog,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from PyQt6 import uic
from datetime import datetime
from pathlib import Path
import yaml


class InstructionsEditorWidget(QWidget):
    """Widget for editing copilot-instructions.md file."""

    save_requested = pyqtSignal(str)

    def __init__(self, yaml_handler, parent=None):
        super().__init__(parent)
        self.yaml_handler = yaml_handler
        self.init_ui()
        self.load_instructions_content()

    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # Toolbar
        toolbar = QHBoxLayout()

        self.save_btn = QPushButton("💾 Save Instructions")
        self.save_btn.clicked.connect(self.save_instructions_content)
        toolbar.addWidget(self.save_btn)

        self.reload_btn = QPushButton("🔄 Reload")
        self.reload_btn.clicked.connect(self.load_instructions_content)
        toolbar.addWidget(self.reload_btn)

        self.validate_btn = QPushButton("✓ Validate Format")
        self.validate_btn.clicked.connect(self.validate_instructions)
        toolbar.addWidget(self.validate_btn)

        self.format_btn = QPushButton("🎨 Format Document")
        self.format_btn.clicked.connect(self.format_instructions)
        toolbar.addWidget(self.format_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Status label
        self.status_label = QLabel("Ready - copilot-instructions.md editor")
        layout.addWidget(self.status_label)

        # Editor
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 10))
        layout.addWidget(self.editor)

    def load_instructions_content(self):
        """Load copilot-instructions.md content from file."""
        try:
            instructions_path = Path(".github") / "copilot-instructions.md"
            if instructions_path.exists():
                with open(instructions_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.editor.setPlainText(content)
                self.status_label.setText(f"Loaded: {instructions_path}")
            else:
                self.status_label.setText("No copilot-instructions.md file found")
                self.editor.setPlainText("# GitHub Copilot Instructions\n\nPlease create instructions file first.")

        except Exception as e:
            QMessageBox.warning(self, "Load Error", f"Failed to load instructions file:\n{str(e)}")

    def save_instructions_content(self):
        """Save copilot-instructions.md content to file."""
        try:
            content = self.editor.toPlainText()
            instructions_path = Path(".github") / "copilot-instructions.md"
            instructions_path.parent.mkdir(parents=True, exist_ok=True)

            with open(instructions_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.status_label.setText(f"Saved: {instructions_path}")
            QMessageBox.information(self, "Save Success", "Instructions file saved successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save instructions file:\n{str(e)}")

    def validate_instructions(self):
        """Validate instructions file format."""
        try:
            content = self.editor.toPlainText()
            # Basic validation - check for required sections
            required_sections = [
                "## 📌 Quick Start",
                "## 📦 Entry Points",
                "## 🏗️ Architecture Patterns",
                "## 🔧 Required Setup"
            ]

            missing_sections = []
            for section in required_sections:
                if section not in content:
                    missing_sections.append(section)

            if missing_sections:
                QMessageBox.warning(
                    self,
                    "Validation Warning",
                    f"Missing required sections:\n" + "\n".join(missing_sections)
                )
            else:
                QMessageBox.information(self, "Validation Success", "Instructions file format is valid!")

        except Exception as e:
            QMessageBox.critical(self, "Validation Error", f"Failed to validate instructions:\n{str(e)}")

    def format_instructions(self):
        """Format the instructions document."""
        try:
            content = self.editor.toPlainText()
            # Basic formatting - ensure consistent line endings and spacing
            formatted_content = content.replace('\r\n', '\n').replace('\r', '\n')
            # Remove excessive blank lines
            import re
            formatted_content = re.sub(r'\n\n\n+', '\n\n', formatted_content)

            self.editor.setPlainText(formatted_content)
            self.status_label.setText("Document formatted")

        except Exception as e:
            QMessageBox.critical(self, "Format Error", f"Failed to format document:\n{str(e)}")
    
    save_requested = pyqtSignal(str)
    
    def __init__(self, yaml_handler, parent=None):
        super().__init__(parent)
        self.yaml_handler = yaml_handler
        self.init_ui()
        self.load_content()
        
    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.save_btn = QPushButton("💾 Save")
        self.save_btn.clicked.connect(self.save_content)
        toolbar.addWidget(self.save_btn)
        
        self.reload_btn = QPushButton("🔄 Reload")
        self.reload_btn.clicked.connect(self.load_content)
        toolbar.addWidget(self.reload_btn)
        
        self.validate_btn = QPushButton("✓ Validate")
        self.validate_btn.clicked.connect(self.validate_yaml)
        toolbar.addWidget(self.validate_btn)
        
        self.backup_btn = QPushButton("📋 Backups")
        self.backup_btn.clicked.connect(self.show_backups)
        toolbar.addWidget(self.backup_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Editor
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 10))
        layout.addWidget(self.editor)
        
    def load_content(self):
        """Load YAML content from file."""
        try:
            data = self.yaml_handler.read()
            yaml_text = yaml.dump(data, allow_unicode=True, sort_keys=False, indent=2)
            self.editor.setPlainText(yaml_text)
            self.status_label.setText("✓ Loaded successfully")
            self.status_label.setStyleSheet("color: green")
        except Exception as e:
            self.status_label.setText(f"✗ Error loading: {e}")
            self.status_label.setStyleSheet("color: red")
    
    def save_content(self):
        """Save YAML content to file."""
        try:
            # Parse YAML
            yaml_text = self.editor.toPlainText()
            data = yaml.safe_load(yaml_text)
            
            # Save using YAML handler (with backup)
            self.yaml_handler.write(data, create_backup=True)
            
            self.status_label.setText("✓ Saved successfully (backup created)")
            self.status_label.setStyleSheet("color: green")
            
            QMessageBox.information(self, "Success", "Instructions saved successfully!")
            
        except yaml.YAMLError as e:
            self.status_label.setText(f"✗ Invalid YAML: {e}")
            self.status_label.setStyleSheet("color: red")
            QMessageBox.warning(self, "YAML Error", f"Invalid YAML format:\n{e}")
        except Exception as e:
            self.status_label.setText(f"✗ Save error: {e}")
            self.status_label.setStyleSheet("color: red")
            QMessageBox.critical(self, "Error", f"Failed to save:\n{e}")
    
    def validate_yaml(self):
        """Validate YAML syntax."""
        try:
            yaml_text = self.editor.toPlainText()
            yaml.safe_load(yaml_text)
            self.status_label.setText("✓ YAML is valid")
            self.status_label.setStyleSheet("color: green")
            QMessageBox.information(self, "Validation", "YAML syntax is valid!")
        except yaml.YAMLError as e:
            self.status_label.setText(f"✗ Invalid YAML")
            self.status_label.setStyleSheet("color: red")
            QMessageBox.warning(self, "Validation Error", f"Invalid YAML:\n{e}")
    
    def show_backups(self):
        """Show available backups."""
        backups = self.yaml_handler.get_backups()
        
        if not backups:
            QMessageBox.information(self, "Backups", "No backups found.")
            return
        
        backup_list = "\n".join([f"• {b.name}" for b in backups[:10]])
        msg = f"Available backups (showing recent 10):\n\n{backup_list}"
        QMessageBox.information(self, "Backups", msg)


class SetupWizardWidget(QWidget):
    """Widget for initial setup wizard to create copilot-instructions.md"""
    
    setup_completed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize the setup wizard UI."""
        # Main layout with scroll area
        main_layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("vibeStation 초기 설정 마법사")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        subtitle = QLabel("GitHub Copilot Instructions 파일을 생성하기 위한 설정을 입력해주세요.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle)
        
        # Scroll area for form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        form_widget = QWidget()
        self.form_layout = QVBoxLayout(form_widget)
        
        # Section 1: 프로그램 기본 정보
        self.create_program_info_section()
        
        # Section 2: 코딩 설정
        self.create_coding_settings_section()
        
        # Section 3: 문서 설정
        self.create_document_settings_section()
        
        # Section 4: 고급 설정
        self.create_advanced_settings_section()
        
        # Complete button
        self.complete_btn = QPushButton("설정 완료 및 파일 생성")
        self.complete_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.complete_btn.setStyleSheet("background-color: #28a745; color: white; padding: 10px;")
        self.complete_btn.clicked.connect(self.on_complete)
        self.form_layout.addWidget(self.complete_btn)
        
        scroll.setWidget(form_widget)
        main_layout.addWidget(scroll)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)
    
    def create_program_info_section(self):
        """Create program information section."""
        group = QGroupBox("프로그램 기본 정보")
        group.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout = QFormLayout()
        
        # 프로그램 이름
        self.project_name_edit = QLineEdit()
        self.project_name_edit.setPlaceholderText("예: My Awesome App")
        layout.addRow("프로그램 이름:", self.project_name_edit)
        
        # 프로그램 설명
        self.project_desc_edit = QTextEdit()
        self.project_desc_edit.setMaximumHeight(60)
        self.project_desc_edit.setPlaceholderText("프로그램의 주요 기능과 특징을 설명해주세요.")
        layout.addRow("프로그램 설명:", self.project_desc_edit)
        
        # 프로그램 목적
        self.project_purpose_edit = QTextEdit()
        self.project_purpose_edit.setMaximumHeight(60)
        self.project_purpose_edit.setPlaceholderText("프로그램의 개발 목적과 목표를 설명해주세요.")
        layout.addRow("프로그램 목적:", self.project_purpose_edit)
        
        group.setLayout(layout)
        self.form_layout.addWidget(group)
    
    def create_coding_settings_section(self):
        """Create coding settings section."""
        group = QGroupBox("코딩 설정")
        group.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout = QFormLayout()
        
        # 코딩 언어
        self.programming_language_combo = QComboBox()
        self.programming_language_combo.addItems([
            "Python", "JavaScript", "TypeScript", "Java", "C#", "C++", 
            "Go", "Rust", "PHP", "Ruby", "Swift", "Kotlin", "기타"
        ])
        layout.addRow("주요 코딩 언어:", self.programming_language_combo)
        
        # 코드 구조 방식
        self.code_structure_edit = QTextEdit()
        self.code_structure_edit.setMaximumHeight(80)
        self.code_structure_edit.setPlaceholderText("MVC, MVVM, Layered Architecture 등 사용하는 구조 방식을 설명해주세요.")
        layout.addRow("코드 구조 방식:", self.code_structure_edit)
        
        group.setLayout(layout)
        self.form_layout.addWidget(group)
    
    def create_document_settings_section(self):
        """Create document settings section."""
        group = QGroupBox("문서 설정")
        group.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout = QFormLayout()
        
        # 작업 계획 문서 경로
        self.doc_path_edit = QLineEdit()
        repo_name = self.get_current_repo_name()
        default_path = f"{repo_name}\\docs"
        self.doc_path_edit.setText(default_path)
        self.doc_path_edit.setPlaceholderText(f"기본값: {default_path}")
        layout.addRow("작업 계획 문서 경로:", self.doc_path_edit)
        
        group.setLayout(layout)
        self.form_layout.addWidget(group)
    
    def create_advanced_settings_section(self):
        """Create advanced settings section."""
        group = QGroupBox("고급 설정")
        group.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout = QFormLayout()
        
        # 호완성 유지 규칙
        self.compatibility_rules_edit = QTextEdit()
        self.compatibility_rules_edit.setMaximumHeight(80)
        self.compatibility_rules_edit.setPlaceholderText("프로그램의 호환성 유지 규칙을 설명해주세요.")
        layout.addRow("호완성 유지 규칙:", self.compatibility_rules_edit)
        
        # Key Design Patterns
        self.design_patterns_edit = QTextEdit()
        self.design_patterns_edit.setMaximumHeight(100)
        self.design_patterns_edit.setPlaceholderText("사용할 주요 디자인 패턴들을 나열해주세요.\n예: Strategy Pattern, Factory Pattern, Observer Pattern 등")
        layout.addRow("Key Design Patterns (GoF):", self.design_patterns_edit)
        
        group.setLayout(layout)
        self.form_layout.addWidget(group)
    
    def get_current_repo_name(self):
        """Get current repository name from path."""
        try:
            current_path = Path.cwd()
            return current_path.name
        except:
            return "MyProject"
    
    def on_complete(self):
        """Handle setup completion."""
        try:
            # Collect all input data
            setup_data = {
                'project_name': self.project_name_edit.text().strip(),
                'project_description': self.project_desc_edit.toPlainText().strip(),
                'project_purpose': self.project_purpose_edit.toPlainText().strip(),
                'programming_language': self.programming_language_combo.currentText(),
                'code_structure': self.code_structure_edit.toPlainText().strip(),
                'doc_path': self.doc_path_edit.text().strip(),
                'compatibility_rules': self.compatibility_rules_edit.toPlainText().strip(),
                'design_patterns': self.design_patterns_edit.toPlainText().strip(),
                'created_date': datetime.now().strftime("%Y-%m-%d"),
                'updated_date': datetime.now().strftime("%Y-%m-%d")
            }
            
            # Validate required fields
            if not setup_data['project_name']:
                QMessageBox.warning(self, "입력 오류", "프로그램 이름을 입력해주세요.")
                return
            
            if not setup_data['project_description']:
                QMessageBox.warning(self, "입력 오류", "프로그램 설명을 입력해주세요.")
                return
            
            # Generate the instructions file
            success = self.generate_instructions_file(setup_data)
            if success:
                self.setup_completed.emit(setup_data)
                self.status_label.setText("✓ 설정이 완료되었습니다!")
                self.status_label.setStyleSheet("color: green")
            else:
                self.status_label.setText("✗ 파일 생성 실패")
                self.status_label.setStyleSheet("color: red")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 처리 중 오류가 발생했습니다: {str(e)}")
    
    def generate_instructions_file(self, setup_data):
        """Generate .github/copilot-instructions.md from template."""
        try:
            # Template file path
            template_path = Path(__file__).parent.parent / "copilot-instructions.format.md"
            
            # Output file path
            output_path = Path(".github") / "copilot-instructions.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Read template
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Prepare replacement data
            replacements = {
                'PROJECT_NAME': setup_data['project_name'],
                'PROJECT_DESCRIPTION': setup_data['project_description'],
                'PROJECT_PURPOSE': setup_data['project_purpose'],
                'VERSION_MAJOR': '1',
                'VERSION_MINOR': '0',
                'VERSION_PATCH': '0',
                'CREATED_DATE': setup_data['created_date'],
                'UPDATED_DATE': setup_data['updated_date'],
                'Main_Planning_document': 'NextTask',
                'path_to_main_planning_document': setup_data['doc_path'],
                'INSTALL_COMMAND': f'pip install {setup_data["project_name"].lower().replace(" ", "-")}',
                'RUN_COMMAND': f'python -m {setup_data["project_name"].lower().replace(" ", "_")}',
                'SYSTEM_OVERVIEW': self.generate_system_overview(setup_data),
                'ENTRY_POINTS': self.generate_entry_points(setup_data),
                'ARCHITECTURE_PATTERNS': self.generate_architecture_patterns(setup_data),
                'REQUIRED_SETUP': self.generate_required_setup(setup_data),
                'GUIDELINES_REFERENCE': self.generate_guidelines_reference(setup_data),
                'CRITICAL_CONSTRAINTS': setup_data['compatibility_rules'],
                'KEY_DOCUMENTATION': self.generate_key_documentation(setup_data),
                'CURRENT_STATUS': self.generate_current_status(setup_data),
                'Main_Guidelines_document': 'docs_2/guidelines/'
            }
            
            # Apply replacements
            result_content = template_content
            for key, value in replacements.items():
                placeholder = f"{{{{{key}}}}}"
                result_content = result_content.replace(placeholder, value)
            
            # Write output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result_content)
            
            return True
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(self, "파일 생성 오류", f"파일 생성 중 오류가 발생했습니다:\n{str(e)}\n\n상세 정보:\n{error_details}")
            return False
    
    def generate_system_overview(self, setup_data):
        """Generate system overview section."""
        return f"""**Purpose**: {setup_data['project_purpose']}

**Technology Stack**:
- **Primary Language**: {setup_data['programming_language']}
- **Architecture**: {setup_data['code_structure']}
- **Design Patterns**: {setup_data['design_patterns']}

**Key Features**:
- {setup_data['project_description']}"""

    def generate_entry_points(self, setup_data):
        """Generate entry points section."""
        return f"""## 📦 Entry Points

### Main Application
```bash
python main.py  # or equivalent entry point
```

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run in development mode
python -m {setup_data['project_name'].lower().replace(' ', '_')}
```"""

    def generate_architecture_patterns(self, setup_data):
        """Generate architecture patterns section."""
        return f"""## 🏗️ Architecture Patterns

The system implements the following core architecture patterns:

1. **{setup_data['code_structure']}**: Primary architecture approach
2. **Strategy Pattern**: For flexible algorithm selection
3. **Factory Pattern**: For object creation management
4. **Observer Pattern**: For event-driven communication

**Key Design Patterns** (GoF):
{setup_data['design_patterns']}"""

    def generate_required_setup(self, setup_data):
        """Generate required setup section."""
        return f"""## 🔧 Required Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# For {setup_data['programming_language']} development
# Add your specific setup commands here
```

**Prerequisites**:
- Python 3.8+
- {setup_data['programming_language']} development environment
- Git for version control"""

    def generate_guidelines_reference(self, setup_data):
        """Generate guidelines reference section."""
        return f"""## 📚 Guidelines Reference

**Main**: `{setup_data['doc_path']}/NextTask-2.md`

**Detailed** (`{setup_data['doc_path']}/guidelines/`):
1. `architecture-guidelines.md` - Architecture patterns and principles
2. `coding-standards.md` - {setup_data['programming_language']} coding standards
3. `testing-guidelines.md` - Testing requirements and practices
4. `deployment-guide.md` - Deployment and production setup"""

    def generate_key_documentation(self, setup_data):
        """Generate key documentation section."""
        return f"""## 📚 Key Documentation

**Before Changes**:
- `{setup_data['doc_path']}/` - Project documentation root
- `{setup_data['doc_path']}/guidelines/` - Development guidelines
- `{setup_data['doc_path']}/NextTask-2.md` - Current tasks and progress

**API Documentation**:
- Auto-generated from docstrings
- Located in `docs/api/` directory"""

    def generate_current_status(self, setup_data):
        """Generate current status section."""
        return f"""## 📊 Current Status (v1.0.0)

- **Development Stage**: Initial setup completed
- **Architecture**: {setup_data['code_structure']} implemented
- **Testing**: Basic test structure in place
- **Documentation**: Initial documentation created

**Active Development**: See `{setup_data['doc_path']}/NextTask-2.md` for current priorities

**Next Steps**:
1. Implement core functionality
2. Add comprehensive tests
3. Set up CI/CD pipeline
4. Deploy initial version"""


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, api_server, yaml_handler, config):
        super().__init__()
        self.api_server = api_server
        self.yaml_handler = yaml_handler
        self.config = config
        
        # Check for existing copilot-instructions.md
        self.check_instructions_file()
        
        self.init_ui()
        
    def check_instructions_file(self):
        """Check for existing copilot-instructions.md and handle user choice."""
        instructions_path = Path(".github") / "copilot-instructions.md"
        
        if instructions_path.exists():
            # File exists, ask user what to do
            self.show_instructions_choice_dialog()
        else:
            # File doesn't exist, show setup wizard
            self.show_setup_wizard()
    
    def show_instructions_choice_dialog(self):
        """Show dialog for existing instructions file choice."""
        msg_box = QMessageBox()
        msg_box.setWindowTitle("기존 Copilot Instructions 파일 발견")
        msg_box.setText("이미 .github/copilot-instructions.md 파일이 존재합니다.\n\n어떻게 하시겠습니까?")
        msg_box.setIcon(QMessageBox.Icon.Question)
        
        # Custom buttons
        format_btn = msg_box.addButton("서식에 맞게 변경", QMessageBox.ButtonRole.ActionRole)
        create_new_btn = msg_box.addButton("새로 생성", QMessageBox.ButtonRole.ActionRole)
        keep_btn = msg_box.addButton("기존 파일 유지", QMessageBox.ButtonRole.ActionRole)
        skip_btn = msg_box.addButton("생성하지 않음", QMessageBox.ButtonRole.ActionRole)
        
        msg_box.setDefaultButton(keep_btn)
        msg_box.exec()
        
        clicked_button = msg_box.clickedButton()
        
        if clicked_button == format_btn:
            self.format_existing_instructions()
        elif clicked_button == create_new_btn:
            self.show_setup_wizard()
        elif clicked_button == keep_btn:
            # Do nothing, proceed with existing file
            pass
        elif clicked_button == skip_btn:
            # Show warning and proceed
            warning_box = QMessageBox()
            warning_box.setWindowTitle("경고")
            warning_box.setText("copilot-instructions.md 파일이 없으면 vibeStation의 호환성이 떨어질 수 있습니다.\n\n계속 진행하시겠습니까?")
            warning_box.setIcon(QMessageBox.Icon.Warning)
            warning_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            warning_box.setDefaultButton(QMessageBox.StandardButton.No)
            
            if warning_box.exec() == QMessageBox.StandardButton.Yes:
                pass  # Proceed without file
            else:
                self.show_instructions_choice_dialog()  # Show choice dialog again
    
    def format_existing_instructions(self):
        """Format existing instructions file to match template structure."""
        try:
            instructions_path = Path(".github") / "copilot-instructions.md"
            
            # Check if file exists
            if not instructions_path.exists():
                QMessageBox.warning(self, "오류", "copilot-instructions.md 파일을 찾을 수 없습니다.")
                return
            
            # Read existing file
            with open(instructions_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
            
            # Create backup
            backup_path = instructions_path.with_suffix('.md.backup')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(existing_content)
            
            # Try to extract basic info from existing file
            setup_data = self.extract_info_from_existing_file(existing_content)
            
            # Generate new formatted file
            success = self.generate_instructions_file(setup_data)
            
            if success:
                # Switch to editor tab for review and manual editing
                tabs = self.findChild(QTabWidget)
                if tabs:
                    for i in range(tabs.count()):
                        if tabs.tabText(i) == "📝 Instructions Editor":
                            tabs.setCurrentIndex(i)
                            break
                
                # Reload content in editor
                self.editor_widget.load_instructions_content()
                
                QMessageBox.information(
                    self, 
                    "서식 변경 완료", 
                    f"기존 파일을 서식에 맞게 변경했습니다.\n\n백업 파일: {backup_path}\n\n이제 'Instructions Editor' 탭에서 내용을 검토하고 수동으로 수정할 수 있습니다."
                )
            else:
                QMessageBox.warning(self, "오류", "파일 서식 변경에 실패했습니다.")
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(self, "오류", f"파일 서식 변경 중 오류가 발생했습니다:\n{str(e)}\n\n상세 정보:\n{error_details}")
    
    def extract_info_from_existing_file(self, content):
        """Extract basic information from existing instructions file."""
        # Default values
        setup_data = {
            'project_name': 'My Project',
            'project_description': '프로젝트 설명을 입력해주세요.',
            'project_purpose': '프로젝트 목적을 입력해주세요.',
            'programming_language': 'Python',
            'code_structure': 'Layered Architecture',
            'doc_path': f"{Path.cwd().name}\\docs",
            'compatibility_rules': '호환성 유지 규칙을 입력해주세요.',
            'design_patterns': 'Strategy Pattern, Factory Pattern, Observer Pattern',
            'created_date': datetime.now().strftime("%Y-%m-%d"),
            'updated_date': datetime.now().strftime("%Y-%m-%d")
        }
        
        # Try to extract project name from title
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            if line.startswith('# '):
                setup_data['project_name'] = line[2:].strip()
                break
        
        return setup_data
    
    def show_setup_wizard(self):
        """Show the setup wizard for new instructions file."""
        self.setup_wizard = SetupWizardWidget()
        self.setup_wizard.setup_completed.connect(self.on_setup_completed)
        
        # Replace central widget with setup wizard
        if hasattr(self, 'central_widget'):
            self.setCentralWidget(self.setup_wizard)
        else:
            self.setCentralWidget(self.setup_wizard)
    
    def on_setup_completed(self, setup_data):
        """Handle setup completion."""
        # Show success message
        QMessageBox.information(
            self, 
            "설정 완료", 
            ".github/copilot-instructions.md 파일이 성공적으로 생성되었습니다!"
        )
        
        # Switch back to main UI
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface."""
        # Load UI from .ui file if it exists
        ui_file = Path(__file__).parent / "main_window.ui"
        if ui_file.exists():
            uic.loadUi(str(ui_file), self)
            # Additional setup after loading UI
            self.setup_ui_after_load()
        else:
            # Fallback to programmatic UI creation
            self.create_ui_programmatically()
    
    def setup_ui_after_load(self):
        """Setup UI components after loading from .ui file."""
        # Set window properties
        self.setWindowTitle("vibeStation Setup - GitHub Instructions Manager")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize Instructions Editor tab
        self.editor_widget = InstructionsEditorWidget(self.yaml_handler)
        # Replace the placeholder editor with the actual widget
        if hasattr(self, 'instructionsEditor'):
            # Remove placeholder and add real widget
            layout = self.instructionsTab.layout()
            layout.replaceWidget(self.instructionsEditor, self.editor_widget)
            self.instructionsEditor.hide()
        
        # Initialize Setup Wizard tab
        self.setup_widget = SetupWizardWidget()
        self.setup_widget.setup_completed.connect(self.on_setup_completed)
        # Replace the scroll area content with the actual widget
        if hasattr(self, 'scrollArea'):
            self.scrollArea.setWidget(self.setup_widget)
        
        # Initialize Info tab
        info_widget = self.create_info_widget()
        if hasattr(self, 'infoTextEdit'):
            layout = self.infoTab.layout()
            layout.replaceWidget(self.infoTextEdit, info_widget)
            self.infoTextEdit.hide()
        
        # Connect menu actions
        if hasattr(self, 'actionSave'):
            self.actionSave.triggered.connect(self.save_current_tab)
        if hasattr(self, 'actionExit'):
            self.actionExit.triggered.connect(self.close)
        if hasattr(self, 'actionAbout'):
            self.actionAbout.triggered.connect(self.show_about)
        
        # Status bar
        self.statusBar().showMessage("Ready - Setup Mode")
        
    def create_ui_programmatically(self):
        """Create UI programmatically (fallback method)."""
        self.setWindowTitle("vibeStation Setup - GitHub Instructions Manager")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Header
        header = QLabel("vibeStation Setup - GitHub Copilot Instructions Manager")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Tab widget
        tabs = QTabWidget()

        # Instructions editor tab
        self.editor_widget = InstructionsEditorWidget(self.yaml_handler)
        tabs.addTab(self.editor_widget, "📝 Instructions Editor")

        # Setup wizard tab
        self.setup_widget = SetupWizardWidget()
        self.setup_widget.setup_completed.connect(self.on_setup_completed)
        tabs.addTab(self.setup_widget, "🛠️ Setup Wizard")

        # Info tab
        info_widget = self.create_info_widget()
        tabs.addTab(info_widget, "ℹ️ Info")

        layout.addWidget(tabs)

        # Status bar
        self.statusBar().showMessage("Ready - Setup Mode")
    
    def save_current_tab(self):
        """Save content of current tab."""
        current_index = self.tabWidget.currentIndex()
        if current_index == 0:  # Instructions Editor
            self.editor_widget.save_instructions_content()
        elif current_index == 1:  # Setup Wizard
            # Setup wizard has its own save button
            pass
        elif current_index == 2:  # Info
            # Info tab is read-only
            pass
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About vibeStation Setup",
            "vibeStation Setup v1.0\n\n"
            "GitHub Copilot Instructions Manager\n\n"
            "Create and edit .github/copilot-instructions.md files\n"
            "with an intuitive setup wizard and editor."
        )
    
    def create_info_widget(self) -> QWidget:
        """Create info widget with usage instructions."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setHtml("""
        <h2>vibeStation - Vibe Coding Support Tool</h2>
        
        <h3>Features</h3>
        <ul>
            <li><b>Tier Logs (A-F):</b> Monitor real-time logs received via POST /stream</li>
            <li><b>Instructions Editor:</b> Edit .github/instructions.yaml with backup and validation</li>
            <li><b>FastAPI Server:</b> Built-in API server with authentication</li>
            <li><b>Secure Operations:</b> Atomic file writes with automatic backups</li>
        </ul>
        
        <h3>API Endpoints</h3>
        <ul>
            <li><b>POST /stream:</b> Send tier logs (requires auth)</li>
            <li><b>GET /logs:</b> Retrieve stored logs (requires auth)</li>
            <li><b>POST /vibe_log:</b> Send logs with retry mechanism (requires auth)</li>
            <li><b>GET /health:</b> Health check</li>
            <li><b>GET /auth_key:</b> Get authentication key</li>
        </ul>
        
        <h3>Authentication</h3>
        <p>Auth key is stored in <code>.github/auth_key.txt</code>. 
        Use as Bearer token in API requests:</p>
        <pre>Authorization: Bearer &lt;auth_key&gt;</pre>
        
        <h3>Example Usage</h3>
        <pre>
# Send a log entry
curl -X POST http://127.0.0.1:8765/stream \\
  -H "Authorization: Bearer YOUR_AUTH_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"tier": "A", "message": "High priority log"}'
        </pre>
        """)
        
        layout.addWidget(info_text)
        return widget
    

    def closeEvent(self, event):
        """Handle window close event."""
        reply = QMessageBox.question(
            self,
            'Exit',
            'Are you sure you want to exit vibeStation?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
    
    def generate_instructions_file(self, setup_data):
        """Generate .github/copilot-instructions.md from template."""
        try:
            # Template file path
            template_path = Path(__file__).parent.parent / "copilot-instructions.format.md"
            
            # Output file path
            output_path = Path(".github") / "copilot-instructions.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Read template
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Prepare replacement data
            replacements = {
                'PROJECT_NAME': setup_data['project_name'],
                'PROJECT_DESCRIPTION': setup_data['project_description'],
                'PROJECT_PURPOSE': setup_data['project_purpose'],
                'VERSION_MAJOR': '1',
                'VERSION_MINOR': '0',
                'VERSION_PATCH': '0',
                'CREATED_DATE': setup_data['created_date'],
                'UPDATED_DATE': setup_data['updated_date'],
                'Main_Planning_document': 'NextTask',
                'path_to_main_planning_document': setup_data['doc_path'],
                'INSTALL_COMMAND': f'pip install {setup_data["project_name"].lower().replace(" ", "-")}',
                'RUN_COMMAND': f'python -m {setup_data["project_name"].lower().replace(" ", "_")}',
                'SYSTEM_OVERVIEW': self.generate_system_overview(setup_data),
                'ENTRY_POINTS': self.generate_entry_points(setup_data),
                'ARCHITECTURE_PATTERNS': self.generate_architecture_patterns(setup_data),
                'REQUIRED_SETUP': self.generate_required_setup(setup_data),
                'GUIDELINES_REFERENCE': self.generate_guidelines_reference(setup_data),
                'CRITICAL_CONSTRAINTS': setup_data['compatibility_rules'],
                'KEY_DOCUMENTATION': self.generate_key_documentation(setup_data),
                'CURRENT_STATUS': self.generate_current_status(setup_data),
                'Main_Guidelines_document': 'docs_2/guidelines/'
            }
            
            # Apply replacements
            result_content = template_content
            for key, value in replacements.items():
                placeholder = f"{{{{{key}}}}}"
                result_content = result_content.replace(placeholder, value)
            
            # Write output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result_content)
            
            return True
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            QMessageBox.critical(self, "파일 생성 오류", f"파일 생성 중 오류가 발생했습니다:\n{str(e)}\n\n상세 정보:\n{error_details}")
            return False
    
    def generate_system_overview(self, setup_data):
        """Generate system overview section."""
        return f"""**Purpose**: {setup_data['project_purpose']}

**Technology Stack**:
- **Primary Language**: {setup_data['programming_language']}
- **Architecture**: {setup_data['code_structure']}
- **Design Patterns**: {setup_data['design_patterns']}

**Key Features**:
- {setup_data['project_description']}"""

    def generate_entry_points(self, setup_data):
        """Generate entry points section."""
        return f"""## 📦 Entry Points

### Main Application
```bash
python main.py  # or equivalent entry point
```

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run in development mode
python -m {setup_data['project_name'].lower().replace(' ', '_')}
```"""

    def generate_architecture_patterns(self, setup_data):
        """Generate architecture patterns section."""
        return f"""## 🏗️ Architecture Patterns

The system implements the following core architecture patterns:

1. **{setup_data['code_structure']}**: Primary architecture approach
2. **Strategy Pattern**: For flexible algorithm selection
3. **Factory Pattern**: For object creation management
4. **Observer Pattern**: For event-driven communication

**Key Design Patterns** (GoF):
{setup_data['design_patterns']}"""

    def generate_required_setup(self, setup_data):
        """Generate required setup section."""
        return f"""## 🔧 Required Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# For {setup_data['programming_language']} development
# Add your specific setup commands here
```

**Prerequisites**:
- Python 3.8+
- {setup_data['programming_language']} development environment
- Git for version control"""

    def generate_guidelines_reference(self, setup_data):
        """Generate guidelines reference section."""
        return f"""## 📚 Guidelines Reference

**Main**: `{setup_data['doc_path']}/NextTask-2.md`

**Detailed** (`{setup_data['doc_path']}/guidelines/`):
1. `architecture-guidelines.md` - Architecture patterns and principles
2. `coding-standards.md` - {setup_data['programming_language']} coding standards
3. `testing-guidelines.md` - Testing requirements and practices
4. `deployment-guide.md` - Deployment and production setup"""

    def generate_key_documentation(self, setup_data):
        """Generate key documentation section."""
        return f"""## 📚 Key Documentation

**Before Changes**:
- `{setup_data['doc_path']}/` - Project documentation root
- `{setup_data['doc_path']}/guidelines/` - Development guidelines
- `{setup_data['doc_path']}/NextTask-2.md` - Current tasks and progress

**API Documentation**:
- Auto-generated from docstrings
- Located in `docs/api/` directory"""

    def generate_current_status(self, setup_data):
        """Generate current status section."""
        return f"""## 📊 Current Status (v1.0.0)

- **Development Stage**: Initial setup completed
- **Architecture**: {setup_data['code_structure']} implemented
- **Testing**: Basic test structure in place
- **Documentation**: Initial documentation created

**Active Development**: See `{setup_data['doc_path']}/NextTask-2.md` for current priorities

**Next Steps**:
1. Implement core functionality
2. Add comprehensive tests
3. Set up CI/CD pipeline
4. Deploy initial version"""
