from fastapi import APIRouter, UploadFile, File, Form
from typing import List, Optional
import datetime, uuid, asyncio

router = APIRouter()

@router.post('/incapacities')
async def submit_incapacity(
    cedula: str = Form(...),
    incapacity_type: str = Form(...),
    days: Optional[int] = Form(None),
    mother_working: Optional[str] = Form(None),
    ghost_vehicle: Optional[str] = Form(None),
    files: List[UploadFile] = File(...)
):
    await asyncio.sleep(0.5)
    required = []
    if incapacity_type == 'enfermedad-general':
        if days and days > 2:
            required = ['Incapacidad médica', 'Epicrisis o resumen clínico']
        else:
            required = ['Incapacidad médica']
    elif incapacity_type == 'maternidad':
        required = ['Licencia/incapacidad de maternidad','Epicrisis o resumen clínico','Cédula de la madre','Registro civil','Certificado de nacido vivo']
    elif incapacity_type == 'paternidad':
        required = ['Epicrisis o resumen clínico','Cédula del padre','Registro civil','Certificado de nacido vivo']
        if mother_working == 'si': required.insert(0,'Licencia/incapacidad de maternidad')
    elif incapacity_type == 'accidente-transito':
        required = ['Incapacidad médica','Epicrisis o resumen clínico','FURIPS']
        if ghost_vehicle == 'no': required.append('SOAT')
    else:
        required = ['Incapacidad médica']

    uploaded = [f.filename for f in files]
    present = []
    for r in required:
        # simple heuristic
        if any(k in ' '.join(uploaded).lower() for k in r.lower().split()):
            present.append(r)
    missing = [r for r in required if r not in present]
    status = 'complete' if not missing else 'incomplete'

    extracted = {
        'codigo_diagnostico': 'A00', 'diagnostico': 'Simulado', 'identificacion': cedula,
        'nombres': 'Desconocido', 'numero_incapacidad': str(uuid.uuid4())[:8],
        'numero_dias': days, 'prorroga': False,
        'fecha_inicio': datetime.date.today().isoformat(),
        'fecha_fin': (datetime.date.today() + datetime.timedelta(days=days)).isoformat() if days else None,
        'fecha_subida': datetime.datetime.utcnow().isoformat() + 'Z', 'fecha_radicacion': None
    }

    radicado = None
    if status == 'complete':
        radicado = {'radicado_id': 'RAD-' + datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S'), 'fecha_radicacion': datetime.datetime.utcnow().isoformat() + 'Z'}
        extracted['fecha_radicacion'] = radicado['fecha_radicacion']

    return {'status': status, 'missing': missing, 'extracted': extracted, 'radicado': radicado, 'uploaded_files': uploaded}
