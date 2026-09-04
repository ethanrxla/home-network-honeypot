import ipaddress
import os
import re
import subprocess
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from mac_vendor_lookup import MacLookup

load_dotenv()

PROJECT_NAME = os.environ.get("PROJECT_NAME", "home-network")
ROUTER_HOST = os.environ.get("ROUTER_HOST", "http://192.168.0.1")
ROUTER_USERNAME = os.environ.get("ROUTER_USERNAME", "admin")
ROUTER_PASSWORD = os.environ.get("ROUTER_PASSWORD", "")
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "").rstrip("/")
INGEST_TOKEN = os.environ.get("INGEST_TOKEN", "")
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "120"))
LAN_SUBNET = ipaddress.ip_network(os.environ.get("LAN_SUBNET", "192.168.0.0/24"))

mac_lookup = MacLookup()

ARP_LINE = re.compile(r"([0-9]{1,3}(?:\.[0-9]{1,3}){3})\s+([0-9a-fA-F]{2}(?:[:-][0-9a-fA-F]{2}){5})")
BROADCAST_MAC = "FF:FF:FF:FF:FF:FF"
MULTICAST_PREFIX = "01:00:5E"


def normalize_mac(mac):
    return mac.replace("-", ":").upper()


def load_vendor_db():
    try:
        mac_lookup.load_vendors()
    except Exception:
        try:
            print("[info] downloading MAC vendor database (first run)...")
            mac_lookup.update_vendors()
        except Exception as e:
            print(f"[warn] could not load/update MAC vendor DB: {e}")


def vendor_for(mac):
    try:
        return mac_lookup.lookup(mac)
    except Exception:
        return ""


def scan_router():
    """Query a TP-Link router (anything supported by tplinkrouterc6u) for
    connected clients, tagged by segment (host wifi / guest wifi / wired / iot).
    Requires ROUTER_HOST/ROUTER_USERNAME/ROUTER_PASSWORD to be set."""
    devices = []
    if not ROUTER_PASSWORD:
        return devices
    try:
        from tplinkrouterc6u import TplinkRouterProvider

        router = TplinkRouterProvider.get_client(ROUTER_HOST, ROUTER_PASSWORD, username=ROUTER_USERNAME)
        router.authorize()
        try:
            status = router.get_status()
            for d in status.devices:
                devices.append(
                    {
                        "mac": normalize_mac(str(d.macaddr)),
                        "ip": str(d.ipaddr),
                        "hostname": d.hostname or "",
                        "connection_type": d.type.value,
                    }
                )
        finally:
            router.logout()
    except Exception as e:
        print(f"[warn] router scan failed: {e}")
    return devices


def scan_arp():
    """Fallback/supplement: read the local ARP table. Windows and Linux both
    support `arp -a` with a similar-enough format for this regex."""
    devices = []
    try:
        out = subprocess.check_output(["arp", "-a"], text=True, timeout=10)
        for line in out.splitlines():
            m = ARP_LINE.search(line)
            if not m:
                continue
            ip, mac = m.group(1), normalize_mac(m.group(2))
            if mac == BROADCAST_MAC or mac.startswith(MULTICAST_PREFIX):
                continue
            try:
                if ipaddress.ip_address(ip) not in LAN_SUBNET:
                    continue
            except ValueError:
                continue
            devices.append({"mac": mac, "ip": ip, "hostname": "", "connection_type": "unknown"})
    except Exception as e:
        print(f"[warn] arp scan failed: {e}")
    return devices


def merge(router_devices, arp_devices):
    by_mac = {}
    for d in arp_devices:
        by_mac[d["mac"]] = d
    for d in router_devices:
        # router data is authoritative (has real connection_type/hostname)
        by_mac[d["mac"]] = {**by_mac.get(d["mac"], {}), **d}
    result = []
    for mac, d in by_mac.items():
        d["vendor"] = vendor_for(mac)
        result.append(d)
    return result


def post_snapshot(devices):
    if not DASHBOARD_URL:
        print("[error] DASHBOARD_URL not set, skipping post")
        return
    try:
        resp = requests.post(
            f"{DASHBOARD_URL}/api/ingest",
            json={"devices": devices, "source": "windows-collector"},
            headers={"Authorization": f"Bearer {INGEST_TOKEN}"},
            timeout=15,
        )
        resp.raise_for_status()
        print(f"[ok] posted {len(devices)} devices -> {resp.json()}")
    except Exception as e:
        print(f"[error] failed to post snapshot: {e}")


def run_once():
    router_devices = scan_router()
    arp_devices = scan_arp()
    devices = merge(router_devices, arp_devices)
    ts = datetime.now(timezone.utc).isoformat()
    print(f"[{ts}] router={len(router_devices)} arp={len(arp_devices)} merged={len(devices)}")
    post_snapshot(devices)


def main():
    load_vendor_db()
    print(f"{PROJECT_NAME} collector starting. Polling every {POLL_SECONDS}s -> {DASHBOARD_URL}")
    while True:
        run_once()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
