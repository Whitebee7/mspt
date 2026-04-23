import sys
import os
import threading
import time
import shutil
import paramiko
import getpass
import codecs
import re
import signal
from collections import deque
from rich.console import Console
from core.models import SessionModel
from core.i18n import _
from core.crypto import crypto

console = Console()

def get_visual_width(text):
    """문자열의 시각적 너비 계산 (CJK 대응)"""
    width = 0
    for char in text:
        if ord(char) > 0x7F: width += 2
        else: width += 1
    return width

def truncate_by_width(text, max_width):
    """시각적 너비를 기준으로 문자열 절단"""
    current_width = 0
    result = ""
    for char in text:
        char_width = 2 if ord(char) > 0x7F else 1
        if current_width + char_width > max_width:
            break
        result += char
        current_width += char_width
    return result

class SSHTerminalSession:
    def __init__(self, session_model: SessionModel):
        self.model = session_model
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.chan = None
        self.is_active = False
        self.decoder = codecs.getincrementaldecoder(session_model.encoding)(errors='replace')
        # 화면 복원용 버퍼 (최근 15000바이트)
        self.screen_buffer = deque(maxlen=15000)

    def connect(self):
        try:
            username = self.model.user or input(f"[{self.model.host}] Username: ").strip()
            params = {
                "hostname": self.model.host, "port": self.model.port,
                "username": username, "timeout": 10,
                "look_for_keys": False, "allow_agent": False
            }
            if self.model.auth_type == 2 and self.model.key_path:
                params["key_filename"] = self.model.key_path
            else:
                pwd = crypto.decrypt(self.password_enc if hasattr(self, 'password_enc') else self.model.password_enc) or getpass.getpass(f"[{username}@{self.model.host}] Password: ")
                params["password"] = pwd

            self.client.connect(**params)
            if self.model.keep_alive > 0:
                self.client.get_transport().set_keepalive(self.model.keep_alive)
            
            size = shutil.get_terminal_size()
            self.chan = self.client.get_transport().open_session()
            # 헤더 공간(1행) 제외
            self.chan.get_pty(term='xterm', width=size.columns, height=max(size.lines - 1, 1))
            self.chan.invoke_shell()
            self.is_active = True
            return True
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return False

    def close(self):
        self.is_active = False
        if self.chan: self.chan.close()
        self.client.close()

    def resize_pty(self, width, height):
        """서버에 터미널 크기 변경 알림"""
        if self.is_active and self.chan:
            try:
                self.chan.resize_pty(width=width, height=height)
            except: pass

class Multiplexer:
    def __init__(self):
        self.slots = []
        self.current_idx = -1
        self.prefix_mode = False
        self.running = False
        self.return_to_menu = False
        self._setup_signals()

    def _setup_signals(self):
        """윈도우 리사이즈 시그널 설정"""
        if os.name != 'nt':
            signal.signal(signal.SIGWINCH, self._on_resize)
        
    def _on_resize(self, signum=None, frame=None):
        """터미널 크기 변경 시 모든 세션에 알림 및 UI 재배치"""
        if not self.running: return
        size = shutil.get_terminal_size()
        new_h = max(size.lines - 1, 1)
        for slot in self.slots:
            slot.resize_pty(size.columns, new_h)
        
        # UI 강제 재드로잉
        self._setup_terminal()
        self._draw_header()

    def _get_header_text(self):
        size = shutil.get_terminal_size()
        cols = size.columns
        
        if not self.prefix_mode:
            # 평상시 모드
            active_slot = self.slots[self.current_idx]
            max_n_len = max(cols - 25, 5)
            name = truncate_by_width(active_slot.model.name, max_n_len)
            header_base = f" MSPT - {self.current_idx+1}:{name} [Ctrl-T]"
        else:
            # 프리픽스 모드 가이드
            guide = " (1-9 or C:Menu, P:Prev, N:Next, X:Kill)"
            available_for_slots = cols - 46
            num_slots = len(self.slots)
            
            if num_slots > 0:
                slot_width = max(available_for_slots // num_slots, 4)
                max_name_per_slot = max(slot_width - 5, 0)
            else:
                max_name_per_slot = 0

            parts = []
            for i, slot in enumerate(self.slots):
                name = truncate_by_width(slot.model.name, max_name_per_slot)
                if i == self.current_idx:
                    parts.append(f"\x1b[1;37;42m {i+1}:{name} \x1b[0;44;37m")
                else:
                    parts.append(f" {i+1}:{name} ")
            
            header_base = f" MSPT {'|'.join(parts)}{guide}"
        
        return f"\x1b[44;37m{header_base}\x1b[K\x1b[0m"

    def _draw_header(self):
        """1행에 헤더 고정 출력. DECOM 해제 후 출력하여 절대 좌표 보장."""
        header = self._get_header_text()
        # \x1b7: 커서 저장, \x1b[?6l: DECOM Off, \x1b[1;1H: 1행1열 이동, \x1b[?6h: DECOM On(원복), \x1b8: 커서 복구
        sys.stdout.write(f"\x1b7\x1b[?6l\x1b[1;1H{header}\x1b[?6h\x1b8")
        sys.stdout.flush()

    def _setup_terminal(self):
        """스크롤 영역(2행~끝) 설정 및 Origin Mode(DECOM) 활성화"""
        size = shutil.get_terminal_size()
        # \x1b[2;{size.lines}r: CSR 설정, \x1b[?6h: DECOM On (1,1이 실제로는 2,1이 됨)
        sys.stdout.write(f"\x1b[2;{size.lines}r\x1b[?6h\x1b[H")
        sys.stdout.flush()

    def _reset_terminal(self):
        """스크롤 영역 초기화 및 DECOM 해제"""
        sys.stdout.write("\x1b[?6l\x1b[r\x1b[H\x1b[2J") 
        sys.stdout.flush()

    def _restore_screen(self, slot):
        """세션의 버퍼를 기반으로 화면을 복구함"""
        if not slot.screen_buffer:
            return

        # 1. 작업 영역 초기화 (DECOM 상태이므로 1,1 이동 후 끝까지 지우면 작업 영역만 지워짐)
        sys.stdout.write("\x1b[H\x1b[J")
        sys.stdout.flush()

        raw_data = bytes(slot.screen_buffer)
        # 버퍼 내에서 레이아웃을 파괴할 수 있는 코드 제거 (CSR 초기화, DECOM 해제 등)
        filtered_data = raw_data.replace(b'\x1b[r', b'').replace(b'\x1b[?6l', b'')
        
        try:
            temp_decoder = codecs.getincrementaldecoder(slot.model.encoding)(errors='replace')
            sys.stdout.write(temp_decoder.decode(filtered_data, final=True))
            sys.stdout.flush()
        except: pass

    def _display_loop(self):
        while self.running:
            if 0 <= self.current_idx < len(self.slots):
                active_slot = self.slots[self.current_idx]
                if active_slot.chan and active_slot.chan.exit_status_ready():
                    self._kill_current_session()
                    continue

                if active_slot.chan and active_slot.chan.recv_ready():
                    try:
                        data = active_slot.chan.recv(active_slot.model.buffer_size)
                        if data:
                            active_slot.screen_buffer.extend(data)
                            text = active_slot.decoder.decode(data)
                            sys.stdout.write(text)
                            sys.stdout.flush()
                            # 2J(전체삭제) 등 발생 시 헤더가 지워질 수 있는 터미널 대응
                            if "\x1b[2J" in text or "\x1b[J" in text:
                                self._draw_header()
                    except: pass
            time.sleep(0.001)

    def _input_loop(self):
        if os.name == 'nt':
            import msvcrt
            while self.running:
                if msvcrt.kbhit():
                    char = msvcrt.getch()
                    if char == b'\x14': # Ctrl+T
                        self._handle_prefix_trigger()
                    else:
                        self._handle_key(char)
                time.sleep(0.01)
        else:
            import termios, tty, select
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while self.running:
                    r, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if sys.stdin in r:
                        char = sys.stdin.read(1).encode()
                        if char == b'\x14': # Ctrl+T
                            self._handle_prefix_trigger()
                        else:
                            self._handle_key(char)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def _handle_prefix_trigger(self):
        self.prefix_mode = not self.prefix_mode
        self._draw_header()

    def _handle_key(self, char):
        if self.prefix_mode:
            cmd = char.lower()
            if b'1' <= cmd <= b'9':
                target_idx = int(cmd) - 1
                if target_idx < len(self.slots):
                    self._switch_session(target_idx)
            elif cmd == b'n': self._switch_session((self.current_idx + 1) % len(self.slots))
            elif cmd == b'p': self._switch_session((self.current_idx - 1) % len(self.slots))
            elif cmd == b'x': self._kill_current_session()
            elif cmd in (b'c', b' ', b'\x14'):
                self.running = False
                self.return_to_menu = True
            
            self.prefix_mode = False
            self._draw_header()
            return

        self._send_to_active(char)

    def _send_to_active(self, data):
        if 0 <= self.current_idx < len(self.slots):
            try:
                self.slots[self.current_idx].chan.send(data)
            except: pass

    def _switch_session(self, idx):
        if 0 <= idx < len(self.slots):
            time.sleep(0.05)
            self.current_idx = idx
            
            # 1. 화면 초기화 및 CSR/DECOM 재설정
            sys.stdout.write("\x1b[r\x1b[H\x1b[2J") 
            sys.stdout.flush()
            self._setup_terminal()
            
            # 2. 버퍼 기반 화면 복원 수행 후 헤더를 마지막에 그림
            self._restore_screen(self.slots[idx])
            self._draw_header()

    def _kill_current_session(self):
        if 0 <= self.current_idx < len(self.slots):
            slot = self.slots.pop(self.current_idx)
            slot.close()
            if not self.slots:
                self.running = False
            else:
                self.current_idx = min(self.current_idx, len(self.slots) - 1)
                self._switch_session(self.current_idx)

    def start(self, initial_session: SessionModel = None, force_new=False):
        is_existing = False
        if initial_session:
            existing_slot_idx = -1
            if not force_new:
                for i, s in enumerate(self.slots):
                    if s.model.id == initial_session.id:
                        existing_slot_idx = i
                        break
            if existing_slot_idx >= 0:
                self.current_idx = existing_slot_idx
                is_existing = True
            else:
                new_slot = SSHTerminalSession(initial_session)
                if new_slot.connect():
                    self.slots.append(new_slot)
                    self.current_idx = len(self.slots) - 1
        
        if not self.slots: return False

        self.running = True
        self.return_to_menu = False
        
        sys.stdout.write("\x1b[r\x1b[H\x1b[2J")
        self._setup_terminal()

        # 기존 세션이거나, 파라미터 없이 재개하는 경우 화면 복원 수행
        if is_existing or not initial_session:
            if 0 <= self.current_idx < len(self.slots):
                self._restore_screen(self.slots[self.current_idx])
        
        self._draw_header()

        display_thread = threading.Thread(target=self._display_loop, daemon=True)
        display_thread.start()
        
        try:
            self._input_loop()
        finally:
            self.running = False
            self._reset_terminal()
        
        return self.return_to_menu

mux_instance = Multiplexer()

class SSHClientManager:
    def connect(self, session: SessionModel, force_new=False):
        return mux_instance.start(session, force_new=force_new)
