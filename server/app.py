from fastapi import FastAPI, HTTPException, Body, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from models import LogisticsAction, Observation, Reward, Info
from environment import LogisTechEnv
from tasks import LogisticsGrader, get_tasks_list
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from dotenv import load_dotenv
import jwt
import uuid
import os
from datetime import datetime, timedelta

# Load environment variables from .env
load_dotenv()

app = FastAPI(title="LogisTech-OpenEnv: Autonomous Supply Chain Environment")

# MongoDB Setup
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017").strip()
client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=2000)
db_client = client.logistech_db
users_collection = db_client.users
otps_collection = db_client.otps

@app.on_event("startup")
async def startup_event():
    try:
        # TTL Index: OTPs expire after 15 minutes (900 seconds)
        await otps_collection.create_index("createdAt", expireAfterSeconds=900)
    except Exception as e:
        print(f"Warning: Could not create TTL index: {e}")

# Security
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "LOGISTECH_SUPER_SECRET")
ALGORITHM = "HS256"

# Mount static files
root_dir = os.path.dirname(os.path.dirname(__file__))
static_dir = os.path.join(root_dir, "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/health")
async def health():
    """Health check endpoint required by OpenEnv multi-mode deployment."""
    return {"status": "ok", "env": "LogisTech-OpenEnv", "version": "1.0.0"}

@app.get("/dashboard")
async def dashboard():
    return FileResponse(os.path.join(static_dir, "dashboard.html"))

# Models for Auth
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class OtpRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    otp: str

class OtpResetRequest(BaseModel):
    email: str
    password: str
    otp: str

def generate_otp():
    import random
    return f"{random.randint(100000, 999999)}"

@app.post("/auth/register")
async def register(req: OtpRegisterRequest):
    try:
        # Verify OTP
        otp_entry = await otps_collection.find_one({"email": req.email, "otp": req.otp})
        if not otp_entry:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
        user = await users_collection.find_one({"email": req.email})
        if user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        pw_str = str(req.password)[:72]
        new_user = {
            "email": req.email,
            "full_name": req.name,
            "hashed_password": pwd_context.hash(pw_str)
        }
        await users_collection.insert_one(new_user)
        # Delete OTP after use
        await otps_collection.delete_one({"_id": otp_entry["_id"]})
        return {"message": "User created successfully"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")

@app.post("/auth/otp/generate")
async def request_otp(email: str = Body(..., embed=True)):
    otp = generate_otp()
    await otps_collection.update_one(
        {"email": email},
        {"$set": {"otp": otp, "createdAt": datetime.utcnow()}},
        upsert=True
    )
    return {"otp": otp}

@app.post("/auth/login")
async def login(req: LoginRequest):
    user = await users_collection.find_one({"email": req.email})
    if not user or not pwd_context.verify(req.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = jwt.encode({"sub": req.email, "exp": datetime.utcnow() + timedelta(days=1)}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": access_token, "full_name": user["full_name"]}

@app.post("/auth/forgot-password")
async def forgot_password(email: str = Body(...), otp: Optional[str] = Body(None), new_password: Optional[str] = Body(None)):
    user = await users_collection.find_one({"email": email})
    if not user:
         raise HTTPException(status_code=404, detail="Email not found")
    
    if otp and new_password:
        otp_entry = await otps_collection.find_one({"email": email, "otp": otp})
        if not otp_entry:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
        # Update password
        await users_collection.update_one(
            {"email": email},
            {"$set": {"hashed_password": pwd_context.hash(new_password)}}
        )
        await otps_collection.delete_one({"_id": otp_entry["_id"]})
        return {"message": "Password updated successfully"}
    
    return {"message": "OTP generated. Check your email."}

# In-memory storage for active sessions
sessions: Dict[str, Dict[str, Any]] = {}

@app.get("/config")
async def get_config():
    return {
        "EMAILJS_SERVICE_ID": os.getenv("EMAILJS_SERVICE_ID"),
        "EMAILJS_TEMPLATE_OTP": os.getenv("EMAILJS_TEMPLATE_OTP"),
        "EMAILJS_TEMPLATE_WELCOME": os.getenv("EMAILJS_TEMPLATE_WELCOME"),
        "EMAILJS_PUBLIC_KEY": os.getenv("EMAILJS_PUBLIC_KEY"),
    }

@app.get("/tasks")
async def get_tasks():
    return {
        "tasks": get_tasks_list(),
        "action_schema": LogisticsAction.schema()
    }

@app.post("/reset")
async def reset(task_id: str = "easy"):
    session_id = str(uuid.uuid4())
    env = LogisTechEnv(task_id=task_id)
    obs = env.reset()
    sessions[session_id] = {"env": env, "history": [], "task_id": task_id}
    return {"session_id": session_id, "observation": obs}

@app.post("/step")
async def step(session_id: str, action: LogisticsAction):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = sessions[session_id]
    env = session["env"]
    obs, reward, done, info = env.step(action)
    history_entry = {
        "action": action.dict(),
        "observation": obs.dict(),
        "reward": reward.dict(),
        "done": done,
        "info": info.dict(),
        "state": env.state()
    }
    session["history"].append(history_entry)
    return {"observation": obs, "reward": reward, "done": done, "info": info}

@app.get("/state")
async def get_state(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]["env"].state()

@app.post("/add-branch")
async def add_branch(session_id: str = Body(...), wh_id: str = Body(...), location: str = Body(...), capacity: int = Body(...)):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    env = sessions[session_id]["env"]
    success = env.add_warehouse(wh_id, location, capacity)
    if not success:
        raise HTTPException(status_code=400, detail="Branch already exists or ID invalid")
    return {"message": "New branch added to network", "branch": wh_id}

@app.get("/grader")
async def get_grader(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = sessions[session_id]
    score = LogisticsGrader.score(session["task_id"], session["history"])
    return {"score": score, "task_id": session["task_id"]}

@app.post("/baseline")
async def run_baseline():
    results = {}
    for task_id in ["easy", "medium", "hard"]:
        env = LogisTechEnv(task_id=task_id)
        env.reset()
        history = []
        done, steps = False, 0
        while not done and steps < 30:
            action = LogisticsAction(action_type="NOTIFY", params={"order_id": "none", "message": "all good"})
            obs, reward, done, info = env.step(action)
            history.append({"action": action.dict(), "observation": obs.dict(), "reward": reward.dict(), "done": done, "info": info.dict(), "state": env.state()})
            steps += 1
        results[task_id] = LogisticsGrader.score(task_id, history)
    return {"baseline_results": results}

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
