from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import uvicorn
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.database.models import User
from backend.database.security import hash_password

from backend.database.security import verify_password
from jose import jwt
from datetime import timedelta, datetime
# uvicorn backend.server:app --reload

SECRET_KEY = "CHANGE_THIS"
ALGORITHM = "HS256"

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Data validation model
class UserSignup(BaseModel):
    username: str
    password: str
    input_type: str  # Expecting "audio" or "text"

class UserLogin(BaseModel):
    username: str
    password: str

@app.post("/signup")
async def signup(data: UserSignup, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "Username already exists")

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        input_type=data.input_type
    )

    db.add(user)
    db.commit()

    # This logic only runs if Pydantic validation passes
    print(f"New Signup: {data.username} with preference {data.input_type}")
    
    # You can add further backend checks here (e.g., if user exists)
    return {"status": "success", "message": "User registered successfully"}

@app.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    token = jwt.encode(
        {
            "sub": user.username,
            "exp": datetime.utcnow() + timedelta(days=7)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {"access_token": token, "input_type": user.input_type}

if __name__ == "__main__":
    # Run server on http://127.0.0.1:8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
