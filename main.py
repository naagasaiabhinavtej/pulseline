import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from crud import create_patient_session, trigger_emergency_escalation
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

UPLOAD_DIR = "HealthProjectfile_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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



