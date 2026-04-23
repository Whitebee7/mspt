# 🚀 MSPT (Modern Secure Pythonic Terminal)

**MSPT** is a lightweight, secure, and modern TUI-based SSH multiplexer. It bridges the gap between complex multiplexers like `tmux` and heavy GUI clients like `Tabby`, providing a seamless "Client-Side Multiplexing" experience directly in your terminal.

---

## 🌟 Why MSPT?

Most multiplexers require server-side installation (like `tmux`) or are heavy desktop applications. **MSPT** runs purely on your local machine, allowing you to manage multiple SSH sessions, switch between them instantly, and restore screen states—even on servers where you can't install additional software.

---

## ✨ Key Features

- 🎨 **Modern Multiplexer UI**: Manage multiple SSH sessions in one terminal window. Switch slots with `Ctrl+T` followed by `1-9`.
- 🔄 **Intelligent Screen Restoration**: Automatically restores your TUI environment (like `vim` or `top`) when switching sessions or returning from the menu.
- 🛡️ **Hardened Security**: No clear-text passwords. Utilizes AES encryption and integrates with OS Native Keychains (Windows Registry, Linux XDG, macOS Keychain).
- 🌐 **Global by Default**: Native support for **9 languages** (English, Korean, Japanese, Chinese, Spanish, French, German, Italian, Russian).
- 🐍 **Zero-Dependency Core**: Built with pure Python, `Paramiko`, and `Rich`. Highly portable and extensible.
- 🖼️ **Layout Stability**: Implements advanced terminal features like **Origin Mode (DECOM)** to protect UI headers from being overwritten by server output.

---

## ⌨️ Multiplexer Hotkeys (Prefix: `Ctrl+T`)

Once connected, press **`Ctrl + T`** to enter Prefix Mode, then:

- **`1 ~ 9`**: Switch instantly to the corresponding session slot.
- **`N` (Next) / `P` (Prev)**: Cycle through active sessions.
- **`C` (Create/Menu)**: Return to the main menu while keeping active connections alive.
- **`X` (Kill)**: Terminate the current session.
- **`Ctrl + T`**: Send a literal `Ctrl + T` to the remote server.

---

## 🛠️ Architecture & How it Works

MSPT is designed with a focus on **portability, security, and stability**. Unlike traditional multiplexers, it manages multiple SSH channels over a single TUI instance on the client side.

### 1. Advanced Terminal Control
MSPT utilizes ANSI escape sequences to maintain layout stability:
- **Origin Mode (DECOM)**: Maps the coordinate `(1,1)` to the start of the scroll region (2nd row), protecting the top header from being overwritten by server output or `clear` commands.
- **Scroll Regions (CSR)**: Restricts scrolling to the lower part of the terminal window, keeping the status bar fixed at the top.
- **Smart Buffer Restoration**: Captures and replays recent terminal state to ensure seamless switching between active sessions (e.g., maintaining your `vim` or `top` state).

### 2. Secure Data Persistence & Encryption
Your sensitive data is protected using industry-standard practices:

- **OS-Native Storage**: 
  - **Windows**: Data is stored in the **Registry** (`HKCU\Software\MSPT`).
  - **Linux/macOS**: Data is stored in `~/.config/mspt/sessions.json` with strict **600 permissions** (Owner read/write only).
- **Two-Layer Encryption**: 
  - **Master Key**: A unique master key is generated and stored in your **System Keychain** (Windows Credential Manager, macOS Keychain, or Linux Secret Service/libsecret) via the `keyring` library. This key never leaves your system.
  - **Session Passwords**: SSH passwords are encrypted using **AES (Fernet)** and stored in the `password_enc` field. They can only be decrypted on the same machine where the Master Key resides.
- **Identity Protection**: SSH usernames are stored in the `user` field, while authentication remains isolated from the plain-text configuration.

### 3. Core Technologies
- **Python 3.6+**
- **Paramiko**: Robust SSHv2 protocol implementation.
- **Rich**: Advanced TUI rendering for the main menu and dashboard.
- **Multi-threading**: Separate threads handle I/O for each session to prevent UI blocking.

---

## 🛠️ Installation

### Prerequisites
- Python 3.6 or higher.

### Quick Start
```bash
# Clone the repository
git clone https://github.com/whitebee/mspt.git
cd mspt

# Install dependencies
pip install -r requirements.txt

# Run MSPT
python main.py
```

---

## 🤝 Contributing

Contributions are welcome! Whether it's reporting a bug, suggesting a feature, or adding a new language translation, feel free to open an Issue or a Pull Request.

---

## 📄 License

This project is licensed under the **MIT License**.

> *"Designed by Choi Inhyeok <whitebee@gmail.com>, Powered by Mulder (AI Assistant)."*
