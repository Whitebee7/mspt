import uuid
from pydantic import BaseModel, Field

class SessionModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(default="새 연결")
    host: str = Field(..., description="접속할 IP 또는 도메인")
    port: int = Field(default=22)
    user: str = Field(default="")
    
    auth_type: int = Field(default=1)
    key_path: str = Field(default="")
    password_enc: str = Field(default="")
    
    # 고급 설정 기본값
    encoding: str = Field(default="utf-8")
    buffer_size: int = Field(default=2000)
    keep_alive: int = Field(default=0)  # 보안을 위해 기본값 0 (비활성화)

    class Config:
        validate_assignment = True