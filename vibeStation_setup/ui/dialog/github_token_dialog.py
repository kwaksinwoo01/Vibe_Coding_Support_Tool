"""
GitHub Token Help Dialog
Dialog component for GitHub Personal Access Token creation guide.
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton


class GitHubTokenHelpDialog(QDialog):
    """GitHub Token 생성법 도움말 다이얼로그"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GitHub Token 생성 가이드")
        self.setGeometry(200, 200, 600, 500)

        layout = QVBoxLayout()

        # 도움말 텍스트
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h2>GitHub Personal Access Token 생성 방법</h2>

        <h3>1. GitHub 로그인</h3>
        <p><a href="https://github.com">https://github.com</a></p>

        <h3>2. Settings 접근</h3>
        <p>우측 상단 프로필 아이콘 클릭 → <b>Settings</b></p>

        <h3>3. Developer settings</h3>
        <p>좌측 메뉴 하단 <b>"Developer settings"</b> 클릭</p>

        <h3>4. Personal access tokens</h3>
        <p><b>"Personal access tokens"</b> → <b>"Tokens (classic)"</b> 선택</p>

        <h3>5. 새 토큰 생성</h3>
        <p><b>"Generate new token"</b> → <b>"Generate new token (classic)"</b> 클릭</p>

        <h3>6. 토큰 설정</h3>
        <ul>
        <li><b>Note:</b> "MCP Server Token" (원하는 이름)</li>
        <li><b>Expiration:</b> "No expiration" (만료 없음) 또는 원하는 기간</li>
        <li><b>Select scopes (권한):</b>
          <ul>
          <li>✓ <b>repo</b> (전체 저장소 접근)</li>
          <li>✓ <b>workflow</b> (GitHub Actions 접근)</li>
          <li>✓ <b>read:org</b> (조직 정보 읽기)</li>
          </ul>
        </li>
        </ul>

        <h3>7. 토큰 생성</h3>
        <p>하단 <b>"Generate token"</b> 버튼 클릭</p>

        <h3>⚠️ 중요</h3>
        <p style="color: red; font-weight: bold;">생성된 토큰을 복사하세요!</p>
        <p>예: <code>ghp_1234567890abcdefghijklmnopqrstuvwxyz</code></p>
        <p style="color: orange;">(이 페이지를 떠나면 다시 볼 수 없습니다!)</p>
        """)
        layout.addWidget(help_text)

        # 닫기 버튼
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)