from pydantic import BaseModel
from typing import Optional

class AIRequest(BaseModel):
    prompt: str
    model: Optional[str] = "llama3-8b-8192"

class TokenInfo(BaseModel):
    symbol: str
    name: str
    price: Optional[float]
    change_24h: Optional[float]

class JobListing(BaseModel):
    title: str
    company: str
    link: str
    source: str
