from pydantic import BaseModel

class Analysis(BaseModel):
    id: int
    filename: str
    status: str
    result: str
    error: str