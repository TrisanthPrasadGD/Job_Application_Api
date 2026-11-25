from fastapi import FastAPI, status, HTTPException, Depends
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Literal
from database import get_db
from models import Application as ApplicationTable, User as UserTable
from sqlalchemy import select
from sqlalchemy.orm import Session
from pwdlib import PasswordHash
import os
from datetime import datetime, timedelta, timezone
import jwt
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError



load_dotenv()

SECRET_KEY = os.environ["JWT_SECRET_KEY"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()
password_hash = PasswordHash.recommended()

class Application_Create(BaseModel):
    company: str
    role: str
    status: Literal['Applied','Assessment', 'Interview', 'Offered',  'Rejected']
    priority: Literal['High', 'Medium', 'Low']

class Application_Response(Application_Create):
    id: int
    model_config = ConfigDict(from_attributes = True)

class User_Create(BaseModel):
    email: str
    password: str

class User_Response(BaseModel):
    id: int
    email: str
    model_config = ConfigDict(from_attributes = True)

class Token(BaseModel):
    access_token: str
    token_type: str

class User_Create(BaseModel):
    email: EmailStr
    password: str

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials",
                        headers={"WWW-Authenticate": "Bearer"})

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM])

        user_id = int(payload.get("sub"))
    except (InvalidTokenError, TypeError, ValueError):
        raise credentials_error

    user = db.get(UserTable, user_id)

    if user is None:
        raise credentials_error

    return user

@app.get("/applications", response_model=list[Application_Response])
def get_applications(
    status: Literal["Applied", "Assessment", "Interview", "Offered", "Rejected"] | None = None,company: str | None = None,
    sort_by: Literal["Priority", "Company"] | None = None,db: Session = Depends(get_db),
    current_user: UserTable = Depends(get_current_user)):
    results = list(db.scalars(select(ApplicationTable).where(ApplicationTable.user_id == current_user.id)).all())

    if status is not None:
        results = [application for application in results if application.status.casefold() == status.casefold()]

    if company is not None:
        results = [application for application in results if company.casefold() in application.company.casefold()]

    if sort_by == "Priority":
        priority_order = {"high": 0, "medium": 1, "low": 2}
        results = sorted(results, key=lambda application: priority_order[application.priority.casefold()],)

    elif sort_by == "Company":
        results = sorted(results, key=lambda application: application.company.casefold(),)

    return results

@app.post("/applications",response_model = Application_Response,status_code = status.HTTP_201_CREATED)
def create_application(application: Application_Create, db: Session = Depends(get_db),
                       current_user: UserTable = Depends(get_current_user)):
    new_application = ApplicationTable(**application.model_dump(),user_id=current_user.id,)
    db.add(new_application)
    db.commit()
    db.refresh(new_application)
    return new_application

@app.delete("/applications/{id}")
def delete_application(id: int, db: Session = Depends(get_db)):
    application = db.scalar(select(ApplicationTable).where(ApplicationTable.id == id,
                                                           ApplicationTable.user_id == current_user.id))

    if application is None:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Application not found")

    db.delete(application)
    db.commit()
    return {"message": "Application deleted"}

@app.put("/applications/{id}")
def update_application(id: int, new_status: Literal["Applied", "Assessment", "Interview", "Offered", "Rejected"],
                       db: Session = Depends(get_db)):
    application = db.scalar(select(ApplicationTable).where(ApplicationTable.id == id,ApplicationTable.user_id == current_user.id))

    if application is None:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = "Application not found")

    application.status = new_status
    db.commit()
    return {"message": "Application updated",
            "new status": application.status
    }

@app.post("/users/register", response_model = User_Response, status_code = status.HTTP_201_CREATED)
def register_user(user: User_Create, db: Session = Depends(get_db)):
    email = user.email.strip().casefold()

    existing_user = db.scalar(select(UserTable).where(UserTable.email == email))

    if existing_user is not None:
        raise HTTPException(status_code = status.HTTP_409_CONFLICT, detail = "Email Already Registered")

    new_user = UserTable(email = email, hashed_password = password_hash.hash(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@app.post("/token", response_model = Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db) ):
    email = form_data.username.strip().casefold()

    user = db.scalar(select(UserTable).where(UserTable.email == email))

    if user is None or not password_hash.verify(form_data.password, user.hashed_password):
        raise HTTPException(status_code = status.HTTP_401_UNAUTHORIZED, detail = "Incorrect Email or Password", headers =
        {"WWW-Authenticate": "Bearer"})
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = jwt.encode({"sub": str(user.id), "exp": expires_at}, SECRET_KEY, algorithm = ALGORITHM)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User_Response)
def read_current_user(current_user: UserTable = Depends(get_current_user)):
    return current_user
