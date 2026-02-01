# settings_dialog.py

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTabWidget, QWidget, QGroupBox, QComboBox, QToolButton, QTextEdit,
    QFileDialog, QListWidget, QCheckBox
)
from PyQt6.QtCore import Qt

from dotenv import load_dotenv

from settings.github_repository_config import GitHubRepositoryConfig
from .dialog.github_token_dialog import GitHubTokenHelpDialog
from settings.config_manager import load_config, save_config, load_env_vars
from settings.constants import AGENT_PATH, REDIS_URL

# 환경 변수 로드
load_dotenv()


class SettingsDialog(QDialog):
    """설정 다이얼로그 (GitHub 저장소 연결 + 서버설정)"""
    
    def __init__(self, parent, config_file, github_repo_config, env_vars):
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.setGeometry(100, 100, 900, 700)
        
        self.parent_app = parent
        self.config_file = config_file
        self.github_repo_config = github_repo_config
        self.env_vars = env_vars
        
        # 메인 레이아웃
        main_layout = QVBoxLayout()
        
        # 탭 위젯
        self.tabs = QTabWidget()
        
        # 탭 1: GitHub 저장소 연결
        self.github_tab = QWidget()
        self.init_github_tab()
        self.tabs.addTab(self.github_tab, "GitHub 저장소 연결")
        
        # 탭 2: 서버 설정
        self.server_tab = QWidget()
        self.init_server_tab()
        self.tabs.addTab(self.server_tab, "서버 설정")
        
        main_layout.addWidget(self.tabs)
        
        # 닫기 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)
        
        self.setLayout(main_layout)
        
        # 저장된 설정 로드
        self.load_saved_settings()
    
    def load_saved_settings(self):
        """저장된 설정 로드"""
        saved_config = load_config(self.config_file)
        
        # GitHub Token 로드
        if "github_token" in saved_config:
            self.github_token_input.setText(saved_config["github_token"])
        
        # Workflow Secret 로드
        if "workflow_secret" in saved_config:
            self.workflow_secret_input.setText(saved_config["workflow_secret"])
        
        # 저장소 경로 로드
        if "repo_path" in saved_config:
            self.repo_input.setText(saved_config["repo_path"])
        
        # 메인 문서 로드
        if "main_doc" in saved_config:
            self.main_doc_input.setText(saved_config["main_doc"])
        
        # 브랜치 로드
        if "branch" in saved_config:
            self.branch_combo.setCurrentText(saved_config["branch"])

        # Redis URL 로드
        if "redis_url" in saved_config:
            self.redis_url_input.setText(saved_config["redis_url"])

        # 문서 검색 옵션 로드
        if "docs2_filter" in saved_config:
            self.docs2_filter_checkbox.setChecked(bool(saved_config["docs2_filter"]))
        if "docs_filter" in saved_config:
            self.docs_filter_checkbox.setChecked(bool(saved_config["docs_filter"]))
        if "keyword_filter" in saved_config:
            self.keyword_filter_checkbox.setChecked(bool(saved_config["keyword_filter"]))
    
    def init_github_tab(self):
        """GitHub 저장소 연결 탭 초기화"""
        layout = QVBoxLayout()
        
        # GitHub 저장소 설정 그룹
        github_group = QGroupBox("GitHub 저장소 설정")
        github_layout = QVBoxLayout()
        
        # 저장소 경로 + GitHub Token
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("저장소 경로:"))
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("https://github.com/owner/repo.git")
        row1.addWidget(self.repo_input)
        detect_repo_btn = QPushButton("연결")
        detect_repo_btn.clicked.connect(self.connect_github_repo)
        row1.addWidget(detect_repo_btn)
        github_layout.addLayout(row1)
        
        # GitHub Token + 도움말
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("GitHub Token:"))
        self.github_token_input = QLineEdit()
        self.github_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.github_token_input.setPlaceholderText("ghp_...")
        self.github_token_input.textChanged.connect(self.on_token_changed)
        row2.addWidget(self.github_token_input)
        
        # Token 도움말 버튼
        help_btn = QToolButton()
        help_btn.setText("?")
        help_btn.clicked.connect(self.show_token_help)
        row2.addWidget(help_btn)
        github_layout.addLayout(row2)
        
        # 저장소 정보 라벨
        self.repo_info_label = QLabel("저장소: 연결 안됨")
        self.repo_info_label.setStyleSheet("color: #888; font-size: 9pt;")
        github_layout.addWidget(self.repo_info_label)
        
        # Workflow Secret
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Workflow Secret:"))
        self.workflow_secret_input = QLineEdit()
        self.workflow_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        row3.addWidget(self.workflow_secret_input)
        github_layout.addLayout(row3)
        
        # 브랜치 선택
        row4 = QVBoxLayout()
        branch_label = QLabel("브랜치:")
        branch_label_desc = QLabel("(최근 커밋순 | GitHub Token 필요)")
        branch_label_desc.setStyleSheet("color: #888; font-size: 8pt;")
        row4.addWidget(branch_label)
        row4.addWidget(branch_label_desc)
        
        self.branch_combo = QComboBox()
        self.branch_combo.setEnabled(False)
        self.branch_combo.setEditable(True)
        
        # ✅ 브랜치 선택 시 이벤트 핸들러 연결
        self.branch_combo.currentTextChanged.connect(self.on_branch_selected)
        
        row4.addWidget(self.branch_combo)
        github_layout.addLayout(row4)

        
        # 메인 문서
        row5 = QVBoxLayout()
        doc_label = QLabel("메인 문서:")
        doc_label_desc = QLabel("(GitHub 저장소 기준 상대 경로 또는 로컬 파일 경로)")
        doc_label_desc.setStyleSheet("color: #888; font-size: 8pt;")
        row5.addWidget(doc_label)
        row5.addWidget(doc_label_desc)
        
        doc_input_layout = QHBoxLayout()
        self.main_doc_input = QLineEdit()
        self.main_doc_input.setPlaceholderText("docs_2/NextTask-2.md")
        doc_input_layout.addWidget(self.main_doc_input)
        
        validate_doc_btn = QPushButton("검증")
        validate_doc_btn.clicked.connect(self.validate_main_document)
        doc_input_layout.addWidget(validate_doc_btn)
        
        find_doc_btn = QPushButton("찾기")
        find_doc_btn.clicked.connect(self.find_main_document_in_github)
        doc_input_layout.addWidget(find_doc_btn)
        row5.addLayout(doc_input_layout)
        github_layout.addLayout(row5)

        # 문서 검색 옵션
        doc_filter_layout = QHBoxLayout()
        doc_filter_layout.addWidget(QLabel("검색 옵션:"))
        self.docs2_filter_checkbox = QCheckBox("docs_2")
        self.docs2_filter_checkbox.setChecked(True)
        doc_filter_layout.addWidget(self.docs2_filter_checkbox)
        self.docs_filter_checkbox = QCheckBox("docs")
        self.docs_filter_checkbox.setChecked(False)
        doc_filter_layout.addWidget(self.docs_filter_checkbox)
        self.keyword_filter_checkbox = QCheckBox("키워드 필터 사용(NextTask/WPD/PRD/Task)")
        self.keyword_filter_checkbox.setChecked(True)
        doc_filter_layout.addWidget(self.keyword_filter_checkbox)
        doc_filter_layout.addStretch()
        github_layout.addLayout(doc_filter_layout)

        # 문서 검색 결과 리스트
        results_group = QGroupBox("문서 검색 결과")
        results_layout = QVBoxLayout()
        self.doc_results_list = QListWidget()
        self.doc_results_list.setMinimumHeight(120)
        self.doc_results_list.itemDoubleClicked.connect(self._on_document_double_clicked)
        results_layout.addWidget(self.doc_results_list)

        results_btn_layout = QHBoxLayout()
        apply_doc_btn = QPushButton("선택 적용")
        apply_doc_btn.clicked.connect(self._on_apply_button_clicked)
        results_btn_layout.addStretch()
        results_btn_layout.addWidget(apply_doc_btn)
        results_layout.addLayout(results_btn_layout)

        results_group.setLayout(results_layout)
        github_layout.addWidget(results_group)
        
        # 설정 저장 버튼
        save_config_btn = QPushButton("GitHub 설정 저장")
        save_config_btn.clicked.connect(self.save_github_config)
        github_layout.addWidget(save_config_btn)
        
        github_group.setLayout(github_layout)
        layout.addWidget(github_group)
        
        # Agent 설정 그룹
        config_group = QGroupBox("Agent 설정")
        config_layout = QVBoxLayout()
        
        # Agent 경로 - 제거됨 (main_agent.py가 번들링됨)
        agent_info = QLabel("Agent 모듈: vibeStation_setup.mcp_suver.main_agent (번들링됨)")
        agent_info.setStyleSheet("color: #4CAF50; font-weight: bold;")
        config_layout.addWidget(agent_info)
        
        # Redis URL
        redis_url_layout = QHBoxLayout()
        redis_url_layout.addWidget(QLabel("Redis URL:"))
        self.redis_url_input = QLineEdit(self.env_vars["REDIS_URL"])
        redis_url_layout.addWidget(self.redis_url_input)
        config_layout.addLayout(redis_url_layout)
        
        # 적용 버튼
        apply_env_btn = QPushButton("환경 변수 적용")
        apply_env_btn.clicked.connect(self.apply_env_vars)
        config_layout.addWidget(apply_env_btn)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # 설정 로그 출력
        log_group = QGroupBox("설정 로그")
        log_layout = QVBoxLayout()
        self.settings_log_viewer = QTextEdit()
        self.settings_log_viewer.setReadOnly(True)
        self.settings_log_viewer.setStyleSheet(
            "background-color: #1e1e1e; color: #dcdcdc; "
            "font-family: 'Consolas', 'Courier New', monospace; "
            "font-size: 9pt; padding: 5px;"
        )
        log_layout.addWidget(self.settings_log_viewer)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        layout.addStretch()
        self.github_tab.setLayout(layout)
    
    def init_server_tab(self):
        """서버 설정 탭 초기화"""
        layout = QVBoxLayout()
        
        # 추후 확장용
        placeholder = QLabel("서버 설정 옵션 (추후 추가 예정)")
        placeholder.setStyleSheet("color: #888; font-size: 12pt; padding: 50px;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(placeholder)
        
        self.server_tab.setLayout(layout)
    
    def show_token_help(self):
        """GitHub Token 도움말 표시"""
        dialog = GitHubTokenHelpDialog(self)
        dialog.exec()
    
    def on_token_changed(self, text):
        """GitHub Token 입력시 브랜치 활성화"""
        if text.strip():
            self.branch_combo.setEnabled(True)
        else:
            self.branch_combo.setEnabled(False)
    
    def connect_github_repo(self):
        """GitHub 저장소 연결 및 브랜치 조회"""
        repo_path = self.repo_input.text().strip()
        if not repo_path:
            self.log("저장소 경로를 입력하세요.")
            return
        
        self.log(f"[GitHub] 저장소 연결 시도: {repo_path}")
        
        if self.github_repo_config.parse_repository(repo_path):
            self.log(f"✓ GitHub 저장소 연결 성공: {self.github_repo_config.owner}/{self.github_repo_config.repo_name}")
            self.log(f"  타입: {self.github_repo_config.repo_type}")
            self.repo_info_label.setText(
                f"저장소: {self.github_repo_config.owner}/{self.github_repo_config.repo_name} "
                f"({self.github_repo_config.repo_type})"
            )
            
            # GitHub Token 설정
            token = self.github_token_input.text().strip()
            if token:
                self.github_repo_config.github_token = token
                self.log("[GitHub] Token 지원 API 호출 (제한: 60 -> 5000)")
            
            # 브랜치 목록 조회
            self.log("[GitHub] 활성 브랜치 조회 중...")
            self.log("  방법 1: GitHub API 시도...")
            branches = self.github_repo_config.fetch_available_branches(use_git=False)
            
            if not branches:
                self.log("  GitHub API 실패 - 대체 방법 시도")
                self.log("  방법 2: git ls-remote 명령어 시도...")
                branches = self.github_repo_config.fetch_available_branches(use_git=True)
            
            if branches:
                # 최근 5개만 표시
                top_branches = branches[:5]
                
                self.log(f"✓ 활성 브랜치 총 {len(branches)}개 발견 (최근 5개 표시):")
                for i, branch in enumerate(top_branches, 1):
                    self.log(f"  {i}. {branch}")
                
                if len(branches) > 5:
                    self.log(f"  ... 외 {len(branches) - 5}개 (직접 입력 가능)")
                
                # 브랜치 콤보박스 업데이트 (드롭다운 방식)
                self.branch_combo.blockSignals(True)
                self.branch_combo.clear()
                self.branch_combo.addItems(top_branches)
                self.branch_combo.setEnabled(True)
                
                # 현재 브랜치 선택 (시그널 활성화 전에 설정)
                if self.github_repo_config.branch in top_branches:
                    self.branch_combo.setCurrentText(self.github_repo_config.branch)
                else:
                    self.branch_combo.setCurrentText(top_branches[0])
                
                self.branch_combo.blockSignals(False)
                
                # 초기 브랜치 적용 (시그널 활성화 후 수동 호출)
                initial_branch = self.branch_combo.currentText()
                self.github_repo_config.set_branch(initial_branch)
                self.log(f"✓ 브랜치 선택 준비 완료: {initial_branch}")
                self.log("  팁: 다른 브랜치는 콤보박스에서 직접 입력할 수 있습니다")
            else:
                self.log("⚠ 경고: 브랜치를 조회할 수 없습니다")
                self.log("  해결책:")
                self.log("  1. GitHub Token을 입력하세요")
                self.log("  2. 또는 git을 설치하고 PATH에 추가하세요")
                self.log("  3. 또는 로컬 저장소 경로로 변경하세요")
                self.log("  임시 해결: 브랜치를 수동으로 입력할 수 있습니다")
                
                # 수동 입력 활성화
                self.branch_combo.setEnabled(True)
                self.branch_combo.setEditable(True)
                self.branch_combo.lineEdit().setText("main")
        else:
            self.log("✗ GitHub 저장소 연결 실패. 경로 형식을 확인하세요.")
            self.repo_info_label.setText("저장소: 연결 실패")
            self.branch_combo.setEnabled(False)
            self.branch_combo.clear()

    def on_branch_selected(self, branch_name: str):
        """브랜치 선택 시 호출되는 함수"""
        if not branch_name or not branch_name.strip():
            return
        
        branch_name = branch_name.strip()
        
        # github_repo_config에 브랜치 적용
        if self.github_repo_config.is_valid:
            self.github_repo_config.set_branch(branch_name)
            self.log(f"")
            self.log(f"============================================================")
            self.log(f"[브랜치 선택] {branch_name}")
            self.log(f"============================================================")
            
            # 전역 환경 변수에도 반영
            global GITHUB_REPO_PATH, MAIN_DOCUMENT_PATH
            os.environ["GITHUB_BRANCH"] = branch_name
            
            # 메인 문서 경로가 있으면 자동 검증
            main_doc = self.main_doc_input.text().strip()
            if main_doc:
                self.log(f"✓ 메인 문서 자동 검증 시작: {main_doc}")
                self.validate_main_document()
        else:
            self.log(f"⚠ 브랜치 선택됨: {branch_name} (저장소 먼저 연결하세요)")


    def validate_main_document(self):
        """메인 문서 경로 검증 (자동 브랜치 폴백 포함)"""
        main_doc = self.main_doc_input.text().strip()
        
        if not main_doc:
            self.log("메인 문서 경로를 입력하세요.")
            return False
        
        if not self.github_repo_config.is_valid:
            self.log("GitHub 저장소를 먼저 연결하세요.")
            return False
        
        # 현재 선택된 브랜치 확인 (UI 우선)
        current_branch = self.branch_combo.currentText().strip()
        if not current_branch:
            current_branch = self.github_repo_config.branch
        
        self.log(f"")
        self.log(f"[검증 시작] 문서: {main_doc}")
        self.log(f"[검증] 선택된 브랜치: {current_branch}")
        
        # 시도할 브랜치 목록 (현재 → main → 기본 브랜치)
        branches_to_try = [current_branch]
        if "main" not in branches_to_try:
            branches_to_try.append("main")
        if self.github_repo_config.branch not in branches_to_try:
            branches_to_try.append(self.github_repo_config.branch)
        
        self.log(f"[검증] 브랜치별 순차 검색 시작...")
        
        # 브랜치별 순차 시도
        for branch in branches_to_try:
            raw_url = self.github_repo_config.get_raw_content_url(main_doc, branch)
            
            if not raw_url:
                self.log(f"  ✗ {branch}: URL 생성 실패")
                continue
            
            self.log(f"  시도 중: {branch}")
            
            try:
                import urllib.request
                import urllib.error
                
                request = urllib.request.Request(raw_url)
                request.add_header('User-Agent', 'Mozilla/5.0')
                
                # GitHub Token 인증 헤더 추가
                if self.github_repo_config.github_token:
                    request.add_header('Authorization', f'token {self.github_repo_config.github_token}')
                
                with urllib.request.urlopen(request, timeout=5) as response:
                    if response.status == 200:
                        content = response.read().decode('utf-8')
                        self.log(f"  ✓ 파일 발견! (브랜치: {branch}, 크기: {len(content)} bytes)")
                        
                        # 브랜치 자동 변경
                        if branch != current_branch:
                            self.branch_combo.setCurrentText(branch)
                            self.github_repo_config.set_branch(branch)
                            self.log(f"  ✓ 브랜치 자동 변경: {current_branch} → {branch}")
                        
                        self.log(f"")
                        self.log(f"✓✓✓ 검증 성공! ✓✓✓")
                        self.log(f"============================================================")
                        return True
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    self.log(f"  ✗ {branch}: 파일 없음 (404)")
                else:
                    self.log(f"  ✗ {branch}: HTTP {e.code}")
            except Exception as e:
                self.log(f"  ✗ {branch}: {str(e)}")
        
        # 모든 브랜치에서 실패
        self.log(f"")
        self.log(f"✗✗✗ 검증 실패 ✗✗✗")
        self.log(f"  시도한 브랜치: {', '.join(branches_to_try)}")
        self.log(f"  파일 경로: {main_doc}")
        self.log(f"")
        self.log(f"  해결책:")
        self.log(f"  1. '찾기' 버튼으로 전체 검색")
        self.log(f"  2. 브랜치를 수동으로 변경")
        self.log(f"  3. 파일 경로를 다시 확인")
        self.log(f"============================================================")
        return False
    
    def find_main_document_in_github(self):
        """GitHub 저장소에서 메인 문서 찾기"""
        if not self.github_repo_config.is_valid:
            self.log("GitHub 저장소를 먼저 연결하세요.")
            return
        
        current_branch = self.branch_combo.currentText() or self.github_repo_config.branch
        
        self.log(f"[GitHub] 문서 파일 검색 중 (브랜치: {current_branch})...")
        self.log("  마크다운 파일 찾기 (NextTask, WPD, PRD 등)...")
        
        try:
            import urllib.request
            import json
            
            # GitHub API: 트리 조회
            api_url = f"https://api.github.com/repos/{self.github_repo_config.owner}/{self.github_repo_config.repo_name}/git/trees/{current_branch}?recursive=1"
            request = urllib.request.Request(api_url)
            request.add_header('User-Agent', 'Mozilla/5.0')
            
            if self.github_repo_config.github_token:
                request.add_header('Authorization', f'token {self.github_repo_config.github_token}')
            
            with urllib.request.urlopen(request, timeout=10) as response:
                tree_data = json.loads(response.read().decode('utf-8'))
                
                # 마크다운 파일 수집
                markdown_files = [
                    item['path']
                    for item in tree_data.get('tree', [])
                    if item.get('type') == 'blob' and item.get('path', '').endswith('.md')
                ]

                # 키워드 필터 적용
                if self.keyword_filter_checkbox.isChecked():
                    keywords = ['nexttask', 'wpd', 'prd', 'task']
                    markdown_files = [
                        path for path in markdown_files
                        if any(keyword in path.lower() for keyword in keywords)
                    ]

                # docs_2 / docs 필터 적용
                selected_prefixes = []
                if self.docs2_filter_checkbox.isChecked():
                    selected_prefixes.append('docs_2/')
                if self.docs_filter_checkbox.isChecked():
                    selected_prefixes.append('docs/')

                if selected_prefixes:
                    markdown_files = [
                        path for path in markdown_files
                        if any(path.startswith(prefix) for prefix in selected_prefixes)
                    ]
                
                # 결과 리스트 갱신
                self.doc_results_list.clear()

                if markdown_files:
                    for file_path in markdown_files:
                        self.doc_results_list.addItem(file_path)

                    self.log(f"\n✓ 발견된 문서 파일 ({len(markdown_files)}개)")

                    # 첫 번째 항목 기본 선택
                    first_file = markdown_files[0]
                    self.doc_results_list.setCurrentRow(0)
                    self.main_doc_input.setText(first_file)
                    self.log(f"✓ 기본 선택: {first_file}")
                    self.log("  리스트에서 다른 문서를 선택한 뒤 '선택 적용'을 누르세요")
                else:
                    self.log(f"✗ 마크다운 문서를 찾을 수 없습니다.")
                    self.log(f"  docs_2/ 디렉토리에 파일이 없을 수 있습니다.")
        
        except Exception as e:
            self.log(f"✗ 오류: {str(e)}")
            self.log(f"  수동으로 파일 경로를 입력하거나 GitHub Token을 확인하세요")

    def apply_selected_document(self, item=None):
        """검색 결과에서 선택한 문서를 메인 문서로 적용"""
        if item is None:
            item = self.doc_results_list.currentItem()

        if not item:
            self.log("선택된 문서가 없습니다.")
            return

        selected_path = item.text()
        self.main_doc_input.setText(selected_path)
        self.log(f"✓ 문서 선택됨: {selected_path}")

    def _on_document_double_clicked(self, item):
        """리스트 항목 더블클릭 이벤트 핸들러"""
        self.apply_selected_document(item)

    def _on_apply_button_clicked(self):
        """선택 적용 버튼 클릭 이벤트 핸들러"""
        # 통합: 선택 적용 + 설정 저장까지 수행
        self.save_github_config()
    
    def save_github_config(self):
        """GitHub 설정 저장"""
        # 문서 검색 결과에서 선택된 항목이 있으면 먼저 적용
        current_item = self.doc_results_list.currentItem() if self.doc_results_list else None
        if current_item is not None:
            selected_path = current_item.text().strip()
            if selected_path:
                self.main_doc_input.setText(selected_path)
                self.log(f"✓ 문서 선택됨(저장): {selected_path}")

        repo_path = self.repo_input.text().strip()
        main_doc = self.main_doc_input.text().strip()

        if not repo_path:
            self.log("저장소 경로가 비어 있습니다. 그래도 설정은 저장합니다.")

        if not main_doc:
            self.log("메인 문서 경로가 비어 있습니다. 그래도 설정은 저장합니다.")
        
        # 브랜치 설정 (UI에서 선택된 브랜치 우선)
        selected_branch = self.branch_combo.currentText().strip()
        if selected_branch:
            if self.github_repo_config.is_valid:
                self.github_repo_config.set_branch(selected_branch)
            self.log(f"  저장할 브랜치: {selected_branch}")
        else:
            self.log(f"  경고: 브랜치가 선택되지 않음")
        
        # Raw GitHub URL 생성
        raw_url = ""
        if self.github_repo_config.is_valid and main_doc:
            raw_url = self.github_repo_config.get_raw_content_url(main_doc)
            if not raw_url:
                self.log("Raw URL을 생성할 수 없습니다. 저장소 설정을 확인하세요.")
        
        # 설정 파일에 저장
        config = load_config(self.config_file)
        config["github_token"] = self.github_token_input.text().strip()
        config["workflow_secret"] = self.workflow_secret_input.text().strip()
        config["repo_path"] = repo_path
        config["main_doc"] = main_doc
        config["branch"] = selected_branch or self.github_repo_config.branch
        config["redis_url"] = self.redis_url_input.text().strip()
        config["docs2_filter"] = self.docs2_filter_checkbox.isChecked()
        config["docs_filter"] = self.docs_filter_checkbox.isChecked()
        config["keyword_filter"] = self.keyword_filter_checkbox.isChecked()
        save_config(config, self.config_file)
        
        # 전역 변수 업데이트
        global GITHUB_REPO_PATH, MAIN_DOCUMENT_PATH
        GITHUB_REPO_PATH = repo_path
        MAIN_DOCUMENT_PATH = main_doc
        
        self.log(f"✓ GitHub 설정 저장됨")
        self.log(f"  저장소: {repo_path}")
        self.log(f"  브랜치: {selected_branch or self.github_repo_config.branch}")
        self.log(f"  메인 문서: {main_doc}")
        if raw_url:
            self.log(f"  Raw GitHub URL: {raw_url}")
        self.log(f"  저장 위치: {self.config_file}")
    
    
    def apply_env_vars(self):
        """환경 변수 적용 및 저장"""
        # 환경 변수 업데이트
        self.env_vars["GITHUB_TOKEN"] = self.github_token_input.text().strip()
        self.env_vars["WORKFLOW_SHARED_SECRET"] = self.workflow_secret_input.text().strip()
        self.env_vars["REDIS_URL"] = self.redis_url_input.text().strip()
        
        # 시스템 환경 변수 설정
        os.environ["GITHUB_TOKEN"] = self.env_vars["GITHUB_TOKEN"]
        os.environ["WORKFLOW_SHARED_SECRET"] = self.env_vars["WORKFLOW_SHARED_SECRET"]
        os.environ["REDIS_URL"] = self.env_vars["REDIS_URL"]
        
        # 설정 파일에 저장
        config = load_config(self.config_file)
        config["github_token"] = self.env_vars["GITHUB_TOKEN"]
        config["workflow_secret"] = self.env_vars["WORKFLOW_SHARED_SECRET"]
        save_config(config, self.config_file)
        
        self.log("✓ 환경 변수 적용 및 저장됨")
        self.log(f"  저장 위치: {self.config_file}")
        
        # GitHub Token을 github_repo_config에도 적용
        if self.env_vars["GITHUB_TOKEN"]:
            self.github_repo_config.github_token = self.env_vars["GITHUB_TOKEN"]
            self.log("✓ GitHubReporter 활성화됨")
        else:
            self.log("⚠ GitHubReporter 비활성화됨 (토큰 없음)")
    
    def log(self, message: str):
        """로그 출력 (부모 앱의 로그 뷰어 사용)"""
        if hasattr(self, "settings_log_viewer") and self.settings_log_viewer is not None:
            self.settings_log_viewer.append(message)
        self.parent_app.log(message)

__all__ = [
"SettingsDialog",

]