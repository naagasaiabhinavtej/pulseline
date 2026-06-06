import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from crud import create_patient_session, complete_patient_session
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
        




















@app.post("/api/sessions/submit")
async def submit_patient_session(
    health_id:str =Form(...),
    clinic_id:str = Form(...),
    logged_nurse_name:str = Form(...),
    chief_complaint: Optional[str] = Form(None),
    additional_vitals: Optional[str] = Form(None),
    report_file: UploadFile = File(...)
):
    try:
        _, file_extension = os.path.splitext(report_file.filename)
        if not file_extension:
            file_extension = ".jpg"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{health_id}_{timestamp}{file_extension}"
        saved_file_path = os.path.join(UPLOAD_DIR, unique_filename)

        with open(saved_file_path, "wb") as buffer:
            content = await report_file.read()
            buffer.write(content)

        result = create_patient_session(
                    health_id=health_id,
                    clinic_id=clinic_id,
                    logged_nurse_name=logged_nurse_name,
                    file_path=saved_file_path, 
                    chief_complaint=chief_complaint,
                    additional_vitals=additional_vitals
                )        
        return result
    except Exception as e:
        if 'saved_file_path' in locals() and os.path.exists(saved_file_path):
            os.remove(saved_file_path)
        raise HTTPException(status_code=500, detail="Internal Error Occurred")
    
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



