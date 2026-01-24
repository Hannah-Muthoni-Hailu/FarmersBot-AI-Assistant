from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
# uvicorn server:app --reload

app = FastAPI()

# Data validation model
class UserSignup(BaseModel):
    username: str
    password: str
    input_type: str  # Expecting "audio" or "text"

@app.post("/signup")
async def signup(user: UserSignup):
    # This logic only runs if Pydantic validation passes
    print(f"New Signup: {user.username} with preference {user.input_type}")
    
    # You can add further backend checks here (e.g., if user exists)
    return {"status": "success", "message": "User registered successfully"}

if __name__ == "__main__":
    # Run server on http://127.0.0.1:8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
