from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    nickname: str
    role: str
