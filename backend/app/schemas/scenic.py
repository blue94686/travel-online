from pydantic import BaseModel


class ScenicOut(BaseModel):
    id: int
    name: str
    province: str
    city: str
    district: str
