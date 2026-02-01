"""
Common Dialogs
공통으로 사용되는 다이얼로그 컴포넌트를 제공합니다.
"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit


class GitHubTokenHelpDialog(QDialog):
    """
    GitHub 토큰 도움말 다이얼로그
    
    GitHub Personal Access Token 생성 방법을 안내하는 다이얼로그입니다.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GitHub 토큰 생성 도움말")
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        # 제목
        title_label = QLabel("GitHub Personal Access Token 생성 방법")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)
        
        # 도움말 내용
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h3>GitHub Personal Access Token 생성 단계:</h3>
        <ol>
            <li>GitHub에 로그인합니다.</li>
            <li>Settings > Developer settings > Personal access tokens로 이동합니다.</li>
            <li>"Generate new token" 버튼을 클릭합니다.</li>
            <li>토큰 설명을 입력하고 필요한 권한을 선택합니다:
                <ul>
                    <li><b>repo</b> - 저장소 접근 권한</li>
                    <li><b>workflow</b> - GitHub Actions 워크플로우 권한</li>
                </ul>
            </li>
            <li>"Generate token" 버튼을 클릭합니다.</li>
            <li>생성된 토큰을 복사하여 안전한 곳에 보관합니다.</li>
        </ol>
        <p><b>주의:</b> 토큰은 한 번만 표시되므로 반드시 복사해 두세요!</p>
        """)
        layout.addWidget(help_text)
        
        # 닫기 버튼
        close_btn = QPushButton("확인")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
        self.resize(500, 400)


class SettingsDialog(QDialog):
    """
    설정 다이얼로그
    
    애플리케이션 설정을 변경할 수 있는 다이얼로그입니다.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        # 제목
        title_label = QLabel("Vibe Station 설정")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(title_label)
        
        # 설정 안내
        info_label = QLabel(
            "이 다이얼로그에서 다양한 설정을 변경할 수 있습니다.\n"
            "(설정 항목은 추후 추가될 예정입니다)"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 확인/취소 버튼
        ok_btn = QPushButton("확인")
        ok_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("취소")
        cancel_btn.clicked.connect(self.reject)
        
        layout.addWidget(ok_btn)
        layout.addWidget(cancel_btn)
        
        self.setLayout(layout)
        self.resize(400, 300)
