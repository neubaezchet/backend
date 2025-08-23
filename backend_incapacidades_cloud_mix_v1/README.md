# Backend Incapacidades — OneDrive + Supabase (opcional)

Listo para subir sin vueltas. Guarda envíos en Excel y archivos en disco (apunta `STORAGE_DIR` a una carpeta de OneDrive para sincronización).  
Opcional: inserta fila en **Supabase Postgres** y sube archivos a **Supabase Storage** (ideal para soportes antiguos).

## Rápido arranque local
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```
Swagger: http://127.0.0.1:8000/docs

## Endpoints clave
- `GET /api/employees/{cedula}` → busca en semilla/local Excel
- `GET /api/requirements` → devuelve lista de documentos según reglas
- `POST /api/submit` → recibe formulario + archivos
- `POST /api/archive/older` → mueve archivos antiguos a Supabase Storage (si está configurado)
- `GET /api/dev/exports/excel` → descarga el Excel (requiere `X-Dev-Token`)
- `GET /api/dev/download/{submission_id}` → ZIP de los archivos del envío (requiere `X-Dev-Token`)
- `GET /api/dev/list` → lista envíos y rutas (requiere `X-Dev-Token`)

## Deploy (Render)
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Define variables de entorno del `.env.example`
- Agrega tu dominio de Vercel a `CORS_ORIGINS`

## Supabase
- Crea bucket `incapacidades` (o cambia `SUPABASE_BUCKET`).
- Crea tabla `incapacidades` con columnas amigables (o el cliente la crea via REST si existe política Public). El código inserta un JSON básico; puedes ajustar esquema luego.
