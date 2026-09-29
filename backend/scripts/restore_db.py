"""Production automated PostgreSQL restore script for HeyZen.

Features:
- Decompresses and restores .sql.gz archives
- Safe confirmation gate (--confirm)
- Connects via docker exec or local psql binary
- Performs post-restore validation query
"""

import argparse
import gzip
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

# Ensure backend directory is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings


def parse_db_url(url: str):
    """Parse postgres connection URL into parameters."""
    clean_url = url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg://", "postgresql://")
    parsed = urlparse(clean_url)
    return {
        "user": parsed.username or "heyzen",
        "password": parsed.password or "",
        "host": parsed.hostname or "127.0.0.1",
        "port": str(parsed.port or 5432),
        "dbname": parsed.path.lstrip("/") or "heyzen",
    }


def find_latest_backup(backup_dir: Path) -> Path:
    """Find the most recently modified backup archive in backup_dir."""
    backups = list(backup_dir.glob("heyzen_backup_*.sql.gz"))
    if not backups:
        raise FileNotFoundError(f"No backup archives found in {backup_dir}")
    backups.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return backups[0]


def perform_restore(backup_file: Path, confirm: bool, container_name: str = "heyzen-postgres") -> None:
    """Decompress and restore archive into target database."""
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file does not exist: {backup_file}")

    settings = get_settings()
    params = parse_db_url(settings.DATABASE_URL)

    if not confirm:
        print("[!] CAUTION: Database restore will overwrite tables and existing state.")
        print(f"[!] Target Database: {params['dbname']} on {params['host']}")
        print(f"[!] Backup Source:   {backup_file}")
        ans = input("Type 'RESTORE' to proceed: ").strip()
        if ans != "RESTORE":
            print("Restore aborted by user.")
            sys.exit(1)

    use_docker = False
    if shutil.which("docker"):
        try:
            res = subprocess.run(
                ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=False,
            )
            if container_name in res.stdout:
                use_docker = True
        except Exception:
            pass

    print(f"[*] Restoring '{backup_file.name}' into database '{params['dbname']}'...")
    print(f"[*] Execution mode: {'Docker container (' + container_name + ')' if use_docker else 'Local psql'}")

    if use_docker:
        cmd = [
            "docker", "exec",
            "-i",
            "-e", f"PGPASSWORD={params['password']}",
            container_name,
            "psql",
            "-U", params["user"],
            "-d", params["dbname"],
            "-q",
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        if not shutil.which("psql"):
            raise RuntimeError("psql binary not found on PATH and Docker container not accessible.")
        cmd = [
            "psql",
            "-h", params["host"],
            "-p", params["port"],
            "-U", params["user"],
            "-d", params["dbname"],
            "-q",
        ]
        env = os.environ.copy()
        env["PGPASSWORD"] = params["password"]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

    with gzip.open(backup_file, "rb") as gz_in:
        while True:
            chunk = gz_in.read(64 * 1024)
            if not chunk:
                break
            proc.stdin.write(chunk)

    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"psql failed with exit code {proc.returncode}: {stderr.decode('utf-8', errors='replace')}")

    print("[+] Database restored successfully.")

    # Validation check
    print("[*] Running post-restore sanity check...")
    val_cmd = (
        ["docker", "exec", "-e", f"PGPASSWORD={params['password']}", container_name, "psql", "-U", params["user"], "-d", params["dbname"], "-t", "-c", "SELECT count(*) FROM workspaces;"]
        if use_docker
        else ["psql", "-h", params["host"], "-p", params["port"], "-U", params["user"], "-d", params["dbname"], "-t", "-c", "SELECT count(*) FROM workspaces;"]
    )
    val_env = os.environ.copy()
    val_env["PGPASSWORD"] = params["password"]
    val_res = subprocess.run(val_cmd, capture_output=True, text=True, env=val_env)
    if val_res.returncode == 0:
        ws_count = val_res.stdout.strip()
        print(f"[+] Post-restore check passed: {ws_count} workspace(s) verified.")
    else:
        print(f"[!] Warning: verification query returned code {val_res.returncode}: {val_res.stderr}")


def main():
    parser = argparse.ArgumentParser(description="HeyZen Automated PostgreSQL Restore")
    parser.add_argument("--input", type=Path, default=None, help="Path to .sql.gz backup archive")
    parser.add_argument("--latest", action="store_true", help="Restore the latest backup in backups/ directory")
    parser.add_argument("--confirm", action="store_true", help="Bypass interactive confirmation prompt")
    parser.add_argument("--container", type=str, default="heyzen-postgres", help="Docker container name")
    args = parser.parse_args()

    backup_dir = BACKEND_DIR / "backups"
    if args.input:
        target_file = args.input
    elif args.latest:
        target_file = find_latest_backup(backup_dir)
    else:
        print("Error: Specify either --input <file.sql.gz> or --latest", file=sys.stderr)
        sys.exit(1)

    try:
        perform_restore(target_file, confirm=args.confirm, container_name=args.container)
    except Exception as exc:
        print(f"[ERROR] Restore failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
