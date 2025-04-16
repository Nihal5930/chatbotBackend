from pydantic import BaseModel, EmailStr, Field
from typing import List
from typing import Optional, Dict
from uuid import uuid4
from datetime import datetime


class User(BaseModel):
    fullName: str
    emailID: EmailStr
    phoneNumber: str
    conversationHistory: List[str] = []
    sub: int
    picture: str



