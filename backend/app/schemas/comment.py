from pydantic import BaseModel


class CommentIn(BaseModel):
    scenic_id: int
    content: str
    rating: float = 5
