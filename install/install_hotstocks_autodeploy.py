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
AGENT_SHA = "de00a93571fe988ff44fac893bd5c311cff1db95bdcf92191f4f186fd8ec49ec"
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
