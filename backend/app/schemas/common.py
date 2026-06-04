from pydantic import BaseModel


class ApiResponse(BaseModel):
    success: bool
    data: dict | list
    message: str
    timestamp: str
