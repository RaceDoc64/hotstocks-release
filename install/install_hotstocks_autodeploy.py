#!/usr/bin/env python3
"""Einrichtung des Hotstocks-Auto-Deploy-Agenten auf VPS3 (einmalig, danach keine Terminal-Eingaben mehr noetig).

  python3 install_hotstocks_autodeploy.py            -> Trockenlauf: prueft alles, schreibt NICHTS
  python3 install_hotstocks_autodeploy.py --apply    -> installiert Agent + systemd-Timer (alle 10 Minuten), erster Lauf als Trockenlauf
  python3 install_hotstocks_autodeploy.py --uninstall-> Timer/Dienst entfernen (Backups, Zustand und Websites bleiben)

Der Agent holt NUR freigegebene Release-Pakete aus https://github.com/RaceDoc64/hotstocks-release.git (Pull, keine offene Tuer), prueft Pfad, Dateityp,
SHA-256, Skripthosts, sichert jede Aenderung, tauscht atomar, prueft den Origin und rollt bei Fehlern selbst zurueck.
Er beruehrt nur die zwei statischen Site-Ordner, sein Backup- und Zustandsverzeichnis. Nicht: family-office-api, Postgres,
Redis, Caddy/Compose, DNS, Secrets, SSH. Pause jederzeit: touch /etc/hotstocks-autodeploy/PAUSE
"""
import argparse, base64, hashlib, json, os, pathlib, shutil, subprocess, sys, zlib
REPO = "https://github.com/RaceDoc64/hotstocks-release.git"
AGENT_SHA = "af31fe58adb3d060655df63076dd8389884982e246cc6e066e676609289c12cd"
AGENT_B64 = "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"
SITES = {"pharma": {"root": "/opt/joe-platform/apps/pharma-site", "host": "www.pharma-hotstocks.net"},
         "rohstoff": {"root": "/opt/joe-platform/apps/rohstoff-site", "host": "www.rohstoff-hotstocks.net"}}
BIN = pathlib.Path("/opt/hotstocks-autodeploy"); CFG = pathlib.Path("/etc/hotstocks-autodeploy")
STATE = pathlib.Path("/var/lib/hotstocks-autodeploy"); BACKUP = pathlib.Path("/opt/joe-platform/backups/autodeploy")
LOG = pathlib.Path("/opt/joe-platform/logs/infra_change_log.txt")
UNIT = "/etc/systemd/system/hotstocks-autodeploy"
SERVICE = f"""[Unit]
Description=Hotstocks Auto-Deploy (Pull freigegebener Releases)
After=network-online.target docker.service
Wants=network-online.target
[Service]
Type=oneshot
Environment=HOME={STATE}
ExecStart=/usr/bin/python3 {BIN}/agent.py --once
TimeoutStartSec=600
Nice=10
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths={SITES['pharma']['root']} {SITES['rohstoff']['root']} {BACKUP} {STATE} {LOG.parent}
CapabilityBoundingSet=CAP_CHOWN CAP_DAC_OVERRIDE CAP_FOWNER
"""
TIMER = """[Unit]
Description=Hotstocks Auto-Deploy alle 10 Minuten
[Timer]
OnBootSec=3min
OnCalendar=*:0/10
Persistent=true
RandomizedDelaySec=20
[Install]
WantedBy=timers.target
"""
def run(*c, **k):
    return subprocess.run(c, capture_output=True, text=True, **k)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--apply", action="store_true"); ap.add_argument("--uninstall", action="store_true")
    a = ap.parse_args(); ok = True
    def chk(good, msg):
        nonlocal ok; ok &= bool(good); print(("OK   " if good else "FEHL ") + msg)
    chk(os.geteuid() == 0, "als root ausgefuehrt")
    if a.uninstall:
        if os.geteuid() != 0: return 1
        run("systemctl", "disable", "--now", "hotstocks-autodeploy.timer")
        for p in (UNIT + ".service", UNIT + ".timer"): pathlib.Path(p).unlink(missing_ok=True)
        run("systemctl", "daemon-reload"); print("Agent-Timer entfernt. Backups/Zustand/Websites unveraendert."); return 0
    data = zlib.decompress(base64.b64decode(AGENT_B64)); chk(hashlib.sha256(data).hexdigest() == AGENT_SHA, "Agent-Paket intakt " + AGENT_SHA[:12])
    for tool in ("git", "curl", "python3", "systemctl"): chk(shutil.which(tool), f"{tool} vorhanden")
    chk(sys.version_info >= (3, 8), "Python >= 3.8")
    for name, s in SITES.items():
        chk(pathlib.Path(s["root"], "index.html").is_file(), f"{name}: {s['root']}/index.html vorhanden")
        r = run("curl", "-sk", "--resolve", f"{s['host']}:443:127.0.0.1", "-m", "20", "-o", "/dev/null", "-w", "%{http_code}", f"https://{s['host']}/")
        chk(r.stdout.strip() == "200", f"{name}: Origin liefert HTTPS 200 (lokal)")
    r = run("git", "ls-remote", REPO, "HEAD"); chk(r.returncode == 0, "Release-Repo erreichbar (lesend)")
    free = shutil.disk_usage("/opt").free // 2**20; chk(free > 1000, f"freier Platz {free} MiB")
    if not ok: print("ABBRUCH: Voraussetzungen nicht erfuellt, nichts geschrieben."); return 2
    if not a.apply: print("TROCKENLAUF beendet - nichts geschrieben. Mit --apply installieren."); return 0
    for d in (BIN, CFG, STATE, BACKUP): d.mkdir(parents=True, exist_ok=True)
    os.chmod(STATE, 0o700); os.chmod(BACKUP, 0o700)
    (BIN / "agent.py").write_bytes(data); os.chmod(BIN / "agent.py", 0o755)
    cfg = {"repo": REPO, "branch": "main", "sites": SITES, "state_dir": str(STATE), "backup_dir": str(BACKUP), "log_file": str(LOG),
           "max_ops": 60, "max_file_bytes": 6000000, "allow_remove": False}
    (CFG / "config.json").write_text(json.dumps(cfg, indent=1)); os.chmod(CFG / "config.json", 0o644)
    pathlib.Path(UNIT + ".service").write_text(SERVICE); pathlib.Path(UNIT + ".timer").write_text(TIMER)
    r = run("systemd-analyze", "verify", UNIT + ".service"); print("systemd-Pruefung:", (r.stderr.strip() or "ok")[:300])
    print("Erster Lauf (Trockenlauf):"); r = run(sys.executable, str(BIN / "agent.py"), "--dry-run"); print(r.stdout[-1500:], r.stderr[-500:])
    if r.returncode not in (0, 1): print("Trockenlauf fehlgeschlagen - Timer NICHT aktiviert"); return 3
    run("systemctl", "daemon-reload"); e = run("systemctl", "enable", "--now", "hotstocks-autodeploy.timer"); print(e.stdout, e.stderr)
    t = run("systemctl", "list-timers", "hotstocks-autodeploy.timer", "--no-pager"); print(t.stdout)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f: f.write(f"autodeploy-agent installiert (sha {AGENT_SHA[:12]}), Repo {REPO}, Timer alle 10 min; Pause: {CFG}/PAUSE; Entfernen: install --uninstall\n")
    print("ERGEBNIS: INSTALLIERT. Status: python3", BIN / "agent.py", "--status | Pause: touch", CFG / "PAUSE"); return 0
if __name__ == "__main__":
    sys.exit(main())
