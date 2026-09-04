# Cowrie command intercept — routes attacker commands through the tiered
# sensor-agent response system (src/cowrie/commands/sensor_agent/) instead of
# Cowrie's built-in emulated commands. See sensor_agent/shell_broker.py for
# the tier design (local lookup table -> local LLM -> cloud LLM -> stub).

from __future__ import annotations

import os
import sys

from cowrie.core.config import CowrieConfig
from cowrie.shell.command import HoneyPotCommand

_AGENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sensor_agent")
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)

try:
    from shell_broker import handle_command

    _READY = True
except Exception:
    _READY = False

# Commands routed through the sensor agent; anything else falls through to
# Cowrie's normal built-in command handlers.
INTERCEPTED_COMMANDS = {
    "uname", "hostname", "whoami", "id", "uptime",
    "lscpu", "lsb_release", "hostnamectl", "timedatectl",
    "ip", "ss", "netstat", "iptables", "systemctl",
    "ps", "free", "df", "du",
    "apt", "apt-get", "dpkg",
    "find", "locate", "updatedb",
    "journalctl", "dmesg",
    "stat", "readlink",
    "type", "command", "alias",
    "date", "w", "who", "last", "lastlog",
    "top", "pgrep", "pidof", "ifconfig", "arp", "route",
    "ls", "ll", "cat", "head", "tail", "wc", "grep",
    "touch", "mkdir", "rm", "cp", "mv", "cd", "pwd",
    "env", "printenv", "export", "history",
    "mount", "lsblk", "service", "crontab", "sudo", "su",
}


def _enabled() -> bool:
    try:
        return CowrieConfig.getboolean("honeypot", "enable_sensor_agent", fallback=True)
    except Exception:
        return True


def _make_command_class(cmd_name: str) -> type:
    """Build a distinct HoneyPotCommand subclass per intercepted command name.
    A single shared class can't tell which command invoked it (Cowrie doesn't
    pass that in) — so cmd_name is closed over here instead of guessed later
    from the class name."""

    def call(self) -> None:
        cmd_full = f"{cmd_name} {' '.join(self.args)}".strip() if self.args else cmd_name

        if not _READY or not _enabled():
            self.write(f"bash: {cmd_name}: command not found\n")
            self.exit()
            return

        try:
            session_id = str(id(self.protocol))
            attacker_ip = getattr(self.protocol, "clientIP", "unknown")
            response = handle_command(cmd_full, session_id, attacker_ip)
            if response:
                self.write(response + "\n")
        except Exception:
            self.write(f"bash: {cmd_name}: command not found\n")

        self.exit()

    return type(f"SensorAgentCommand_{cmd_name}", (HoneyPotCommand,), {"call": call})


commands = {cmd: _make_command_class(cmd) for cmd in INTERCEPTED_COMMANDS}
