import json
import sys
import os
import platform
from pathlib import Path
from typing import List, Optional
from core.models import SessionModel

# Windows 레지스트리 지원을 위한 모듈 (Windows 환경에서만 로드)
if platform.system() == "Windows":
    import winreg

class SessionManager:
    def __init__(self):
        self.sessions: List[SessionModel] = self.load_sessions()

    def _get_config_path(self) -> Path:
        """플랫폼별 설정 파일 저장 경로를 반환합니다."""
        if platform.system() == "Windows":
            # Windows는 레지스트리를 우선하지만, 백업용 파일 경로도 준비
            return Path(os.environ.get("APPDATA", str(Path.home() / "AppData/Roaming"))) / "MSPT"
        elif platform.system() == "Darwin":
            return Path.home() / "Library/Application Support/MSPT"
        else:
            # Linux 및 기타 XDG 규격 준수
            xdg_config = os.environ.get("XDG_CONFIG_HOME")
            if xdg_config:
                return Path(xdg_config) / "mspt"
            return Path.home() / ".config/mspt"

    def load_sessions(self) -> List[SessionModel]:
        """플랫폼에 맞는 방식으로 세션을 로드합니다."""
        if platform.system() == "Windows":
            return self._load_from_registry()
        else:
            return self._load_from_file()

    def save_sessions(self):
        """플랫폼에 맞는 방식으로 세션을 저장합니다."""
        if platform.system() == "Windows":
            self._save_to_registry()
        else:
            self._save_to_file()

    # --- Windows Registry Methods ---
    def _load_from_registry(self) -> List[SessionModel]:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\MSPT", 0, winreg.KEY_READ) as key:
                data_str, _ = winreg.QueryValueEx(key, "Sessions")
                data = json.loads(data_str)
                return [SessionModel(**item) for item in data]
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            # 레지스트리 키가 없거나 오류 시 파일 백업 확인
            return self._load_from_file()

    def _save_to_registry(self):
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\MSPT") as key:
                data_str = json.dumps([s.dict() for s in self.sessions], ensure_ascii=False)
                winreg.SetValueEx(key, "Sessions", 0, winreg.REG_SZ, data_str)
        except OSError:
            # 레지스트리 실패 시 파일로 저장
            self._save_to_file()

    # --- Linux/macOS File Methods ---
    def _load_from_file(self) -> List[SessionModel]:
        config_path = self._get_config_path()
        session_file = config_path / "sessions.json"
        
        if not session_file.exists():
            return []
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [SessionModel(**item) for item in data]
        except Exception:
            return []

    def _save_to_file(self):
        config_path = self._get_config_path()
        config_path.mkdir(parents=True, exist_ok=True)
        session_file = config_path / "sessions.json"
        
        # 파일 권한 설정 (Linux/macOS 전용: 소유자만 읽기/쓰기 가능)
        if platform.system() != "Windows":
            if not session_file.exists():
                session_file.touch(mode=0o600)
            else:
                os.chmod(session_file, 0o600)

        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump([s.dict() for s in self.sessions], f, indent=4, ensure_ascii=False)

    # --- Session Management Methods ---
    def add_session(self, session: SessionModel):
        self.sessions.append(session)
        self.save_sessions()

    def update_session(self, session_id: str, updated_session: SessionModel):
        for i, s in enumerate(self.sessions):
            if s.id == session_id:
                self.sessions[i] = updated_session
                self.save_sessions()
                return True
        return False

    def delete_session(self, session_id: str):
        self.sessions = [s for s in self.sessions if s.id != session_id]
        self.save_sessions()

    def get_session(self, session_id: str) -> Optional[SessionModel]:
        for s in self.sessions:
            if s.id == session_id:
                return s
        return None

# 전역에서 사용할 인스턴스
session_mgr = SessionManager()
