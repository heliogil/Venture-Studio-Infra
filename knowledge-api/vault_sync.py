"""
knowledge-api/vault_sync.py
Sincroniza vault Obsidian do Dropbox para /vault no VPS.
Após sync, indexa ficheiros novos/modificados via knowledge-api.
Loop: a cada SYNC_INTERVAL_SECONDS (default: 900 = 15 min).
"""
import dropbox
import dropbox.files
import os
import json
import time
import logging
import httpx
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

DROPBOX_CREDS = os.environ.get("DROPBOX_CREDS", "/secrets/dropbox.json")
VAULT_PATH = Path(os.environ.get("VAULT_PATH", "/vault"))
VAULT_DROPBOX_PATH = os.environ.get("VAULT_DROPBOX_PATH", "/Obsidian")
KNOWLEDGE_API_URL = os.environ.get("KNOWLEDGE_API_URL", "http://vs_knowledge_api:8000")
SYNC_INTERVAL = int(os.environ.get("SYNC_INTERVAL_SECONDS", "900"))


def get_dbx() -> dropbox.Dropbox:
    with open(DROPBOX_CREDS) as f:
        creds = json.load(f)
    return dropbox.Dropbox(
        oauth2_refresh_token=creds["refresh_token"],
        app_key=creds["app_key"],
        app_secret=creds["app_secret"],
    )


def sync_vault(dbx: dropbox.Dropbox) -> list:
    """Sincroniza .md do Dropbox para VAULT_PATH. Retorna lista de paths actualizados."""
    VAULT_PATH.mkdir(parents=True, exist_ok=True)
    updated = []

    try:
        result = dbx.files_list_folder(VAULT_DROPBOX_PATH, recursive=True)
    except dropbox.exceptions.ApiError as e:
        logger.error(f"Dropbox API error: {e}")
        return []

    while True:
        for entry in result.entries:
            if not isinstance(entry, dropbox.files.FileMetadata):
                continue
            if not entry.name.endswith(".md"):
                continue

            rel_path = entry.path_lower.replace(
                VAULT_DROPBOX_PATH.lower() + "/", "", 1
            )
            local_path = VAULT_PATH / rel_path
            local_path.parent.mkdir(parents=True, exist_ok=True)

            if local_path.exists():
                local_mtime = local_path.stat().st_mtime
                remote_mtime = entry.server_modified.timestamp()
                if local_mtime >= remote_mtime:
                    continue

            dbx.files_download_to_file(str(local_path), entry.path_lower)
            updated.append(str(local_path))
            logger.info(f"Synced: {entry.path_lower}")

        if not result.has_more:
            break
        result = dbx.files_list_folder_continue(result.cursor)

    return updated


def index_files(file_paths: list) -> None:
    """Envia ficheiros para knowledge-api indexar."""
    for path in file_paths:
        try:
            content = Path(path).read_text(encoding="utf-8", errors="replace")
            if len(content.strip()) < 50:
                continue

            title = Path(path).stem
            source_path = "vault:/" + path.replace(str(VAULT_PATH) + "/", "")

            with httpx.Client(timeout=60) as http:
                resp = http.post(
                    f"{KNOWLEDGE_API_URL}/index",
                    json={
                        "source_path": source_path,
                        "title": title,
                        "content": content,
                        "metadata": {"file_path": path},
                    },
                )
                if resp.status_code == 200:
                    logger.info(f"Indexed: {title}")
                else:
                    logger.warning(f"Index failed {path}: {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Error indexing {path}: {e}")


def main():
    logger.info(
        f"Vault sync started. Dropbox: {VAULT_DROPBOX_PATH} → Local: {VAULT_PATH}"
    )
    logger.info(f"Sync interval: {SYNC_INTERVAL}s ({SYNC_INTERVAL // 60}min)")

    while True:
        try:
            dbx = get_dbx()
            updated = sync_vault(dbx)
            logger.info(f"Sync complete: {len(updated)} files updated")
            if updated:
                index_files(updated)
                logger.info(f"Indexed: {len(updated)} files")
        except Exception as e:
            logger.error(f"Sync cycle error: {e}", exc_info=True)
        time.sleep(SYNC_INTERVAL)


if __name__ == "__main__":
    main()
