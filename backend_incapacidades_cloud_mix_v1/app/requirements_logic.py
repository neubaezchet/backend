from typing import List, Optional

def get_required_docs(incapacity_type: str, sub_type: Optional[str], days: Optional[int], mother_works: Optional[str]) -> List[str]:
    if incapacity_type == 'maternity':
        return ['Licencia o incapacidad de maternidad', 'Epicrisis o resumen clínico', 'Cédula de la madre', 'Registro civil', 'Certificado de nacido vivo']
    if incapacity_type == 'paternity':
        docs = ['Epicrisis o resumen clínico', 'Cédula del padre', 'Registro civil', 'Certificado de nacido vivo']
        if (mother_works or '').strip() == 'Sí':
            docs.insert(0, 'Licencia o incapacidad de maternidad')
        return docs
    if incapacity_type == 'other':
        if not sub_type:
            return []
        if sub_type in ('general', 'labor'):
            d = days or 0
            return ['Incapacidad médica'] if d <= 2 else ['Incapacidad médica', 'Epicrisis o resumen clínico']
        if sub_type == 'traffic':
            return ['Incapacidad médica', 'Epicrisis o resumen clínico', 'FURIPS', 'SOAT (si aplica)']
    return []
