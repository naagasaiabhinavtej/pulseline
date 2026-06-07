import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Query
from crud import create_patient_session, complete_patient_session, emergency_connect_hospitals
from datetime import datetime
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Rural Clinic Telemedicine Platform")

app.add_middleware(
    CORSMiddleware, 
    allow_origins = ["*"],
    allow_credentials = True,
    allow_headers = ["*"],
    allow_methods = ["*"],
)

@app.post("/api/sessions/start")
def make_session(health_id:str = Form(...), clinic_id:str = Form(...), department:str = Form(...), assigned_doctor_id:str = Form(...)):
    #make check when unkown patient_name comes or unknown_doc_name or clinic name comes
    return create_patient_session(health_id, clinic_id, department, assigned_doctor_id)

TO_UPLOAD_DIR = "folder"
os.makedirs(TO_UPLOAD_DIR, exist_ok = True)

@app.post("/api/sessions/{session_id}/submit")
async def complete_session(request:Request,chief_complaint:str = Form(...), additional_vitals:str = Form(...), uploaded_filepath:UploadFile = File(...),
                            blood_pressure: Optional[str] = Form(None), blood_sugar: Optional[float] = Form(None), temperature:Optional[float] = Form(None), 
                            heart_rate: Optional[int] = Form(None)):
    file_path = None
    try:
        _, file_ext = os.path.splitext(uploaded_filepath.filename)
        if not file_ext:
            file_ext = '.jpg'
        session_id = request.path_params.get("session_id")
        resolved_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_total_name = f"{str(session_id)}_{resolved_time}{file_ext}"
        file_path = os.path.join(TO_UPLOAD_DIR, file_total_name)
        with open(file_path, "wb") as f:
            content = await uploaded_filepath.read()
            f.write(content)
        result = complete_patient_session(session_id=int(session_id), chief_complaint=chief_complaint, additional_vitals=additional_vitals,uploaded_filepath=file_path,resolved_time=resolved_time, blood_pressure=blood_pressure, blood_sugar=blood_sugar,temperature=temperature, heart_rate=heart_rate )
        return result
    except Exception as e:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Internal server problem : {str(e)}")
        

@app.get("/api/sessions/emergency")
def connect_hospitals(session_id:int = Query(..., description="The ID of the current consultation session"),
                      clinic_id: int = Query(..., description="The ID of the requesting clinic"),
                      department: str = Query(..., description="The department stream (e.g., Cardiology)")):
    try:
        result = emergency_connect_hospitals(session_id=session_id, clinic_id=clinic_id, department=department)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal sever issue: {str(e)}")
    






































    
@app.post("/api/sessions/{session_id}/escalate")
async def escalate_session(session_id: int):
    try:
        emergency_data = trigger_emergency_escalation(session_id)

        if not emergency_data:
            raise HTTPException(
                status_code=404, 
                detail=f"Session with ID {session_id} not found."
            )
            
        return{
            "status": "success",
            "message": "Session escalated to emergency successfully.",
            "data": emergency_data
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error during escalation: {str(e)}"
        )



