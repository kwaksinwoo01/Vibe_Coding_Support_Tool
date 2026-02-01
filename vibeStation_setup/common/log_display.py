"""
Log display widget for vibeStation monitoring.
Provides tier-based log filtering and display functionality.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QTableWidget, QTableWidgetItem)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from datetime import datetime


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
