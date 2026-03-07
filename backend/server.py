from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn

from backend.database.security import hash_password, verify_password

from jose import jwt
from datetime import timedelta, datetime
import time
import joblib
import os
import shutil

from datetime import date
from dateutil.relativedelta import relativedelta

import json

from huggingface_hub import InferenceClient
from openai import OpenAI

import numpy as np
from vosk import Model, KaldiRecognizer
import wave

import base64
from gradio_client import Client, handle_file
import ast
import ffmpeg
import subprocess

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

SECRET_KEY = "CHANGE_THIS"
ALGORITHM = "HS256"

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "ai_models", "best_intent_model.joblib")

# Load treatments for prescription generation
with open(os.path.join(BASE_DIR, "data", "treatments.json"), 'r') as file:
    treatments = json.load(file)

# Set global image variable
IMAGE = None

# Model holders
disease_client = None
pest_client = None
llm_client = None
intent_model = None
crop_data = None
tts_client = None
att_model = None

# Set global intent variables to allow for persistent intents
intent = None
pending_intent = None

# Simulation data
crop_sim_data = {}
subcounty_files = os.path.join(BASE_DIR, "data", "subcounties.json")

with open(subcounty_files, 'r') as file:
    subcounty_data = json.load(file)

subcounties = subcounty_data["subcounties"]
subcounty_lats = subcounty_data["latitudes"]
subcounty_lons = subcounty_data["longitudes"]

# Database setup
uri = os.environ.get("DATABASE_URI")
client = MongoClient(uri, server_api=ServerApi('1'))
db = client.farmersbot
users_collection = db.users

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
    files: UploadFile

class UserAudio(BaseModel):
   audio: str

class UserAudioImage(BaseModel):
   text: str

class UserUpdate(BaseModel):
    current_username: str
    new_username: Optional[str] = None
    new_password: Optional[str] = None
    input_type: Optional[str] = None
    subcounty: Optional[str] = None

@app.post("/signup")
def signup(data: UserSignup):
    global crop_sim_data

    try:
        existing = users_collection.find_one({"username": data.username})
        if existing:
            raise HTTPException(400, "Username already exists")
    
        user_doc = {
            "username": data.username,
            "password_hash": hash_password(data.password),
            "input_type": data.input_type,
            "subcounty": data.subcounty
        }
    
        users_collection.insert_one(user_doc)
    
        crop_sim_data['location'] = data.subcounty
        crop_sim_data['latitude'] = subcounty_lats[subcounties.index(crop_sim_data['location'])]
        crop_sim_data['longitude'] = subcounty_lats[subcounties.index(crop_sim_data['location'])]
        
        return {"status": "success", "message": "User registered successfully"}
    except Exception as e:
        raise HTTPException(500, f"Signup failed: {str(e)}")

@app.post("/login")
def login(data: UserLogin):
    global crop_sim_data

    try:        
        user = users_collection.find_one({"username": data.username})
        
        if not user or not verify_password(data.password, user["password_hash"]):
            raise HTTPException(401, "Invalid credentials")
    
        if user['subcounty'] not in subcounties:
            raise HTTPException(status_code=400, detail="Invalid stored subcounty")
        
        crop_sim_data['location'] = user['subcounty']
        crop_sim_data['latitude'] = subcounty_lats[subcounties.index(crop_sim_data['location'])]
        crop_sim_data['longitude'] = subcounty_lons[subcounties.index(crop_sim_data['location'])]
    
        token = jwt.encode(
            {
                "sub": user['username'],
                "exp": datetime.utcnow() + timedelta(days=7)
            },
            SECRET_KEY,
            algorithm=ALGORITHM
        )
    
        return {"access_token": token, "input_type": user['input_type'], "subcounty": user['subcounty']}
    except Exception as e:
        raise HTTPException(500, f"Login failed: {str(e)}")

@app.post("/message")
def handle_message(data: UserMessage):
    try:
        reply = handle_intent(data.message.lower())
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/image")
def handle_image(imageFile: UploadFile = File(...),):
    global IMAGE
    global intent
    
    try:
        # Create uploads folder if it doesn't exist
        os.makedirs('uploads', exist_ok=True)
        
        IMAGE = os.path.join('uploads', imageFile.filename)
        
        # Save the file using shutil (FastAPI doesn't have .save())
        with open(IMAGE, "wb") as buffer:
            shutil.copyfileobj(imageFile.file, buffer)

        intent = 'crop_growth_analysis'
        reply = handle_intent('')
            
        return {"message": "Success", "reply": reply}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/image_audio")
def handle_image_audio(imageFile: UploadFile = File(...),):
    global IMAGE
    global intent
    
    try:
        load_audio_models()
        os.makedirs('uploads', exist_ok=True)
        
        IMAGE = os.path.join('uploads', imageFile.filename)
        
        # Save the file using shutil (FastAPI doesn't have .save())
        with open(IMAGE, "wb") as buffer:
            shutil.copyfileobj(imageFile.file, buffer)

        intent = 'crop_growth_analysis'
        reply = handle_intent('')

        base64_string = tts_client.predict(
            text=reply,
            voice="af_heart",
            api_name="/generate_speech_as_bytes"
        )

        return {"reply": reply, "audio": f"{base64_string}"}

    except Exception as e:
        raise HTTPException(500, f"{str(e)}")

@app.post("/audio")
def handle_audio(audio_file: UploadFile = File(...)):
    if not audio_file.filename.endswith(('.3gp', '.wav', '.mp3')):
        raise HTTPException(status_code=400, detail="Unsupported audio format")

    try:
        load_audio_models()
    except Exception as e:
        raise HTTPException(500, f"Error loading audio models: {str(e)}")
    
    try:
        os.makedirs('uploads', exist_ok=True)
        temp_input_path = os.path.join('uploads', audio_file.filename)
        wav_path = os.path.join('uploads', f"conv_{int(time.time())}.wav")
        # generated_audio_path = os.path.join("uploads", f"tts_{int(time.time())}.wav")
        
        with open(temp_input_path, "wb+") as file_object:
            shutil.copyfileobj(audio_file.file, file_object)

         # Convert to WAV
        # os.system(f"ffmpeg -i {temp_input_path} {wav_path}")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", temp_input_path,
                "-ar", "16000",      # sample rate
                "-ac", "1",          # mono
                "-f", "wav",
                wav_path
            ],
            check=True
        )

        # Convert audio to text
        with wave.open(wav_path, "rb") as audio:
            rec = KaldiRecognizer(att_model, 16000)
            all_frames = audio.readframes(audio.getnframes())
            rec.AcceptWaveform(all_frames)
            result_text = json.loads(rec.FinalResult())["text"]

        reply = handle_intent(result_text)

        base64_string = tts_client.predict(
            text=reply,
            voice="af_heart",
            api_name="/generate_speech_as_bytes"
        )

        return {"reply": reply, "audio": f"{base64_string}"}

    except Exception as e:
        raise HTTPException(500, f"{str(e)}")
    finally:
        audio_file.file.close()
        for path in [temp_input_path, wav_path]:
            if os.path.exists(path):
                os.remove(path)

@app.get("/audio/{filename}")
def get_audio(filename: str, background_tasks: BackgroundTasks):
    audio_path = os.path.join(BASE_DIR, "data", filename)
    print("Audio path server: ", audio_path)

    if not os.path.isfile(audio_path):
        raise HTTPException(404, "Audio file not found")
    
    background_tasks.add_task(os.remove, audio_path)
    return FileResponse(audio_path, media_type="audio/wav", filename=filename)

@app.post("/update_profile")
def update_profile(data: UserUpdate):
    user = users_collection.find_one({"username": data.current_username})
    if not user:
        raise HTTPException(404, "User not found")

    if data.new_username and data.new_username != data.current_username:
        existing = users_collection.find_one({"username": data.username})
        if existing:
            raise HTTPException(400, "Username already exists")
        user['username'] = data.new_username

    if data.new_password:
        if len(data.new_password) > 256:
            raise HTTPException(400, "Password too long")
        user['password_hash'] = hash_password(data.new_password)

    if data.input_type:
        if data.input_type not in ["audio", "text"]:
            raise HTTPException(400, "Invalid input_type")
        user['input_type'] = data.input_type

    if data.subcounty:
        if data.subcounty not in subcounties:
            raise HTTPException(400, "Invalid subcounty")
        user['subcounty'] = data.subcounty

    users_collection.update_one(
        {"username": data.current_username},
        {"$set": {
            "username": data.new_username or data.current_username,
            "password_hash": hash_password(data.new_password) if data.new_password else user["password_hash"],
            "input_type": data.input_type or user["input_type"],
            "subcounty": data.subcounty or user["subcounty"]
        }}
    )

    return {
        "username": user['username'],
        "input_type": user['input_type'],
        "subcounty": user['subcounty']
    }

# Lazy loading of models to speed up start-up
def load_analysis_models():
    global pest_client
    global disease_client
    
    if not pest_client:
        try:
            pest_client = Client("Muthoni254/pest-detector")
        except Exception as e:
            raise HTTPException(500, f"Error loading pest model: {str(e)}")
    if not disease_client:
        try:
            disease_client = InferenceClient(
                provider="hf-inference",
                api_key=os.environ["HF_TOKEN"],
            )
        except Exception as e:
            raise HTTPException(500, f"Error loading disease model: {str(e)}")

def load_intent_models():
    global llm_client
    global intent_model
    
    if not llm_client:
        try:
            llm_client = OpenAI(
                base_url="https://router.huggingface.co/v1",
                api_key=os.environ["HF_TOKEN"],
            )
        except Exception as e:
            raise HTTPException(500, f"Error loading llm model: {str(e)}")

    if not intent_model:
        try:
            intent_model = joblib.load(MODEL_PATH)
        except Exception as e:
            raise HTTPException(500, f"Error loading intent model: {str(e)}")

def load_sim_models():
    global crop_data
    
    if not crop_data:
        from pcse.base import ParameterProvider
        from pcse.models import Wofost71_PP
        from pcse.input import YAMLAgroManagementReader, YAMLCropDataProvider, NASAPowerWeatherDataProvider, WOFOST72SiteDataProvider, CABOFileReader
        
        crop_data = YAMLCropDataProvider(Wofost71_PP)

def load_audio_models():
    global tts_client
    global att_model

    if not tts_client:
        try:
            tts_client = Client("Muthoni254/kokoro-audio")
        except Exception as e:
            raise HTTPException(500, f"Error loading tts model: {str(e)}")

    if not att_model:
        try:
            att_model = Model(model_name="vosk-model-small-en-us-0.15")
        except Exception as e:
            raise HTTPException(500, f"Error loading att model: {str(e)}")



def get_simulation_data(text, crop_sim_data):
    try:
        load_sim_models() # load the simulation model and set crop
    except Exception as e:
        raise HTTPException(500, f"Error loading simulation models: {str(e)}")

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

def get_weather_data(latitude, longitude):
    import requests
    from datetime import date
    
    start_date = "20000101"  # YYYYMMDD
    end_date = date.today().strftime("%Y%m%d")
    
    # Use a valid username (not 'anonymous')
    username = "farmersbot"
    
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?request=execute"
        f"&parameters=TOA_SW_DWN,ALLSKY_SFC_SW_DWN,T2M,T2M_MIN,T2M_MAX,T2MDEW,WS2M,PRECTOTCORR"
        f"&latitude={latitude}&longitude={longitude}"
        f"&start={start_date}&end={end_date}"
        f"&community=AG&format=JSON"
        f"&user={username}"
    )
    
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"NASA POWER API failed with code {response.status_code}: {response.text}")
    data = response.json()

    weather_list = []

    daily_data = data['properties']['parameter']
    dates = daily_data['T2M'].keys()  # The keys are dates like "20000101"
    
    for d in dates:
        weather_list.append({
            'YEAR': int(d[:4]),
            'DOY': int(date(int(d[:4]), int(d[4:6]), int(d[6:])).timetuple().tm_yday),
            'T2M': daily_data['T2M'][d],
            'T2M_MIN': daily_data['T2M_MIN'][d],
            'T2M_MAX': daily_data['T2M_MAX'][d],
            'T2MDEW': daily_data['T2MDEW'][d],
            'WS2M': daily_data['WS2M'][d],
            'PRECTOTCORR': daily_data['PRECTOTCORR'][d],
            'ALLSKY_SFC_SW_DWN': daily_data['ALLSKY_SFC_SW_DWN'][d],
            'TOA_SW_DWN': daily_data['TOA_SW_DWN'][d]
        })
        
    return weather_list

def run_simulation():
    global intent
    global crop_sim_data
    global pending_intent

    from pcse.base import ParameterProvider
    from pcse.models import Wofost71_PP
    from pcse.input import YAMLAgroManagementReader, OpenMeteoWeatherDataProvider, YAMLCropDataProvider, NASAPowerWeatherDataProvider, WOFOST72SiteDataProvider, CABOFileReader

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
    try:        
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
    
        weather_provider = OpenMeteoWeatherDataProvider(crop_sim_data['latitude'], crop_sim_data['longitude'])
    
        sitedata = WOFOST72SiteDataProvider(WAV=100)
    
        params = ParameterProvider(cropdata=crop_data, soildata=soil_data, sitedata=sitedata)
    
        # run the model
        model = Wofost71_PP(params, weather_provider, agromanagement)
        model.run_till_terminate()
        summary = model.get_summary_output()[0]

        # Convert datetime to human-readable form
        def ordinal(n):
            if 11 <= n % 100 <= 13:
                return f"{n}th"
            return f"{n}{['th','st','nd','rd','th','th','th','th','th','th'][n % 10]}"

        if DOA:
            new_date = summary['DOA'] + relativedelta(years=1)
            harvest_date = f"{new_date.strftime('%B')} {ordinal(new_date.day)} {new_date.year}"
        elif DOM:
            new_date = summary['DOM'] + relativedelta(years=1)
            harvest_date = f"{new_date.strftime('%B')} {ordinal(new_date.day)} {new_date.year}"
        elif DOH:
            new_date = summary['DOH'] + relativedelta(years=1)
            harvest_date = f"{new_date.strftime('%B')} {ordinal(new_date.day)} {new_date.year}"
        elif DOV:
            new_date = summary['DOV'] + relativedelta(years=1)
            harvest_date = f"{new_date.strftime('%B')} {ordinal(new_date.day)} {new_date.year}"
        
        yeild = summary['TWSO']
    
        output = model.get_output()
        total_transpiration = sum(day['TRA'] for day in output if day['TRA'] is not None)
        total_evaporation = sum(day['CEVST'] for day in output if day['CEVST'] is not None)
    
        total_water_use = total_transpiration + total_evaporation * 100000
        
        intent = None
        pending_intent = None
        del crop_sim_data['crop_name']
        del crop_sim_data['crop_variety']
    
        return f"Your expected harvest date is {harvest_date}. With optimal conditions, you can expect a yeild of {yeild} per hectare. The total amount of water you can expect to use is {total_water_use}"

    except Exception as e:
        raise HTTPException(500, f"Error performing simulation {str(e)}")
        
def analyze_image():
    global intent
    global IMAGE

    try:
        # Load models if not yet loaded
        load_analysis_models()
        
        intent = None
        issues = []
    
        diseases = disease_client.image_classification(IMAGE, model="linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification")[0]['label']
    
        pests = pest_client.predict(
            img=handle_file(IMAGE),
            api_name="/predict_pest"
        )

        raw_list = ast.literal_eval(pests)
        pests = list(dict.fromkeys(raw_list))
        issues.extend(pests)
    except Exception as e:
        raise HTTPException(500, f"Error analyzing image: {str(e)}")

    if diseases.split(' ')[0].lower() != 'healthy':
       issues.append(diseases)

    # 1. Define the starting phrase
    base_string = "The following issues were identified in your crop: "

    # 2. Create a list of formatted strings for each key-value pair
    issue_descriptions = [f"Issue: {issue}, Treatment: {treatments[issue]}" for issue in issues]
    
    try:
        os.remove(IMAGE)
        IMAGE = None
    except Exception as e:
        print("Failed to delete image:", e)

    if len(issues) > 0:
       return base_string + ", ".join(issue_descriptions) + "."
    else:
       return "Your crops seem fine"

def handle_intent(text):
    global intent
    global crop_sim_data
    global pending_intent
    reply = "Sorry, something went wrong. Please try again." # Default reply incase something crashes
    try:
        load_intent_models() # load models needed for handle intent if not yet loaded
    except Exception as e:
        raise HTTPException(500, f"Error loading intent models in handle intent: {str(e)}")

    if not intent:
        try:
            intent = intent_model.predict([text])[0]
        except Exception as e:
            raise HTTPException(500, f"Error predicting intent: {str(e)}")

    if intent == "crop_simulation" or pending_intent == 'crop simulation': # Pending intent will only be passed here on the second call to crop simulation
        needed = get_simulation_data(text, crop_sim_data)
        
        if len(needed) > 0:
            if not pending_intent:
                reply = f"Please provide the following: {", ".join(needed)}. If you already provided a crop name, then we are sorry but it seems like we do not support that crop"
                pending_intent = "crop simulation"
                intent = None
            else:
                pending_intent = None
                intent = None
                reply = f"Please repeat that"
        else:
            try:
                reply = run_simulation()
            except Exception as e:
                raise HTTPException(500, str(e))

        return reply

    elif intent == "crop_growth_analysis" or pending_intent == 'crop_growth_analysis':
        if not IMAGE:
            if not pending_intent:
                reply = "Please provide an image"
                pending_intent = "crop_growth_analysis"
                intent = None
            else:
                pending_intent = None
                intent = None
                reply = f"Please repeat that"
        else:
            try:
               reply = analyze_image()
            except Exception as e:
                raise HTTPException(500, f"{str(e)}")

        return reply
    else:
        intent = None
        try:
            reply = llm_client.chat.completions.create(
                model="jinaai/ReaderLM-v2:featherless-ai",
                messages=[
                    {
                        "role": "user",
                        "content": text
                    }
                ],
            ).choices[0].message.content
        except Exception as e:
            raise HTTPException(500, f"Error generating llm response: {str(e)}")
    
    return reply

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
    print("Application started at port 8000")
