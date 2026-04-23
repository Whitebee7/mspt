import os
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from core.session_mgr import session_mgr
from core.ssh import SSHClientManager
from core.models import SessionModel
from core.i18n import _

# [수정 포인트] : 새로 바뀐 함수 이름들을 가져옵니다.
from ui.prompts import prompt_essential_info, prompt_advanced_info, prompt_session_full

console = Console()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_main_menu():
    clear_screen()
    
    title_text = f"[bold cyan]MSPT[/bold cyan] [white]- {_('app_title')}[/white]"
    console.print(Panel(title_text, expand=False, border_style="cyan"))

    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column(_('table_no'), style="dim", width=4, justify="center")
    table.add_column(_('table_name'), style="bold green", min_width=15)
    table.add_column(_('table_host_port'), style="cyan")
    table.add_column(_('table_user'), style="yellow")
    table.add_column(_('table_auth'), justify="center")
    table.add_column(_('table_enc'), justify="center")

    sessions = session_mgr.sessions

    if not sessions:
        table.add_row("", _('session_empty'), "", "", "", "")
    else:
        for idx, s in enumerate(sessions, 1):
            host_port = f"{s.host}:{s.port}"
            user_str = s.user if s.user else f"[dim]{_('user_on_connect')}[/dim]"
            
            if s.auth_type == 2:
                auth_str = f"[blue]{_('auth_key')}[/blue]"
            else:
                auth_str = f"[red]{_('auth_pwd_saved')}[/red]" if s.password_enc else f"[dim]{_('auth_pwd_none')}[/dim]"

            table.add_row(str(idx), s.name, host_port, user_str, auth_str, s.encoding)

    console.print(table)
    
    console.print(f"\n[bold]{_('opt_label')}[/bold]")
    console.print(f"  [cyan]{_('opt_quick')}[/cyan]   [cyan]{_('opt_new')}[/cyan]")
    console.print(f"  [cyan]{_('opt_edit')}[/cyan]   [cyan]{_('opt_del')}[/cyan]")
    
    from core.ssh import mux_instance
    if mux_instance.slots:
        console.print(f"  [cyan]{_('opt_return')}[/cyan]   [red]{_('opt_exit_all')}[/red]")
    else:
        console.print(f"  [cyan]{_('opt_exit')}[/cyan]")
    console.print("[dim]" + "="*60 + "[/dim]")

def run_app():
    while True:
        draw_main_menu()
        choice = Prompt.ask(_('prompt_choice')).strip().lower()

        if choice == 'q':
            from core.ssh import mux_instance
            if mux_instance.slots:
                mux_instance.start()
                continue
            console.print(f"[green]{_('msg_welcome')}[/green]")
            break
            
        elif choice == 'x':
            from core.ssh import mux_instance
            if mux_instance.slots:
                if Confirm.ask(_('msg_ask_exit_all'), default=False):
                    console.print(f"[green]{_('msg_welcome')}[/green]")
                    break
                continue
            else:
                console.print(f"[bold red]{_('msg_invalid')}[/bold red]")
                time.sleep(0.5)
            
        elif choice == '0':
            console.print(f"\n[bold yellow]{_('msg_quick_conn')}[/bold yellow]")
            temp_session = prompt_essential_info()
            if temp_session and temp_session.host:
                if Confirm.ask(_('msg_ask_advanced'), default=False):
                    temp_session = prompt_advanced_info(temp_session)
                
                SSHClientManager().connect(temp_session)
                
        elif choice == 'n':
            console.print(f"\n[bold green]{_('msg_new_reg')}[/bold green]")
            new_session = prompt_essential_info()
            if new_session and new_session.host:
                session_mgr.add_session(new_session)
                console.print(f"[bold green]{_('msg_session_created')}[/bold green]")
                time.sleep(1)
                
        elif choice == 'e':
            if not session_mgr.sessions: continue
            idx_str = Prompt.ask(_('prompt_idx_edit'))
            if idx_str.isdigit() and 1 <= int(idx_str) <= len(session_mgr.sessions):
                target_session = session_mgr.sessions[int(idx_str)-1]
                updated_session = prompt_session_full(target_session)
                if updated_session:
                    session_mgr.update_session(target_session.id, updated_session)
                    console.print(f"[bold green]{_('msg_update_success')}[/bold green]")
                    time.sleep(1)
                
        elif choice == 'd':
            if not session_mgr.sessions: continue
            idx_str = Prompt.ask(_('prompt_idx_del'))
            if idx_str.isdigit() and 1 <= int(idx_str) <= len(session_mgr.sessions):
                target_session = session_mgr.sessions[int(idx_str)-1]
                confirm = Prompt.ask(_('msg_ask_del').format(target_session.name), choices=["y", "n"])
                if confirm == 'y':
                    session_mgr.delete_session(target_session.id)
                    console.print(f"[bold red]🗑️ {_('msg_del_success')}[/bold red]")
                    time.sleep(1)
                    
        elif choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(session_mgr.sessions):
                selected_session = session_mgr.sessions[idx-1]
                
                # 이미 슬롯에 있는지 확인
                from core.ssh import mux_instance
                is_connected = any(s.model.id == selected_session.id for s in mux_instance.slots)
                
                force_new = False
                if is_connected:
                    dup_choice = Prompt.ask(_('msg_ask_duplicate'), choices=["1", "2"], default="1")
                    if dup_choice == "2":
                        force_new = True
                
                SSHClientManager().connect(selected_session, force_new=force_new)
        else:
            console.print(f"[bold red]{_('msg_invalid')}[/bold red]")
            time.sleep(0.5)
