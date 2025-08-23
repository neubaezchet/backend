import os, io, zipfile
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from dotenv import load_dotenv, getenv
import pandas as pd

from .schemas import EmployeeOut, SubmitResponse, SubmissionListItem
from .requirements_logic import get_required_docs
from .excel_db import append_row, read_df
from .storage import save_files_locally, try_upload_to_onedrive
from .supabase_utils import upload_files as supa_upload_files, insert_row as supa_insert_row, get_client as supa_client

load_dotenv()

app = FastAPI(title="Backend Incapacidades — Cloud Mix", version="1.1.0")

# CORS
origins_env = getenv("CORS_ORIGINS", "*")
origins = [o.strip() for o in origins_env.split(",")] if origins_env else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_DIR = getenv("STORAGE_DIR", "./storage")
DATABASE_XLSX = os.path.join(STORAGE_DIR, "database", "incapacidades.xlsx")
EMPLOYEES_CSV = os.path.join(os.path.dirname(__file__), "employees_seed.csv")

DEV_TOKEN = getenv("DEV_TOKEN", "")

SUPABASE_BUCKET = getenv("SUPABASE_BUCKET", "incapacidades")
ARCHIVE_OLDER_THAN_DAYS = int(getenv("ARCHIVE_OLDER_THAN_DAYS", "90"))

def dev_guard(token: Optional[str]):
    if not DEV_TOKEN:
        return
    if token != DEV_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid developer token.")

def load_employees_df() -> pd.DataFrame:
    # Solo para demo: intentamos leer de hoja 'employees' del Excel si existiera
    try:
        if os.path.exists(DATABASE_XLSX):
            df_all = pd.read_excel(DATABASE_XLSX)
            if {"cedula","userName","userCompany"}.issubset(df_all.columns):
                # construir un df 'employees' simple desde envíos previos
                emp = df_all[["cedula","userName","userCompany"]].drop_duplicates().rename(columns={"userName":"name","userCompany":"company"})
                return emp
    except Exception:
        pass
    return pd.read_csv(EMPLOYEES_CSV)

def find_employee(cedula: str) -> Optional[Dict[str, str]]:
    df = load_employees_df()
    row = df.loc[df["cedula"].astype(str) == str(cedula)]
    if row.empty:
        return None
    r = row.iloc[0]
    return {"name": str(r.get("name", "")), "company": str(r.get("company", ""))}

@app.get("/api/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()}

@app.get("/api/employees/{cedula}", response_model=EmployeeOut)
def get_employee(cedula: str):
    e = find_employee(cedula)
    if e:
        return EmployeeOut(found=True, name=e["name"], company=e["company"])
    return EmployeeOut(found=False)

@app.get("/api/requirements")
def api_requirements(type: str, subType: Optional[str] = None, days: Optional[int] = None, motherWorks: Optional[str] = None):
    docs = get_required_docs(type, subType, days, motherWorks)
    return {"requiredDocs": docs}

@app.post("/api/submit", response_model=SubmitResponse)
async def submit(
    cedula: str = Form(...),
    userName: str = Form(...),
    userCompany: str = Form(...),
    incapacityType: str = Form(...),
    subType: Optional[str] = Form(None),
    daysOfIncapacity: Optional[int] = Form(None),
    motherWorks: Optional[str] = Form(None),
    email: str = Form(...),
    phoneNumber: str = Form(...),
    requiredDocs: str = Form(...),
    files: Optional[List[UploadFile]] = File(None)
):
    import json as _json
    try:
        required = _json.loads(requiredDocs)
        if not isinstance(required, list):
            raise ValueError()
    except Exception:
        raise HTTPException(status_code=400, detail="requiredDocs debe ser un array JSON válido.")

    uploads = []
    if files:
        for f in files:
            uploads.append((f.filename or "archivo", f))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Carpeta por empresa/cedula/fecha
    saved_dir_rel = os.path.join("uploads", userCompany.replace("/", "_"), str(cedula), timestamp)
    saved_local_paths = save_files_locally(STORAGE_DIR, saved_dir_rel, uploads)

    present_names = {os.path.splitext(os.path.basename(p))[0].strip().lower() for p in saved_local_paths}
    missing = [d for d in required if d.strip().lower() not in present_names]
    status = "complete" if len(missing) == 0 else "incomplete"

    submission_id = f"{cedula}-{timestamp}"
    excel_row_index = append_row(
        os.path.join(STORAGE_DIR, "database", "incapacidades.xlsx"),
        {
            "submission_id": submission_id,
            "timestamp": timestamp,
            "cedula": cedula,
            "userName": userName,
            "userCompany": userCompany,
            "incapacityType": incapacityType,
            "subType": subType or "",
            "daysOfIncapacity": daysOfIncapacity or "",
            "motherWorks": motherWorks or "",
            "email": email,
            "phoneNumber": phoneNumber,
            "status": status,
            "missingDocuments": "; ".join(missing),
            "files": "; ".join(saved_local_paths),
            "saved_dir": saved_dir_rel,
        },
    )

    # OneDrive (best-effort)
    remote_base = f"{userCompany}/{cedula}/{timestamp}"
    try_upload_to_onedrive(saved_local_paths, remote_base)

    # Supabase (opcional): insert row + subir archivos si bucket configurado
    supabase_inserted = False
    supabase_uploaded_files = 0
    if supa_client():
        supabase_inserted = supa_insert_row("incapacidades", {
            "submission_id": submission_id,
            "timestamp": timestamp,
            "cedula": cedula,
            "user_name": userName,
            "user_company": userCompany,
            "incapacity_type": incapacityType,
            "sub_type": subType or None,
            "days_of_incapacity": daysOfIncapacity,
            "mother_works": motherWorks,
            "email": email,
            "phone_number": phoneNumber,
            "status": status,
            "missing_documents": missing,
            "saved_dir": saved_dir_rel,
        })
        # Nota: por política, podrías decidir subir inmediatamente o solo archivar después.
        # Aquí no subimos de inmediato, dejamos que /api/archive/older lo haga para "soportes antiguos".

    return SubmitResponse(
        id=submission_id,
        status=status,
        saved_dir=saved_dir_rel,
        saved_files=saved_local_paths,
        missing_documents=missing,
        excel_row_index=excel_row_index,
        supabase_inserted=supabase_inserted,
        supabase_uploaded_files=supabase_uploaded_files,
    )

# --------- Dev / Descargas ---------
@app.get("/api/dev/exports/excel")
def dev_export_excel(x_dev_token: Optional[str] = Header(None)):
    dev_guard(x_dev_token)
    path = os.path.join(STORAGE_DIR, "database", "incapacidades.xlsx")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Aún no existe el Excel.")
    return FileResponse(path, filename="incapacidades.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.get("/api/dev/list", response_model=List[SubmissionListItem])
def dev_list(x_dev_token: Optional[str] = Header(None)):
    dev_guard(x_dev_token)
    df = read_df(DATABASE_XLSX)
    out = []
    for _, r in df.iterrows():
        out.append(SubmissionListItem(
            submission_id=str(r.get("submission_id","")),
            timestamp=str(r.get("timestamp","")),
            cedula=str(r.get("cedula","")),
            userName=str(r.get("userName","")),
            userCompany=str(r.get("userCompany","")),
            status=str(r.get("status","")),
            saved_dir=str(r.get("saved_dir","")),
        ))
    return out

@app.get("/api/dev/download/{submission_id}")
def dev_download(submission_id: str, x_dev_token: Optional[str] = Header(None)):
    dev_guard(x_dev_token)
    df = read_df(DATABASE_XLSX)
    row = df.loc[df["submission_id"].astype(str) == submission_id]
    if row.empty:
        raise HTTPException(status_code=404, detail="submission_id no encontrado.")
    saved_dir = row.iloc[0]["saved_dir"]
    folder = os.path.join(STORAGE_DIR, saved_dir)
    if not os.path.isdir(folder):
        raise HTTPException(status_code=404, detail="Carpeta de archivos no encontrada.")
    # Crear ZIP en memoria
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(folder):
            for f in files:
                full = os.path.join(root, f)
                arc = os.path.relpath(full, folder)
                z.write(full, arcname=arc)
    mem.seek(0)
    headers = {"Content-Disposition": f"attachment; filename={submission_id}.zip"}
    return StreamingResponse(mem, headers=headers, media_type="application/zip")

# --------- Archivar a Supabase (soportes antiguos) ---------
@app.post("/api/archive/older")
def archive_older(days: Optional[int] = None, x_dev_token: Optional[str] = Header(None)):
    dev_guard(x_dev_token)
    if not supa_client():
        raise HTTPException(status_code=400, detail="Supabase no está configurado.")
    max_age = days or ARCHIVE_OLDER_THAN_DAYS
    df = read_df(DATABASE_XLSX)
    if df.empty:
        return {"moved": 0, "message": "No hay envíos registrados."}

    moved = 0
    for _, r in df.iterrows():
        ts = str(r.get("timestamp",""))
        try:
            dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
        except Exception:
            continue
        if datetime.now() - dt < timedelta(days=max_age):
            continue
        saved_dir = str(r.get("saved_dir",""))
        folder = os.path.join(STORAGE_DIR, saved_dir)
        if not os.path.isdir(folder):
            continue

        # subir a supabase storage
        local_files = []
        for root, _, files in os.walk(folder):
            for f in files:
                local_files.append(os.path.join(root, f))
        remote_base = saved_dir.replace("\\","/")
        count = supa_upload_files(SUPABASE_BUCKET, remote_base, local_files)
        if count > 0:
            moved += count
            # Opcional: podrías borrar local para liberar espacio
            # import shutil; shutil.rmtree(folder, ignore_errors=True)

    return {"moved": moved, "older_than_days": max_age}
