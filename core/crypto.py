import base64
import keyring
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os

class CryptoManager:
    SERVICE_NAME = "MSPT_Terminal"
    ACCOUNT_NAME = "MasterKey"

    def __init__(self):
        self.fernet = self._initialize_cipher()

    def _initialize_cipher(self) -> Fernet:
        """OS 키체인에서 마스터 키를 가져오거나 새로 생성합니다. 오류 시 로컬 파일 우회."""
        master_key_b64 = None
        try:
            master_key_b64 = keyring.get_password(self.SERVICE_NAME, self.ACCOUNT_NAME)
        except Exception:
            # 키체인 오류 시 로컬 파일 확인
            master_key_b64 = self._get_fallback_key()
        
        if not master_key_b64:
            # 키체인에 없으면 새로 생성 후 저장
            key = Fernet.generate_key()
            master_key_b64 = key.decode('utf-8')
            try:
                keyring.set_password(self.SERVICE_NAME, self.ACCOUNT_NAME, master_key_b64)
            except Exception:
                # 저장 실패 시 로컬 파일에 저장
                self._set_fallback_key(master_key_b64)

        return Fernet(master_key_b64.encode('utf-8'))

    def _get_fallback_key(self) -> str:
        """키체인 실패 시 사용자 홈 디렉토리의 숨김 파일에서 키를 읽어옵니다."""
        from pathlib import Path
        key_file = Path.home() / ".mspt_key"
        if key_file.exists():
            try:
                return key_file.read_text().strip()
            except Exception: return None
        return None

    def _set_fallback_key(self, key_str: str):
        """키체인 실패 시 사용자 홈 디렉토리에 키를 저장합니다. (600 권한)"""
        from pathlib import Path
        key_file = Path.home() / ".mspt_key"
        try:
            key_file.touch(mode=0o600)
            key_file.write_text(key_str)
            if os.name != 'nt':
                os.chmod(key_file, 0o600)
        except Exception:
            pass

    def encrypt(self, plain_text: str) -> str:
        if not plain_text:
            return ""
        return self.fernet.encrypt(plain_text.encode('utf-8')).decode('utf-8')

    def decrypt(self, encrypted_text: str) -> str:
        if not encrypted_text:
            return ""
        try:
            return self.fernet.decrypt(encrypted_text.encode('utf-8')).decode('utf-8')
        except Exception:
            return ""

# 싱글톤 인스턴스 생성
crypto = CryptoManager()