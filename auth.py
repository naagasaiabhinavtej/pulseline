from datatime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastApi import FastAPI, HTTPException, Response, Request, Depends
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

app = FastAPI()

SECRET_KEY = "DARE_TO_DECODE_THIS"
ALGORITHM = "HS256"  #commonly used for secret keys 

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30

def createAccessToken(data:dict):
    payload = data.copy()     #makes a shallow copy of data i mean the different object 
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload.update({"exp":expire,
                    "type":"access"})
    return jwt.encode(payload, SECRET_KEY,algorithm=ALGORITHM)

def createRefreshToken(data:dict):
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload.update({"exp":expire,
                    "type":"refresh"})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decodeToken(token:str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=401
            detail:"Invalid Token"
        )
#for functions use _ in naming and in 
def hash_password(password:str):
    return pwd_context.hash(password)

def validate_password(password:str, hashed_password:str):
    return pwd_context.verify(password, hashed_password)