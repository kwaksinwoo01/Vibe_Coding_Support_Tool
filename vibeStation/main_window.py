"""
PyQt6 Main Window for vibeStation.
Provides UI for monitoring logs and editing instructions.
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLabel, QPushButton, QTabWidget,
    QComboBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor, QTextCursor
from datetime import datetime
from pathlib import Path
import yaml


class LogDisplayWidget(QWidget):
    """Widget for displaying tier logs."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by Tier:"))
        
        self.tier_filter = QComboBox()
        self.tier_filter.addItems(["All", "A", "B", "C", "D", "E", "F"])
        self.tier_filter.currentTextChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.tier_filter)
        
        self.clear_btn = QPushButton("Clear Logs")
        self.clear_btn.clicked.connect(self.clear_logs)
        filter_layout.addWidget(self.clear_btn)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Log table
        self.log_table = QTableWidget()
        self.log_table.setColumnCount(3)
        self.log_table.setHorizontalHeaderLabels(["Time", "Tier", "Message"])
        self.log_table.setColumnWidth(0, 150)
        self.log_table.setColumnWidth(1, 50)
        self.log_table.setColumnWidth(2, 600)
        layout.addWidget(self.log_table)
        
        self.all_logs = []
        
    def add_log(self, tier: str, message: str, timestamp: str = None):
        """Add a log entry to the display."""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = {
            'tier': tier,
            'message': message,
            'timestamp': timestamp
        }
        self.all_logs.append(log_entry)
        
        # Apply filter
        self.refresh_display()
    
    def refresh_display(self):
        """Refresh the log display with current filter."""
        filter_tier = self.tier_filter.currentText()
        
        # Filter logs
        if filter_tier == "All":
            filtered_logs = self.all_logs
        else:
            filtered_logs = [log for log in self.all_logs if log['tier'] == filter_tier]
        
        # Update table
        self.log_table.setRowCount(len(filtered_logs))
        
        for i, log in enumerate(filtered_logs):
            # Timestamp
            time_item = QTableWidgetItem(log['timestamp'])
            self.log_table.setItem(i, 0, time_item)
            
            # Tier with color coding
            tier_item = QTableWidgetItem(log['tier'])
            tier_color = self._get_tier_color(log['tier'])
            tier_item.setBackground(tier_color)
            tier_item.setForeground(QColor(255, 255, 255))
            tier_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.log_table.setItem(i, 1, tier_item)
            
            # Message
            msg_item = QTableWidgetItem(log['message'])
            self.log_table.setItem(i, 2, msg_item)
        
        # Scroll to bottom
        self.log_table.scrollToBottom()
    
    def _get_tier_color(self, tier: str) -> QColor:
        """Get color for tier level."""
        colors = {
            'A': QColor(220, 53, 69),    # Red
            'B': QColor(255, 193, 7),    # Yellow
            'C': QColor(0, 123, 255),    # Blue
            'D': QColor(40, 167, 69),    # Green
            'E': QColor(108, 117, 125),  # Gray
            'F': QColor(23, 162, 184)    # Cyan
        }
        return colors.get(tier, QColor(128, 128, 128))
    
    def on_filter_changed(self):
        """Handle filter change."""
        self.refresh_display()
    
    def clear_logs(self):
        """Clear all logs."""
        self.all_logs.clear()
        self.log_table.setRowCount(0)
    
    def update_from_api(self, logs: list):
        """Update logs from API."""
        for log in logs:
            if log not in self.all_logs:
                self.add_log(
                    tier=log.get('tier', 'F'),
                    message=log.get('message', ''),
                    timestamp=log.get('timestamp', '')
                )


class InstructionsEditorWidget(QWidget):
    """Widget for editing instructions YAML file."""
    
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


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, api_server, yaml_handler, config):
        super().__init__()
        self.api_server = api_server
        self.yaml_handler = yaml_handler
        self.config = config
        self.init_ui()
        
        # Setup timer for log updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_logs)
        self.update_timer.start(2000)  # Update every 2 seconds
        
    def init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("vibeStation - GitHub Instructions Monitor")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Header
        header = QLabel("vibeStation - Vibe Coding Support Tool")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Server info
        port = self.config.get('server', {}).get('port', 8765)
        server_info = QLabel(f"FastAPI Server: http://127.0.0.1:{port}")
        server_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(server_info)
        
        # Tab widget
        tabs = QTabWidget()
        
        # Logs tab
        self.log_widget = LogDisplayWidget()
        tabs.addTab(self.log_widget, "📊 Tier Logs")
        
        # Instructions editor tab
        self.editor_widget = InstructionsEditorWidget(self.yaml_handler)
        tabs.addTab(self.editor_widget, "📝 Instructions Editor")
        
        # Info tab
        info_widget = self.create_info_widget()
        tabs.addTab(info_widget, "ℹ️ Info")
        
        layout.addWidget(tabs)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
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
    
    def update_logs(self):
        """Update logs from API server."""
        try:
            logs = self.api_server.get_logs()
            
            # Convert to dict format
            log_dicts = []
            for log in logs:
                log_dicts.append({
                    'tier': log.tier,
                    'message': log.message,
                    'timestamp': log.timestamp
                })
            
            # Update display (only new logs)
            current_count = len(self.log_widget.all_logs)
            new_logs = log_dicts[current_count:]
            
            for log in new_logs:
                self.log_widget.add_log(
                    tier=log['tier'],
                    message=log['message'],
                    timestamp=log['timestamp']
                )
            
            # Update status bar
            self.statusBar().showMessage(f"Total logs: {len(logs)}")
            
        except Exception as e:
            self.statusBar().showMessage(f"Error updating logs: {e}")
    
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
