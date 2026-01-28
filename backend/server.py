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
import joblib
import os

from pcse.base import ParameterProvider
from pcse.models import Wofost71_PP
from pcse.input import YAMLAgroManagementReader, YAMLCropDataProvider, NASAPowerWeatherDataProvider, WOFOST72SiteDataProvider, CABOFileReader
from datetime import date
from dateutil.relativedelta import relativedelta

import json
# uvicorn backend.server:app --reload

SECRET_KEY = "CHANGE_THIS"
ALGORITHM = "HS256"

app = FastAPI()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "ai_models", "best_intent_model.joblib")

IMAGE = None

intent_model = joblib.load(MODEL_PATH)
intent = None

# Simulation data
crop_data = YAMLCropDataProvider(Wofost71_PP)
crop_sim_data = {}

subcounty_files = os.path.join(BASE_DIR, "data", "subcounties.json")

with open(subcounty_files, 'r') as file:
    subcounty_data = json.load(file)

subcounties = subcounty_data["subcounties"]
subcounty_lats = subcounty_data["latitudes"]
subcounty_lons = subcounty_data["longitudes"]


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
    subcounty: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserMessage(BaseModel):
    message: str

class UserImage(BaseModel):
    image: str

@app.post("/signup")
async def signup(data: UserSignup, db: Session = Depends(get_db)):
    global crop_sim_data

    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "Username already exists")

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        input_type=data.input_type,
        subcounty=data.subcounty
    )

    db.add(user)
    db.commit()

    crop_sim_data['location'] = data.subcounty
    crop_sim_data['latitude'] = subcounty_lats[subcounties.index(crop_sim_data['location'])]
    crop_sim_data['longitude'] = subcounty_lats[subcounties.index(crop_sim_data['location'])]

    # This logic only runs if Pydantic validation passes
    print(f"New Signup: {data.username} with preference {data.input_type}")
    
    # You can add further backend checks here (e.g., if user exists)
    return {"status": "success", "message": "User registered successfully"}

@app.post("/login")
def login(data: UserLogin, db: Session = Depends(get_db)):
    global crop_sim_data
    user = db.query(User).filter(User.username == data.username).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    
    crop_sim_data['location'] = user.subcounty
    crop_sim_data['latitude'] = subcounty_lats[subcounties.index(crop_sim_data['location'])]
    crop_sim_data['longitude'] = subcounty_lats[subcounties.index(crop_sim_data['location'])]

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
    reply = handle_intent(data.message.lower())
    return {"reply": reply}

@app.post("/image")
def handle_image(data: UserImage):
    global IMAGE
    global intent

    IMAGE = data.image
    intent = 'crop_growth_analysis'
    reply = handle_intent('')

    return {"reply": reply}

def get_simulation_data(text, crop_sim_data):
  # Get crop
  needed = []
  possible_crops = list(crop_data.get_crops_varieties().keys())

  crop_name = ""
  crop_variety = ""

  if 'crop_name' not in crop_sim_data.keys():
    for crop in possible_crops:
      if crop in text:
        crop_name = crop
        crop_variety = list(crop_data.get_crops_varieties()[crop_name])[0]
  else:
    crop_name = crop_sim_data['crop_name']
    crop_variety = crop_sim_data['crop_variety']

  if crop_name == "":
    needed.append('Crop name')
  else:
    crop_sim_data['crop_name'] = crop_name
    crop_sim_data['crop_variety'] = crop_variety

  return needed

def define_agromanagement(crop_name, crop_variety, start_date, end_date, filename):
  content = f"""Version: 1.0
AgroManagement:
- 2000-01-01:
    CropCalendar:
        crop_name: {crop_name}
        variety_name: {crop_variety}
        crop_start_date: {start_date}
        crop_start_type: emergence
        crop_end_date: {end_date}
        crop_end_type: harvest
        max_duration: 360
    TimedEvents: null
    StateEvents: null
"""

  with open(filename, "w") as f:
      f.write(content)

  return filename

def run_simulation():
    global intent
    global crop_sim_data

    planting_duration = {
        "barley": 6,
        "cassava": 13,
        "chickpea": 4,
        "cotton": 6,
        "cowpea": 4,
        "fababean": 5,
        "groundnut": 4,
        "maize": 6,
        "millet": 3,
        "mungbean": 3,
        "pigeonpea": 5,
        "potato": 4,
        "rapeseed": 3,
        "rice": 4,
        "sorghum": 7,
        "soybean": 4,
        "sugarbeet": 6,
        "sugarcane": 15,
        "sunflower": 4,
        "sweetpotato": 5,
        "tobacco": 4,
        "wheat": 5,
        "seed_onion": 4,
    }

    # Crop data
    crop_data.set_active_crop(crop_sim_data['crop_name'], crop_sim_data['crop_variety'])

    # Agromanagement data
    # Start date is assumed to be a year before the current day. End date is calculated based on typical planting season length for the particular crop
    file_path = os.path.join(BASE_DIR, "data", "agromanagement.agro")
    start_date = date.today() - relativedelta(years=1)
    agromanagement_file = define_agromanagement(crop_sim_data['crop_name'], crop_sim_data['crop_variety'], start_date, start_date + relativedelta(months=planting_duration[crop_sim_data['crop_name']]), file_path)
    agromanagement = YAMLAgroManagementReader(agromanagement_file)

    # Soil data
    soil_file = os.path.join(BASE_DIR, "data", "soil", f"{crop_sim_data['location']}.soil")
    soil_data = CABOFileReader(soil_file)

    # Weather data
    weather_data = NASAPowerWeatherDataProvider(crop_sim_data['latitude'], crop_sim_data['longitude'])

    sitedata = WOFOST72SiteDataProvider(WAV=100)

    params = ParameterProvider(cropdata=crop_data, soildata=soil_data, sitedata=sitedata)

    # run the model
    model = Wofost71_PP(params, weather_data, agromanagement)
    model.run_till_terminate()
    output = model.get_output()

    intent = None
    del crop_sim_data['crop_name']
    del crop_sim_data['crop_variety']

    # Return yeild
    yeild = output[-1]['TWSO']
    # water = output['TRA'].sum() * 10

    return f"Your expected output is {yeild} kg/ha."
    # return yeild

def analyze_image():
   global intent
   intent = None

   return "Thankyou for the image"

def handle_intent(text):
    global intent
    global crop_sim_data

    if not intent:
        intent = intent_model.predict([text])[0]

    if intent == "crop_simulation":
        needed = get_simulation_data(text, crop_sim_data)
        
        if len(needed) > 0:
            reply = f"Please provide the following: {", ".join(needed)}. If you already provided a crop name, then we are sorry but it seems like we do not support that crop"
        else:
            reply = run_simulation()

        return reply

    elif intent == "crop_growth_analysis":
        if not IMAGE:
           reply = "Please provide an image"
        else:
           reply = analyze_image()

        return reply
    else:
       intent = None
       reply = "Hello. Welcome"
    
    return reply


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

2. Perform intent handling (function receives text):
    - determines the intent
    - send text to specific model based on intent
        a. Crop simulation:
        b. Crop growth analysis

        
--------------------------------------------------
Additions
1. Allow the page to automatically scroll down once we get to the bottom
2. Improve intent handling function
3. Add water to the stuff you can simulate
'''