from fastapi import APIRouter, Depends
from scripts.handlers.jwt_handler import signup_user_handler, login_user_handler
from scripts.models.jwt_model import UserSignupRequest, Token, UserLoginResponse
from scripts.constants.api_endpoints import Endpoints
from scripts.logging.logger import logger
from fastapi.security import  OAuth2PasswordRequestForm

auth_router = APIRouter()

@auth_router.post(Endpoints.AUTH_SIGNUP)
def signup_user(data: UserSignupRequest) -> Token:
    logger.info(f"User '{data.username}' is signing up with role: {data.role}")
    return signup_user_handler(data)

@auth_router.post(Endpoints.AUTH_LOGIN)
def login_user(data: OAuth2PasswordRequestForm = Depends()) -> UserLoginResponse:
    logger.info(f"User '{data.username}' is attempting to log in.")
    return login_user_handler(data)

