from typing import List, Optional, Dict, Any
import os, mimetypes
from supabase import create_client, Client

def get_client() -> Optional[Client]:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)

def upload_files(bucket: str, remote_base: str, local_paths: List[str]) -> int:
    client = get_client()
    if not client:
        return 0
    uploaded = 0
    for p in local_paths:
        name = os.path.basename(p)
        remote_path = f"{remote_base}/{name}"
        try:
            client.storage.from_(bucket).upload(remote_path, p, file_options={ "content-type": mimetypes.guess_type(p)[0] or "application/octet-stream", "upsert": True })
            uploaded += 1
        except Exception:
            # try upsert if exists
            try:
                client.storage.from_(bucket).update(remote_path, p, file_options={ "content-type": mimetypes.guess_type(p)[0] or "application/octet-stream", "upsert": True })
                uploaded += 1
            except Exception:
                pass
    return uploaded

def signed_urls(bucket: str, paths: List[str], expires_in: int = 3600) -> Dict[str, str]:
    client = get_client()
    if not client:
        return {}
    out = {}
    for path in paths:
        try:
            url = client.storage.from_(bucket).create_signed_url(path, expires_in)
            out[path] = url
        except Exception:
            pass
    return out

def insert_row(table: str, row: Dict[str, Any]) -> bool:
    client = get_client()
    if not client:
        return False
    try:
        client.table(table).insert(row).execute()
        return True
    except Exception:
        return False
