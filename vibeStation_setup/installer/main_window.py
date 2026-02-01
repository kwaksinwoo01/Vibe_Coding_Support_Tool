"""
Installer Module for vibeStation Setup.

This module contains UI components for the installation wizard that helps users
create and configure the copilot-instructions.md file.

Components:
- InstructionsEditorWidget: Editor for modifying copilot-instructions.md files
- SetupWizardWidget: Initial setup wizard for creating copilot-instructions.md
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QPushButton, QTabWidget,
    QMessageBox, QFileDialog, QSplitter, QLineEdit, QComboBox,
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
