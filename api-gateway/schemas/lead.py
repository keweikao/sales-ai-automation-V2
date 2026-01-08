"""潛客相關 Schema"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Lead(BaseModel):
    """潛客資訊"""
    id: str
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    status: str
    score: int = 0
    createdAt: datetime
    updatedAt: Optional[datetime] = None
