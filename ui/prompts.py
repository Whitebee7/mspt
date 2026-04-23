from rich.prompt import Prompt, IntPrompt, Confirm
from rich.console import Console
from core.models import SessionModel
from core.crypto import crypto
from core.i18n import _

console = Console()

def prompt_essential_info(existing_data: SessionModel = None) -> SessionModel:
    """접속에 반드시 필요한 핵심 정보만 입력받음"""
    d = existing_data if existing_data else SessionModel(host="")
    
    name = Prompt.ask(_('prompt_name'), default=d.name)
    host = Prompt.ask(_('prompt_host'), default=d.host)
    if not host: 
        return None
        
    port = IntPrompt.ask(_('prompt_port'), default=d.port)
    user = Prompt.ask(_('prompt_user'), default=d.user)
    
    auth_type_str = Prompt.ask(_('prompt_auth_type'), choices=["1", "2"], default=str(d.auth_type))
    auth_type = int(auth_type_str)
    
    key_path = d.key_path
    password_enc = d.password_enc

    if auth_type == 2:
        key_path = Prompt.ask(_('prompt_key_path'), default=d.key_path)
        password_enc = ""
    else:
        key_path = ""
        password = Prompt.ask(_('prompt_pwd'), password=True, default="")
        if password:
            password_enc = crypto.encrypt(password)

    # 필수 정보만 업데이트된 모델 반환 (나머지는 기본값 유지)
    d.name, d.host, d.port, d.user = name, host, port, user
    d.auth_type, d.key_path, d.password_enc = auth_type, key_path, password_enc
    return d

def prompt_advanced_info(d: SessionModel) -> SessionModel:
    """인코딩, 버퍼, Keep-Alive 등 상세 설정 입력받음"""
    console.print(f"\n[bold blue]{_('title_advanced')}[/bold blue]")
    d.encoding = Prompt.ask(_('prompt_enc'), default=d.encoding)
    d.buffer_size = IntPrompt.ask(_('prompt_buf'), default=d.buffer_size)
    d.keep_alive = IntPrompt.ask(_('prompt_keepalive'), default=d.keep_alive)
    return d

def prompt_session_full(existing_data: SessionModel = None) -> SessionModel:
    """수정 시 사용하는 전체 입력 폼"""
    session = prompt_essential_info(existing_data)
    if session:
        session = prompt_advanced_info(session)
    return session
