"""
암호화된 설정 통합 가이드 - SettingsDialog 업데이트

이 파일은 SettingsDialog를 암호화된 설정으로 업데이트하는 방법을 설명합니다.
"""

# ============================================================================
# 1. Import 추가
# ============================================================================

# settings_dialog.py 상단에 추가:
from settings.config_manager import (
    save_encrypted_config,
    load_encrypted_config,
    setup_encryption
)


# ============================================================================
# 2. load_saved_settings() 메서드 수정
# ============================================================================

# 기존 코드:
def load_saved_settings(self):
    """저장된 설정 로드"""
    saved_config = load_config(self.config_file)
    # ... 기타 코드

# 새로운 코드:
def load_saved_settings(self):
    """저장된 설정 로드 (암호화 지원)"""
    # 먼저 암호화된 설정 시도
    saved_config = load_encrypted_config()
    
    # 암호화된 설정이 없으면 기존 JSON 시도
    if not saved_config:
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
    
    # 문서 검색 옵션 로드
    if "docs2_filter" in saved_config:
        self.docs2_filter_checkbox.setChecked(bool(saved_config["docs2_filter"]))
    if "docs_filter" in saved_config:
        self.docs_filter_checkbox.setChecked(bool(saved_config["docs_filter"]))
    if "keyword_filter" in saved_config:
        self.keyword_filter_checkbox.setChecked(bool(saved_config["keyword_filter"]))


# ============================================================================
# 3. save_github_config() 메서드 수정
# ============================================================================

# 기존 코드:
def save_github_config(self):
    # ... 설정 파일에 저장
    config = load_config(self.config_file)
    config["github_token"] = self.github_token_input.text().strip()
    # ...
    save_config(config, self.config_file)

# 새로운 코드:
def save_github_config(self):
    """GitHub 설정 저장 (암호화)"""
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
    
    # 암호화하여 저장
    config = {
        "github_token": self.github_token_input.text().strip(),
        "workflow_secret": self.workflow_secret_input.text().strip(),
        "repo_path": repo_path,
        "main_doc": main_doc,
        "branch": selected_branch or self.github_repo_config.branch,
        "docs2_filter": self.docs2_filter_checkbox.isChecked(),
        "docs_filter": self.docs_filter_checkbox.isChecked(),
        "keyword_filter": self.keyword_filter_checkbox.isChecked()
    }
    
    # 민감한 정보만 암호화
    sensitive_keys = ["github_token", "workflow_secret"]
    save_encrypted_config(config, sensitive_keys=sensitive_keys)
    
    # 전역 변수 업데이트
    global GITHUB_REPO_PATH, MAIN_DOCUMENT_PATH
    GITHUB_REPO_PATH = repo_path
    MAIN_DOCUMENT_PATH = main_doc
    
    self.log(f"✓ GitHub 설정 저장됨 (암호화됨)")
    self.log(f"  저장소: {repo_path}")
    self.log(f"  브랜치: {selected_branch or self.github_repo_config.branch}")
    self.log(f"  메인 문서: {main_doc}")
    if raw_url:
        self.log(f"  Raw GitHub URL: {raw_url}")
    self.log(f"  저장 위치: config/encrypted_config.json")


# ============================================================================
# 4. apply_env_vars() 메서드 수정
# ============================================================================

# 기존 코드:
def apply_env_vars(self):
    """환경 변수 적용 및 저장"""
    self.env_vars["GITHUB_TOKEN"] = self.github_token_input.text().strip()
    self.env_vars["WORKFLOW_SHARED_SECRET"] = self.workflow_secret_input.text().strip()
    
    # 시스템 환경 변수 설정
    os.environ["GITHUB_TOKEN"] = self.env_vars["GITHUB_TOKEN"]
    os.environ["WORKFLOW_SHARED_SECRET"] = self.env_vars["WORKFLOW_SHARED_SECRET"]
    
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

# 새로운 코드:
def apply_env_vars(self):
    """환경 변수 적용 및 저장 (암호화)"""
    # 환경 변수 업데이트
    github_token = self.github_token_input.text().strip()
    workflow_secret = self.workflow_secret_input.text().strip()
    
    self.env_vars["GITHUB_TOKEN"] = github_token
    self.env_vars["WORKFLOW_SHARED_SECRET"] = workflow_secret
    
    # 시스템 환경 변수 설정
    os.environ["GITHUB_TOKEN"] = github_token
    os.environ["WORKFLOW_SHARED_SECRET"] = workflow_secret
    
    # 암호화하여 저장
    config = {
        "github_token": github_token,
        "workflow_secret": workflow_secret
    }
    save_encrypted_config(config, sensitive_keys=["github_token", "workflow_secret"])
    
    self.log("✓ 환경 변수 적용 및 저장됨 (암호화됨)")
    self.log(f"  저장 위치: config/encrypted_config.json")
    
    # GitHub Token을 github_repo_config에도 적용
    if github_token:
        self.github_repo_config.github_token = github_token
        self.log("✓ GitHubReporter 활성화됨")
    else:
        self.log("⚠ GitHubReporter 비활성화됨 (토큰 없음)")


# ============================================================================
# 5. __init__ 메서드에서 암호화 초기화 추가 (선택사항)
# ============================================================================

def __init__(self, parent, config_file, github_repo_config, env_vars):
    super().__init__(parent)
    # ... 기존 코드
    
    # 암호화 초기화 (마스터 키 없으면 자동 생성)
    try:
        setup_encryption()
    except Exception as e:
        self.log(f"⚠ 암호화 초기화 실패: {e}")
        self.log("  일반 JSON으로 설정을 저장합니다")


# ============================================================================
# 6. requirements.txt 업데이트
# ============================================================================

# 다음을 추가:
cryptography>=41.0.0
python-dotenv>=1.0.0


# ============================================================================
# 완료!
# ============================================================================

# 이제 설정이 다음과 같이 저장됩니다:
# 1. GitHub Token, Workflow Secret → 암호화됨
# 2. Repo Path, Main Doc → 평문 저장
# 3. 파일: config/encrypted_config.json

# 마스터 키는:
# 1. 환경 변수 APP_MASTER_KEY에서 자동으로 읽음
# 2. 없으면 config/.key 파일로 자동 생성
