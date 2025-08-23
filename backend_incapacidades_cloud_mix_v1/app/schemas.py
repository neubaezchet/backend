from pydantic import BaseModel, Field
from typing import List, Optional

class EmployeeOut(BaseModel):
    found: bool
    name: Optional[str] = None
    company: Optional[str] = None

class SubmitResponse(BaseModel):
    id: str
    status: str
    saved_dir: str
    saved_files: List[str] = Field(default_factory=list)
    missing_documents: List[str] = Field(default_factory=list)
    excel_row_index: int
    supabase_inserted: bool = False
    supabase_uploaded_files: int = 0

class SubmissionListItem(BaseModel):
    submission_id: str
    timestamp: str
    cedula: str
    userName: str
    userCompany: str
    status: str
    saved_dir: str
