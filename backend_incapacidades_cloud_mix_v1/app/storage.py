import os, shutil
from typing import List, Tuple, Optional
from starlette.datastructures import UploadFile
import requests
from dotenv import getenv

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def safe_join(*parts: str) -> str:
    p = os.path.join(*parts)
    return p.replace('..', '').replace('\\', '/')

def save_files_locally(base_dir: str, saved_dir: str, uploads: List[Tuple[str, UploadFile]]) -> List[str]:
    ensure_dir(os.path.join(base_dir, saved_dir))
    saved_paths = []
    for field_name, upload in uploads:
        filename = upload.filename or field_name
        safe_name = filename.replace('/', '_').replace('\\', '_')
        dest = os.path.join(base_dir, saved_dir, safe_name)
        with open(dest, 'wb') as f:
            shutil.copyfileobj(upload.file, f)
        saved_paths.append(dest)
    return saved_paths

# OneDrive Graph (best-effort)
def try_upload_to_onedrive(local_paths: List[str], remote_base: str) -> None:
    tenant = getenv("MS_TENANT_ID")
    client_id = getenv("MS_CLIENT_ID")
    client_secret = getenv("MS_CLIENT_SECRET")
    drive_id = getenv("MS_ONEDRIVE_DRIVE_ID", "me")
    base_path = getenv("MS_ONEDRIVE_BASE_PATH", "/IncapacidadesUploads")

    if not tenant or not client_id or not client_secret:
        return

    token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    try:
        tok = requests.post(token_url, data=data, timeout=20).json()
        access_token = tok.get("access_token")
        if not access_token:
            return
    except Exception:
        return

    headers = {"Authorization": f"Bearer {access_token}"}
    for p in local_paths:
        name = os.path.basename(p)
        remote_path = f"{base_path}/{remote_base}/{name}"
        try:
            with open(p, "rb") as fh:
                if drive_id == "me":
                    url = f"https://graph.microsoft.com/v1.0/me/drive/root:{remote_path}:/content"
                else:
                    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:{remote_path}:/content"
                requests.put(url, headers=headers, data=fh, timeout=60)
        except Exception:
            pass
