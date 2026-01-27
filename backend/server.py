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

class UserMessage(BaseModel):
    message: str

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

@app.post("/message")
def handle_message(data: UserMessage):
    reply = handle_intent(data.message)
    return {"reply": reply}

def handle_intent(text):
    pass


if __name__ == "__main__":
    # Run server on http://127.0.0.1:8000
    uvicorn.run(app, host="127.0.0.1", port=8000)

'''
text_input:
    - Intent handling:
        - If intent is crop growth simulation -> send to crop_simulation
        - If intent is crop growth analysis
            - request image
            - pass image through all the models
            - identify response
                - for each result from the models
                    - if no return "No disease/pest/nutrition deficiency identified"
                    - if anything is detected, use the database to find cure and send it in a statement like
                    "The model identified the following issues:
                        - name of pest/disease/nutrition deficiency - prescription"
        - If intent is general conversation - pass to general conversation model but ensure conversations are limited

audio_input:
    - pass to audio to text model:
    - send to intent handling process:
    - get response and send to text to audio to return to user

Tasks:
1. Create function that receives text input
    - receives input
    - send to handle_intent function

2. Perform intent handling (function receives text):

'''