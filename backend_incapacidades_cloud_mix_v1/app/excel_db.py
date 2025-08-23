import os
import pandas as pd
from typing import Dict, Any

COLUMNS = [
    "submission_id","timestamp","cedula","userName","userCompany","incapacityType","subType",
    "daysOfIncapacity","motherWorks","email","phoneNumber","status","missingDocuments","files","saved_dir"
]

def ensure_parent(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def read_df(excel_path: str) -> pd.DataFrame:
    if os.path.exists(excel_path):
        try:
            return pd.read_excel(excel_path)
        except Exception:
            pass
    return pd.DataFrame(columns=COLUMNS)

def append_row(excel_path: str, data: Dict[str, Any]) -> int:
    ensure_parent(excel_path)
    df = read_df(excel_path)
    row = {c: data.get(c, "") for c in COLUMNS}
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_excel(excel_path, index=False)
    return len(df) - 1
