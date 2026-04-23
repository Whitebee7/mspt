import sys
import os

# 현재 디렉토리를 시스템 패스에 추가하여 모듈 임포트 에러 방지
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.cli import run_app

if __name__ == "__main__":
    try:
        # 터미널 색상 출력 강제 활성화 (Windows)
        os.system('')
        run_app()
    except KeyboardInterrupt:
        print("\n프로그램을 강제 종료합니다.")
        sys.exit(0)