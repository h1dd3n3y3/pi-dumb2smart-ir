#!/usr/bin/env python3
"""Interactive IR remote controller for ANAVI IR pHAT.

Hardware:  ANAVI IR pHAT on Raspberry Pi Zero 2W
TX GPIO:   17 (IR LED)
RX GPIO:   18 (IR receiver)
Backend:   pigpiod + PiIR

Usage:
    python3 remote.py [device.json]
"""

import glob
import json
import os
import subprocess
import sys

TX_GPIO = 17
RX_GPIO = 18


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_pigpiod() -> bool:
    """Return True if pigpiod is reachable; print a warning otherwise."""
    try:
        import pigpio  # type: ignore
        pi = pigpio.pi()
        if pi.connected:
            pi.stop()
            return True
        pi.stop()
    except Exception:
        pass
    print(
        "\n[WARNING] Cannot connect to pigpiod.\n"
        "  Start it with:  sudo pigpiod\n"
        "  Or enable at boot:  sudo systemctl enable pigpiod && sudo systemctl start pigpiod\n"
    )
    return False


def _discover_devices() -> list[str]:
    """Return sorted list of *.json files in the script's directory."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return sorted(glob.glob(os.path.join(script_dir, "*.json")))


def _load_keys(device_path: str) -> dict:
    """Return the 'keys' dict from a device JSON file, or {} on error."""
    try:
        with open(device_path, "r") as f:
            data = json.load(f)
        return data.get("keys", {})
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Could not parse {os.path.basename(device_path)}: {exc}")
        return {}


def _short_name(path: str) -> str:
    return os.path.basename(path)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def action_select_device(current: str | None) -> str | None:
    """Let the user pick an existing device or name a new one."""
    devices = _discover_devices()
    print()
    if devices:
        print("Available devices:")
        for i, d in enumerate(devices, 1):
            keys = _load_keys(d)
            marker = " <-- current" if d == current else ""
            print(f"  {i}. {_short_name(d)}  ({len(keys)} key(s)){marker}")
        print(f"  {len(devices) + 1}. Enter a new filename")
    else:
        print("  No device files found in this directory.")
        print("  1. Enter a new filename")

    try:
        choice = input("\nChoice: ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return current

    # Numerical selection of existing device
    if devices and choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(devices):
            selected = devices[idx - 1]
            print(f"Device set to: {_short_name(selected)}")
            return selected

    # New filename
    if not choice.isdigit() or (devices and int(choice) == len(devices) + 1) or (not devices and choice == "1"):
        raw = choice if not choice.isdigit() else ""
        if not raw:
            try:
                raw = input("  New device filename (e.g. samsung.json): ").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                return current
        if not raw:
            return current
        if not raw.endswith(".json"):
            raw += ".json"
        script_dir = os.path.dirname(os.path.abspath(__file__))
        new_path = os.path.join(script_dir, raw)
        print(f"Device set to: {_short_name(new_path)}  (will be created on first record)")
        return new_path

    print("Invalid choice.")
    return current


def action_record_key(device_path: str) -> None:
    """Use the piir CLI to record a named key into device_path."""
    if not device_path:
        print("[ERROR] No device selected.")
        return

    try:
        key_name = input("Key name: ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return

    if not key_name:
        print("Key name cannot be empty.")
        return

    print(f"\nReady to record '{key_name}' — point your remote at the pHAT and press the button.")
    print("Press Enter when ready (or Ctrl-C to cancel)...")
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return

    cmd = ["piir", "record", "--gpio", str(RX_GPIO), "--file", device_path, key_name]
    try:
        result = subprocess.run(cmd, timeout=30)
        if result.returncode == 0:
            print(f"  Recorded '{key_name}' -> {_short_name(device_path)}")
        else:
            print(f"  [ERROR] piir exited with code {result.returncode}")
    except FileNotFoundError:
        print(
            "[ERROR] 'piir' command not found.\n"
            "  Ensure ~/.local/bin is in PATH:\n"
            "    export PATH=$HOME/.local/bin:$PATH"
        )
    except subprocess.TimeoutExpired:
        print("[ERROR] Timed out waiting for IR signal (30 s).")


def action_send_key(device_path: str) -> None:
    """Send a key from device_path using the piir Python API."""
    if not device_path:
        print("[ERROR] No device selected.")
        return

    keys = _load_keys(device_path)
    if not keys:
        print(f"  No keys found in {_short_name(device_path)}.")
        return

    key_list = sorted(keys.keys())
    print()
    for i, k in enumerate(key_list, 1):
        print(f"  {i}. {k}")

    try:
        choice = input("\nKey to send: ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return

    # Accept number or name
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(key_list):
            key_name = key_list[idx - 1]
        else:
            print("Invalid choice.")
            return
    elif choice in keys:
        key_name = choice
    else:
        print(f"Key '{choice}' not found.")
        return

    repeat_raw = input(f"Repeat count [1]: ").strip()
    repeat = int(repeat_raw) if repeat_raw.isdigit() and int(repeat_raw) > 0 else 1

    try:
        import piir  # type: ignore
        remote = piir.Remote(device_path, TX_GPIO)
        remote.send(key_name, repeat=repeat)
        print(f"  Sent '{key_name}' x{repeat}")
    except Exception as exc:
        print(f"[ERROR] Failed to send: {exc}")


def action_list_keys(device_path: str) -> None:
    """Print all key names and their hex data from device_path."""
    if not device_path:
        print("[ERROR] No device selected.")
        return

    keys = _load_keys(device_path)
    if not keys:
        print(f"  No keys in {_short_name(device_path)}.")
        return

    print(f"\n  {_short_name(device_path)}  ({len(keys)} key(s))")
    print("  " + "-" * 40)
    for name, data in sorted(keys.items()):
        print(f"  {name:<20} {data}")


def _pick_key(device_path: str, prompt: str = "Key: ") -> str | None:
    """Print key list and return the chosen key name, or None on cancel."""
    keys = _load_keys(device_path)
    if not keys:
        print(f"  No keys in {_short_name(device_path)}.")
        return None

    key_list = sorted(keys.keys())
    print()
    for i, k in enumerate(key_list, 1):
        print(f"  {i}. {k}")

    try:
        choice = input(f"\n{prompt}").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return None

    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(key_list):
            return key_list[idx - 1]
        print("Invalid choice.")
        return None
    if choice in keys:
        return choice
    print(f"Key '{choice}' not found.")
    return None


def _save_keys(device_path: str, keys: dict) -> None:
    try:
        with open(device_path, "r") as f:
            data = json.load(f)
    except Exception:
        data = {}
    data["keys"] = keys
    with open(device_path, "w") as f:
        json.dump(data, f, indent=2)


def action_edit_key(device_path: str) -> None:
    """Rename, re-record, or delete a key."""
    if not device_path:
        print("[ERROR] No device selected.")
        return

    keys = _load_keys(device_path)
    if not keys:
        print(f"  No keys in {_short_name(device_path)}.")
        return

    print()
    print("  1. Rename a key")
    print("  2. Re-record a key")
    print("  3. Delete a key")

    try:
        choice = input("\nChoice: ").strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return

    if choice == "1":
        key_name = _pick_key(device_path, "Key to rename: ")
        if not key_name:
            return
        try:
            new_name = input(f"New name for '{key_name}': ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            return
        if not new_name:
            print("Name cannot be empty.")
            return
        if new_name in keys:
            print(f"Key '{new_name}' already exists.")
            return
        keys[new_name] = keys.pop(key_name)
        _save_keys(device_path, keys)
        print(f"  Renamed '{key_name}' -> '{new_name}'")

    elif choice == "2":
        key_name = _pick_key(device_path, "Key to re-record: ")
        if not key_name:
            return
        print(f"\nReady to re-record '{key_name}' — point your remote at the pHAT and press the button.")
        print("Press Enter when ready (or Ctrl-C to cancel)...")
        try:
            input()
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return
        cmd = ["piir", "record", "--gpio", str(RX_GPIO), "--file", device_path, key_name]
        try:
            result = subprocess.run(cmd, timeout=30)
            if result.returncode == 0:
                print(f"  Re-recorded '{key_name}'")
            else:
                print(f"  [ERROR] piir exited with code {result.returncode}")
        except FileNotFoundError:
            print("[ERROR] 'piir' command not found.")
        except subprocess.TimeoutExpired:
            print("[ERROR] Timed out waiting for IR signal (30 s).")

    elif choice == "3":
        key_name = _pick_key(device_path, "Key to delete: ")
        if not key_name:
            return
        try:
            confirm = input(f"Delete '{key_name}'? [y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return
        if confirm == "y":
            keys.pop(key_name)
            _save_keys(device_path, keys)
            print(f"  Deleted '{key_name}'")
        else:
            print("  Cancelled.")

    else:
        print("Invalid choice.")


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 42)
    print("   IR Remote Controller — ANAVI pHAT")
    print("=" * 42)

    _check_pigpiod()

    # Allow optional initial device as CLI arg
    current_device: str | None = None
    if len(sys.argv) > 1:
        candidate = sys.argv[1]
        if not os.path.isabs(candidate):
            candidate = os.path.join(os.path.dirname(os.path.abspath(__file__)), candidate)
        current_device = candidate
    else:
        devices = _discover_devices()
        if len(devices) == 1:
            current_device = devices[0]
            print(f"Auto-selected device: {_short_name(current_device)}")

    while True:
        print()
        if current_device:
            keys = _load_keys(current_device)
            print(f"  Device : {_short_name(current_device)}  ({len(keys)} key(s))")
        else:
            print("  Device : (none selected)")
        print()
        print("  1. Select device")
        print("  2. Record a key")
        print("  3. Send a key")
        print("  4. List keys")
        print("  5. Edit a key")
        print("  6. Quit")
        print()

        try:
            choice = input("Choice: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if choice == "1":
            current_device = action_select_device(current_device)
        elif choice == "2":
            if not current_device:
                print("Select a device first (option 1).")
            else:
                action_record_key(current_device)
        elif choice == "3":
            action_send_key(current_device)
        elif choice == "4":
            action_list_keys(current_device)
        elif choice == "5":
            if not current_device:
                print("Select a device first (option 1).")
            else:
                action_edit_key(current_device)
        elif choice == "6":
            print("Exiting.")
            break
        else:
            print("Invalid choice, enter 1-6.")


if __name__ == "__main__":
    main()
