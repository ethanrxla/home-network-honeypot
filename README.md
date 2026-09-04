# Home Network Honeypot Collector

A small collector for home-lab network monitoring: polls your router for
connected clients, tags devices by network segment (main wifi / guest wifi /
wired), and ships snapshots to a dashboard so you can watch what joins your
guest network. Point the guest SSID's password at something weak/public
("Free WiFi", etc.) and it doubles as a low-effort honeypot — anything that
shows up there is worth a look.

Built against a TP-Link router via [tplinkrouterc6u](https://github.com/AlexandrErohin/TP-Link-Archer-C6U),
which supports a range of TP-Link Archer/Deco models. If your router isn't
supported, `scan_arp()` (reading the local ARP table) still works as a
fallback/supplement, or you can add another backend.

## What it does

- `collector/collector.py` — polls the router on an interval, merges results
  with the local ARP table, resolves MAC vendors, and POSTs a JSON snapshot
  to `DASHBOARD_URL/api/ingest`.
- `collector/scratch/` — small one-off scripts used to explore what your
  router's admin API exposes for guest-network / client-isolation settings
  (handy when setting this up against a router model for the first time).

This repo does **not** include a dashboard server — bring your own endpoint
that accepts `POST /api/ingest` with `{"devices": [...], "source": "..."}`
and a `Bearer` token, or adapt `post_snapshot()` to whatever you're using.

## Setup

```bash
cd collector
python -m venv .venv
.venv/Scripts/activate   # or `source .venv/bin/activate` on Linux/macOS
pip install -r requirements.txt
cp .env.example .env
# edit .env with your router's admin credentials and your dashboard URL/token
python collector.py
```

## Configuration (`.env`)

| Variable | Description |
|---|---|
| `PROJECT_NAME` | Label printed in logs, cosmetic only |
| `ROUTER_HOST` | Router admin URL, e.g. `http://192.168.0.1` |
| `ROUTER_USERNAME` / `ROUTER_PASSWORD` | Router admin login |
| `DASHBOARD_URL` | Where snapshots get POSTed |
| `INGEST_TOKEN` | Bearer token for the dashboard's ingest endpoint |
| `POLL_SECONDS` | Poll interval, default 120 |
| `LAN_SUBNET` | Subnet used to filter the ARP fallback scan |

**Set up guest-network client isolation on your router first** if you're
using this as a honeypot — you want joining devices logged and observed, not
able to reach the rest of your LAN. The `scratch/` scripts can help confirm
your router's isolation settings are actually on.

## Safety / scope

This is meant for your own network that you administer. Don't point it at a
network you don't own or don't have permission to monitor.
