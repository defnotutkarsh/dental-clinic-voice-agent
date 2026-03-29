from fastapi import FastAPI , HTTPException , Request
from datetime import datetime
from pydantic import BaseModel
from database import appointments_collection , conversations_collection
import httpx
import os
from dotenv import load_dotenv
load_dotenv()
app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins =["*"],
    allow_credentials = True,
    allow_methods =["*"],
    allow_headers =["*"],
)


@app.get("/transcripts")
async def get_transcripts():
    api_key = os.getenv("ELEVENLABS_API_KEY")
    agent_id = "agent_4801kmxbde2eenevh4wfw2k1et8v"
    
    async with httpx.AsyncClient() as client:
        # Step 1: Get list of conversations
        response = await client.get(
            f"https://api.elevenlabs.io/v1/convai/conversations?agent_id={agent_id}",
            headers={"xi-api-key": api_key}
        )
        conversations = response.json().get("conversations", [])
        
        # Step 2: Fetch each conversation's transcript
        results = []
        for conv in conversations:
            conv_id = conv.get("conversation_id")
            detail = await client.get(
                f"https://api.elevenlabs.io/v1/convai/conversations/{conv_id}",
                headers={"xi-api-key": api_key}
            )
            data = detail.json()
            transcript_parts = []
            for turn in data.get("transcript", []):
                role = turn.get("role", "unknown")
                message = turn.get("message", "")
                transcript_parts.append(f"{role}: {message}")
            
            results.append({
                "conversation_id": conv_id,
                "transcript": "\n".join(transcript_parts),
                "created_at": conv.get("start_time", "")
            })
        
        return {"transcripts": results}

clinic_info = {
    "name" : "Bright Smile Dental Clinic",
    "address" : "42 MG Road , Chennai , Tamil Nadu 600001",
    "phone": "+91-44-2345-6789",
    "opening_hours" : {
        "monday_to_friday": "9:00 AM - 6:00 PM",
        "sunday":"Closed"
    },
    "services" : [
        "General Checkup",
        "Teeth Cleaning",
        "Teeth whitening",
        "Root Canal Treatment",
        "Dental Implants",
        "Braces Consultation",
    ]
}
available_slots = [
    {"date" : "2026-03-28" , "time": "10:00 AM","available" : True},
    {"date" : "2026-03-28" , "time": "11:30 AM","available" : True},
    {"date" : "2026-03-28" , "time": "02:00 PM","available" : True},
    {"date" : "2026-03-29" , "time": "09:00 AM","available" : True},
    {"date" : "2026-03-29" , "time": "03:00 PM","available" : True},
]



class AppointmentRequest(BaseModel):
    patient_name : str
    service_type : str
    appointment_time : str

@app.post("/appointments")
async def book_appointment(request : AppointmentRequest):
    slot_found = None
    for slot in available_slots:
        slot_datetime = f"{slot['date']} {slot['time']}"
        if slot_datetime == request.appointment_time and slot["available"]:
            slot_found = slot
            break
    if not slot_found:
        raise HTTPException(status_code = 400,detail ="Slot not available") 
    slot_found["available"] = False
    appointment = {
        "patient_name" : request.patient_name,
        "service_type" : request.service_type,
        "appointment_time": request.appointment_time,
        "status":"confirmed",
        "created_at": datetime.now().isoformat()
    }
    result = await appointments_collection.insert_one(appointment)
    appointment["_id"] = str(result.inserted_id)
    return {"message" : "Appointment booked !", "appointment" : appointment}




def determine_booking_status(transcript_text):
    transcript_lower = transcript_text.lower()
    if "confirmed" in transcript_lower or "booked" in transcript_lower:
        return "success"
    elif "no available" in transcript_lower or "sorry" in transcript_lower or "cannot" in transcript_lower:
        return "failed"
    else:
        return "incomplete" 







@app.get("/clinic")
def get_clinic_info():
    return clinic_info
@app.get("/")
def home():
    return {"message": "Dental Clinic API is running"}

@app.get("/phone")
def get_phone():
    return{"phone" : clinic_info["phone"]}
@app.get("/services")
def get_services():
    return {"services" : clinic_info["services"]}
@app.get("/hours")
def get_hours():
    return {"hours" : clinic_info["opening_hours"]}

@app.get("/slots")
def get_available_slots():
    open_slots = [s for s in available_slots if s["available"]]
    return {"available_slots": open_slots}

@app.get("/appointments")
async def get_appointments():
    appointments = await appointments_collection.find().to_list(100)
    for apt in appointments :
        apt["_id"] = str(apt["_id"])
    return{"appointments":appointments}

class ConversationData(BaseModel):
    caller_id : str
    transcript : str
    booking_status : str

@app.post("/webhook/conversation")
async def store_conversation(request : Request):
    data = await request.json()
    print("RECEIVED FROM ELEVENLABS:",data)
    patient_name = data.get("patient_name","Unknown")
    service_type = data.get("service_type","General Checkup")
    appointment_time = data.get("appointment_time","")
    appointment = {
        "patient_name": patient_name,
        "service_type": service_type,
        "appointment_time": appointment_time,
        "status": "confirmed",
        "created_at": datetime.now().isoformat()
    }
    await appointments_collection.insert_one(appointment)
    conversation = {
        "caller_id": patient_name,
        "booking_status": "success",
        "created_at": datetime.now().isoformat()
    }
    await conversations_collection.insert_one(conversation)

    
    return{"status":"received","message":"appointment booked successfully"}

def extract_name_from_transcript(transcript):
    return "Demo Patient"


def extract_service_from_transcript(transcript):
    services = ["General Checkup","Teeth Cleaning","Teeth Whitening","Root Canal Treatment", "Dental Implants" , "Braces Consultation"]
    transcript_lower = transcript.lower()
    for service in services:
        if service.lower() in transcript_lower:
            return service
    return "General Checkup"

def extract_time_from_transcript(transcript):
    return "2026-03-28 10:00 AM"


@app.get("/conversations")
async def get_conversations():
    conversations = await conversations_collection.find().to_list(100)
    for conv in conversations:
        conv["_id"] = str(conv["_id"])
    return{"conversations":conversations}