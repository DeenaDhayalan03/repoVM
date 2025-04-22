from fastapi import HTTPException, status
from scripts.models.jwt_model import UserSignupRequest, Token, UserLoginRequest, UserLoginResponse
from scripts.utils.jwt_utils import create_user_token
from scripts.utils.mongo_utils import MongoDBConnection
from scripts.logging.logger import logger
from passlib.context import CryptContext

mongodb = MongoDBConnection()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def signup_user_handler(user: UserSignupRequest) -> Token:
    users_collection = mongodb.get_collection("users")

    existing_user = users_collection.find_one({"username": user.username})

    if existing_user:
        logger.warning(f"Signup failed: User '{user.username}' already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    hashed_password = pwd_context.hash(user.password)

    new_user = {
        "username": user.username,
        "password": hashed_password,
        "role": user.role
    }
    users_collection.insert_one(new_user)

    logger.info(f"User '{user.username}' registered successfully")

    access_token = create_user_token(user.username, user.role)
    return Token(access_token=access_token, token_type="bearer", expires_in=3600)


def login_user_handler(user_login: UserLoginRequest) -> UserLoginResponse:
    users_collection = mongodb.get_collection("users")

    username = user_login.username
    password = user_login.password

    user_record = users_collection.find_one({"username": username})

    if not user_record:
        logger.warning(f"Login failed for user '{username}' - User not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    if not pwd_context.verify(password, user_record["password"]):
        logger.warning(f"Login failed for user '{username}' - Incorrect password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    logger.info(f"User '{username}' authenticated successfully")

    access_token = create_user_token(username, user_record["role"])
    return UserLoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=3600
    )

