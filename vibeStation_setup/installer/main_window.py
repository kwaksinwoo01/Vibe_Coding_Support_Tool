"""
Setup Wizard Main Window
초기 설정 마법사 UI를 제공합니다.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QApplication
import sys


class SetupWizardWidget(QWidget):
    """
    초기 설정 마법사 위젯
    
    사용자가 처음 프로그램을 실행할 때 필요한 설정을 
    단계별로 안내하는 마법사 UI입니다.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vibe Station Setup Wizard")
        self.init_ui()
    
    def init_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout()
        
        # 환영 메시지
        welcome_label = QLabel("Vibe Station 설치 마법사에 오신 것을 환영합니다!")
        welcome_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 20px;")
        layout.addWidget(welcome_label)
        
        # 설명
        info_label = QLabel(
            "이 마법사는 Vibe Station을 처음 사용하는 데 필요한 설정을 안내합니다.\n\n"
            "다음 항목들을 설정할 수 있습니다:\n"
            "- GitHub 토큰 설정\n"
            "- 작업 디렉토리 설정\n"
            "- AI 에이전트 기본 설정"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("padding: 20px;")
        layout.addWidget(info_label)
        
        # 시작 버튼
        start_btn = QPushButton("설정 시작")
        start_btn.clicked.connect(self.start_setup)
        layout.addWidget(start_btn)
        
        # 건너뛰기 버튼
        skip_btn = QPushButton("건너뛰기")
        skip_btn.clicked.connect(self.skip_setup)
        layout.addWidget(skip_btn)
        
        self.setLayout(layout)
        self.resize(500, 300)
    
    def start_setup(self):
        """설정 시작"""
        # TODO: 설정 단계별 UI 구현
        print("설정을 시작합니다...")
        self.close()
    
    def skip_setup(self):
        """설정 건너뛰기"""
        print("설정을 건너뛰었습니다.")
        self.close()


def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    wizard = SetupWizardWidget()
    wizard.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
