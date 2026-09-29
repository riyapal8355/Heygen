"""Production automated PostgreSQL backup script for HeyZen.

Features:
- Connects via docker exec (containerized) or host pg_dump
- Gzip stream compression
- SHA-256 verification and file size logging
- Automatic retention rotation (prunes backups older than N days)
"""

import argparse
import datetime
import gzip
import hashlib
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


def perform_backup(output_path: Path, container_name: str = "heyzen-postgres") -> Path:
    """Execute pg_dump and stream to gzipped destination."""
    settings = get_settings()
    params = parse_db_url(settings.DATABASE_URL)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Determine execution method: docker exec or local binary
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

    print(f"[*] Starting PostgreSQL backup for database '{params['dbname']}'...")
    print(f"[*] Execution mode: {'Docker container (' + container_name + ')' if use_docker else 'Local pg_dump'}")

    hasher = hashlib.sha256()
    total_bytes = 0

    if use_docker:
        cmd = [
            "docker", "exec",
            "-e", f"PGPASSWORD={params['password']}",
            container_name,
            "pg_dump",
            "-U", params["user"],
            "-d", params["dbname"],
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        if not shutil.which("pg_dump"):
            raise RuntimeError("pg_dump binary not found on PATH and Docker container not accessible.")
        cmd = [
            "pg_dump",
            "-h", params["host"],
            "-p", params["port"],
            "-U", params["user"],
            "-d", params["dbname"],
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
        ]
        env = os.environ.copy()
        env["PGPASSWORD"] = params["password"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)

    with gzip.open(output_path, "wb") as gz_out:
        while True:
            chunk = proc.stdout.read(64 * 1024)
            if not chunk:
                break
            gz_out.write(chunk)
            hasher.update(chunk)
            total_bytes += len(chunk)

    _, stderr = proc.communicate()
    if proc.returncode != 0:
        if output_path.exists():
            output_path.unlink()
        raise RuntimeError(f"pg_dump failed with exit code {proc.returncode}: {stderr.decode('utf-8', errors='replace')}")

    compressed_size = output_path.stat().st_size
    sha256 = hasher.hexdigest()

    print(f"[+] Backup completed successfully:")
    print(f"    Target:      {output_path}")
    print(f"    Raw Size:    {total_bytes:,} bytes")
    print(f"    Gzip Size:   {compressed_size:,} bytes")
    print(f"    SHA-256:     {sha256}")

    return output_path


def prune_old_backups(backup_dir: Path, retention_days: int) -> None:
    """Delete backup archives older than retention threshold."""
    if retention_days <= 0:
        return
    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(days=retention_days)

    for file in backup_dir.glob("heyzen_backup_*.sql.gz"):
        mtime = datetime.datetime.fromtimestamp(file.stat().st_mtime)
        if mtime < cutoff:
            print(f"[-] Pruning expired backup ({retention_days}d retention): {file.name}")
            try:
                file.unlink()
            except Exception as e:
                print(f"[!] Warning: failed to delete {file}: {e}")


def main():
    parser = argparse.ArgumentParser(description="HeyZen Automated PostgreSQL Backup")
    parser.add_argument("--output", type=Path, default=None, help="Custom destination file path (.sql.gz)")
    parser.add_argument("--retention-days", type=int, default=7, help="Days to retain backup files (default: 7)")
    parser.add_argument("--container", type=str, default="heyzen-postgres", help="Docker container name")
    args = parser.parse_args()

    backup_dir = BACKEND_DIR / "backups"
    if args.output:
        dest_path = args.output
    else:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = backup_dir / f"heyzen_backup_{timestamp}.sql.gz"

    try:
        perform_backup(dest_path, container_name=args.container)
        prune_old_backups(backup_dir, retention_days=args.retention_days)
    except Exception as exc:
        print(f"[ERROR] Backup failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
