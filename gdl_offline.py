#!/usr/bin/env python3
"""
GDLauncher Offline Account Manager
===================================
Injects or removes an offline Minecraft account directly into 
GDLauncher's local database.

Usage:
    python gdl_offline.py add <username>
    python gdl_offline.py remove <username>
    python gdl_offline.py list

Requirements:
    - Python 3.7+
    - GDLauncher Carbon must be CLOSED while running this script
"""

import sys
import os
import platform
import sqlite3
import hashlib
from datetime import datetime, timezone
from pathlib import Path


# --- Colors ---

class Color:
    """ANSI color codes (disabled automatically on Windows without ANSI support)."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    DIM = "\033[2m"

    @classmethod
    def disable(cls):
        for attr in ("RESET", "BOLD", "RED", "GREEN", "YELLOW", "BLUE", "CYAN", "DIM"):
            setattr(cls, attr, "")


def _init_colors():
    """Enable ANSI colors on Windows 10+ and detect dumb terminals."""
    if os.environ.get("NO_COLOR"):
        Color.disable()
        return

    if platform.system() == "Windows":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            # Enable ANSI escape sequences on Windows 10+
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            Color.disable()


_init_colors()


# --- Logging helpers ---

def info(msg: str):
    print(f"  {Color.BLUE}●{Color.RESET} {msg}")


def success(msg: str):
    print(f"  {Color.GREEN}✓{Color.RESET} {msg}")


def warn(msg: str):
    print(f"  {Color.YELLOW}⚠{Color.RESET} {msg}")


def error(msg: str):
    print(f"  {Color.RED}✗{Color.RESET} {msg}")


def header(msg: str):
    print(f"\n  {Color.BOLD}{Color.CYAN}{msg}{Color.RESET}")


# --- UUID Generation ---

def generate_offline_uuid(username: str) -> str:
    """
    Generate a stable offline UUID for a Minecraft username.
    Algorithm: MD5("OfflinePlayer:<username>") with UUID v3 version/variant bits.
    This matches exactly what Minecraft servers use for offline-mode players.
    """
    data = f"OfflinePlayer:{username}".encode("utf-8")
    md5_bytes = hashlib.md5(data).digest()

    # Convert to mutable bytearray
    b = bytearray(md5_bytes)

    # Set UUID version to 3 (name-based MD5)
    b[6] = (b[6] & 0x0F) | 0x30
    # Set variant to RFC 4122
    b[8] = (b[8] & 0x3F) | 0x80

    # Format as UUID string
    return (
        f"{b[0]:02x}{b[1]:02x}{b[2]:02x}{b[3]:02x}-"
        f"{b[4]:02x}{b[5]:02x}-"
        f"{b[6]:02x}{b[7]:02x}-"
        f"{b[8]:02x}{b[9]:02x}-"
        f"{b[10]:02x}{b[11]:02x}{b[12]:02x}{b[13]:02x}{b[14]:02x}{b[15]:02x}"
    )


# ---Database path detection ---

def find_database() -> Path:
    """
    Locate GDLauncher's SQLite database across platforms.

    Logic (mirrors GDLauncher's Electron main process):
      1. Find the Electron userData folder:
           Linux:   $XDG_DATA_HOME/gdlauncher_carbon
           Windows: %APPDATA%/gdlauncher_carbon
           macOS:   ~/Library/Application Support/gdlauncher_carbon
      2. If userData/runtime_path_override exists, read it -> runtime path
      3. Otherwise runtime path = userData/data/
      4. Database = runtime_path/gdl_conf.db
    """
    system = platform.system()

    if system == "Linux":
        base = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    elif system == "Windows":
        base = os.environ.get("APPDATA", "")
        if not base:
            error("Cannot determine %APPDATA% path.")
            sys.exit(1)
    elif system == "Darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        error(f"Unsupported platform: {system}")
        sys.exit(1)

    user_data = Path(base) / "gdlauncher_carbon"
    override_file = user_data / "runtime_path_override"

    if override_file.exists():
        try:
            runtime_path = Path(override_file.read_text().strip())
            info(f"Runtime path override: {Color.DIM}{runtime_path}{Color.RESET}")
        except (OSError, ValueError):
            runtime_path = user_data / "data"
    else:
        runtime_path = user_data / "data"

    return runtime_path / "gdl_conf.db"


# --- Username validation ---

def validate_username(username: str) -> bool:
    """
    Validate a Minecraft username:
    - 3 to 16 characters
    - Only letters, digits, and underscores
    """
    if len(username) < 3 or len(username) > 16:
        return False
    return all(c.isalnum() or c == '_' for c in username)


# --- Database check ---

def check_gdl_not_running():
    warn("Make sure GDLauncher is completely closed before continuing.")
    print()


# --- Commands ---

def cmd_add(username: str):
    """Add an offline account to GDLauncher."""
    header("Adding offline account")
    print()

    # Validate username
    if not validate_username(username):
        error("Invalid username. Must be 3-16 characters, letters/digits/underscores only.")
        sys.exit(1)

    info(f"Username: {Color.BOLD}{username}{Color.RESET}")

    # Generate UUID
    uuid = generate_offline_uuid(username)
    info(f"UUID:     {Color.DIM}{uuid}{Color.RESET}")
    print()

    # Find database
    db_path = find_database()
    info(f"Database: {Color.DIM}{db_path}{Color.RESET}")

    if not db_path.exists():
        error("Database not found. Is GDLauncher installed and has been run at least once ?")
        sys.exit(1)

    check_gdl_not_running()

    # Open database
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
    except sqlite3.Error as e:
        error(f"Cannot open database: {e}")
        sys.exit(1)

    try:
        # Check if account already exists
        cursor.execute("SELECT uuid, username FROM Account WHERE uuid = ?", (uuid,))
        existing = cursor.fetchone()

        if existing:
            warn(f"Account '{existing[1]}' with this UUID already exists.")
            conn.close()
            sys.exit(0)

        # Check if username already taken (different UUID)
        cursor.execute("SELECT uuid, username FROM Account WHERE username = ?", (username,))
        name_taken = cursor.fetchone()

        if name_taken:
            error(f"Username '{username}' is already used by account {name_taken[0]}.")
            conn.close()
            sys.exit(1)

        # Insert the account (lastUsed is stored as milliseconds since epoch)
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

        cursor.execute(
            """INSERT INTO Account (uuid, username, accessToken, lastUsed)
               VALUES (?, ?, NULL, ?)""",
            (uuid, username, now_ms)
        )

        # Set as active account
        cursor.execute(
            "UPDATE AppConfiguration SET activeAccountUuid = ? WHERE id = 0",
            (uuid,)
        )

        conn.commit()
        success(f"Account '{username}' created and set as active!")

    except sqlite3.Error as e:
        error(f"Database error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

    print()
    info("You can now launch GDLauncher ; the offline account will be available.")
    print()


def cmd_remove(username: str):
    """Remove an offline account from GDLauncher."""
    header("Removing offline account")
    print()

    uuid = generate_offline_uuid(username)
    info(f"Username: {Color.BOLD}{username}{Color.RESET}")
    info(f"UUID:     {Color.DIM}{uuid}{Color.RESET}")
    print()

    # Find database
    db_path = find_database()
    info(f"Database: {Color.DIM}{db_path}{Color.RESET}")

    if not db_path.exists():
        error("Database not found.")
        sys.exit(1)

    check_gdl_not_running()

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
    except sqlite3.Error as e:
        error(f"Cannot open database: {e}")
        sys.exit(1)

    try:
        # Check if account exists and is offline (accessToken IS NULL)
        cursor.execute(
            "SELECT username, accessToken FROM Account WHERE uuid = ?",
            (uuid,)
        )
        account = cursor.fetchone()

        if not account:
            error(f"No offline account found for username '{username}'.")
            conn.close()
            sys.exit(1)

        if account[1] is not None:
            error(f"Account '{username}' is a Microsoft account — refusing to delete.")
            conn.close()
            sys.exit(1)

        # Clear active account if it's this one
        cursor.execute(
            "UPDATE AppConfiguration SET activeAccountUuid = NULL WHERE activeAccountUuid = ?",
            (uuid,)
        )

        # Delete the account
        cursor.execute("DELETE FROM Account WHERE uuid = ?", (uuid,))

        conn.commit()
        success(f"Account '{username}' removed.")

    except sqlite3.Error as e:
        error(f"Database error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()

    print()


def cmd_list():
    """List all accounts in GDLauncher."""
    header("GDLauncher accounts")
    print()

    db_path = find_database()

    if not db_path.exists():
        error("Database not found. Is GDLauncher installed?")
        sys.exit(1)

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
    except sqlite3.Error as e:
        error(f"Cannot open database: {e}")
        sys.exit(1)

    try:
        # Get active account
        cursor.execute("SELECT activeAccountUuid FROM AppConfiguration WHERE id = 0")
        row = cursor.fetchone()
        active_uuid = row[0] if row else None

        # List all accounts
        cursor.execute("SELECT uuid, username, accessToken, lastUsed FROM Account ORDER BY lastUsed DESC")
        accounts = cursor.fetchall()

        if not accounts:
            warn("No accounts found.")
            conn.close()
            return

        for uuid, username, access_token, last_used in accounts:
            account_type = f"{Color.GREEN}offline{Color.RESET}" if access_token is None else f"{Color.BLUE}microsoft{Color.RESET}"
            active_marker = f" {Color.YELLOW}← active{Color.RESET}" if uuid == active_uuid else ""

            print(f"    {Color.BOLD}{username}{Color.RESET}  [{account_type}]{active_marker}")
            print(f"    {Color.DIM}{uuid}{Color.RESET}")
            print()

    except sqlite3.Error as e:
        error(f"Database error: {e}")
        sys.exit(1)
    finally:
        conn.close()


# --- Usage ---

def print_usage():
    print(f"""
  {Color.BOLD}GDLauncher Offline Account Manager{Color.RESET}

  {Color.CYAN}Usage:{Color.RESET}
    python {sys.argv[0]} add <username>      Add an offline account
    python {sys.argv[0]} remove <username>   Remove an offline account
    python {sys.argv[0]} list                List all accounts

  {Color.CYAN}Examples:{Color.RESET}
    python {sys.argv[0]} add Steve
    python {sys.argv[0]} remove Steve

  {Color.CYAN}Notes:{Color.RESET}
    - GDLauncher must be closed while running this script !
    - Username: 3-16 characters, letters/digits/underscores only
    - The generated UUID is stable (same username = same UUID every time)
""")


# --- Main ---

def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "add":
        if len(sys.argv) != 3:
            error("Usage: python gdl_offline.py add <username>")
            sys.exit(1)
        cmd_add(sys.argv[2])

    elif command == "remove":
        if len(sys.argv) != 3:
            error("Usage: python gdl_offline.py remove <username>")
            sys.exit(1)
        cmd_remove(sys.argv[2])

    elif command == "list":
        cmd_list()

    elif command in ("-h", "--help", "-help", "help"):
        print_usage()

    else:
        error(f"Unknown command: '{command}'")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
