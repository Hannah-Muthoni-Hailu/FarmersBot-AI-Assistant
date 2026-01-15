'''
1. Recieve input from frontend
2. If audio, pass to audio to text model and return text
3. Send audio to intent identification function
    - Determine intent (general conversation, crop simulation, nutrient/pest/disease identification)
    - Send data to relevant model
    - Obtain response
    - If user is text-based, send response to frontent
    - If user is audio-based:
        - Send response to text-to-audio model then send response to frontend
4. Model functions:
    - Crop simulator
    - Nutrient/pest/disease identification
        - Obtains image
'''

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat/input")
async def chat_input(req):
    user_input = req.input
    input_type = req.type

    if type == 'text':
        return {"reply": "Text input in use."}
    else:
        return {"reply": "Audio input in use."}
