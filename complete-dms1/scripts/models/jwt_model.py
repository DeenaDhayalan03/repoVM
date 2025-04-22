from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str = Field(..., description="The access token issued by the server")
    token_type: str = Field(..., description="Type of the token, usually 'bearer'")
    expires_in: int = Field(..., description="Expiration time in seconds")


class TokenData(BaseModel):
    username: str = Field(..., description="The username of the authenticated user")
    role: str = Field(..., description="The role of the authenticated user")
    access_token: str


class UserSignupRequest(BaseModel):
    username: str = Field(..., description="The unique username for signup")
    password: str = Field(..., description="The password for signup")
    role: str = Field(..., description="The role of the user (Admin, Manager, Employee)")


class UserLoginRequest(BaseModel):
    username: str = Field(..., description="The username for login")
    password: str = Field(..., description="The password for login")


class UserLoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Type of the token (bearer)")
    expires_in: int = Field(..., description="Expiration time of the access token in seconds")
