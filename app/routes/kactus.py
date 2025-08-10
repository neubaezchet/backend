from fastapi import APIRouter
router = APIRouter()

MOCK_EMPLOYEES = {
    '1085043374': {
        'name': 'Juan Pérez', 'docType': 'CC', 'company': 'Soluciones Médicas S.A.S.', 'status': 'Activo', 'email': 'juan.perez@solucionesmedicas.com'
    }
}

@router.get('/employee/{cedula}')
async def get_employee(cedula: str):
    emp = MOCK_EMPLOYEES.get(cedula)
    if not emp:
        return {'found': False, 'message': 'Usuario no encontrado'}
    return {'found': True, 'employee': emp}
