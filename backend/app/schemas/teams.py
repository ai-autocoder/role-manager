from typing import List, Optional
from pydantic import BaseModel, Field


class Role(BaseModel):
    code: str
    name: str
    enabled: bool = True
    description: Optional[str] = None

class UserQualification(BaseModel):
    role_code: str
    motivation_factor: float = 1.0

class User(BaseModel):
    user_id: str
    name: str
    qualifications: List[UserQualification] = Field(default_factory=list)

class TeamCreateRequest(BaseModel):
    name: str
    roles: List[Role] = Field(default_factory=list)
    users: List[User] = Field(default_factory=list)


class TeamResponse(BaseModel):
    team_id: str
    name: str
    roles: List[Role] = Field(default_factory=list)
    users: List[User] = Field(default_factory=list)
