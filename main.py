import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Query, WebSocket, Response
from crud import create_patient_session, complete_patient_session, emergency_connect_hospitals, make_available_doctor, patientLogin
from datetime import datetime
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from auth import createAccessToken, createRefreshToken, decodeToken, hash_password, validate_password
from schema import patientRegister

app = FastAPI(title="Rural Clinic Telemedicine Platform")

app.add_middleware(
    CORSMiddleware, 
    allow_origins = ["*"],
    allow_credentials = True,
    allow_headers = ["*"],
    allow_methods = ["*"],
)

@app.get("/refresh")
def refresh_token(request:Request):  #request is the entire piece of data or what you send to backend no need ot send the cookie if sent in htppsonlycookie
    refresh_token = request.cookies.get(
        "refresh_token"
    )
    if not refresh_token:
        raise HTTPException(
            status_code=401,
            detail="Refresh Token Missing"
        )
    payload = decodeToken(refresh_token)
    if(payload.get("type")!="refresh"):                  #jwtdecode only sees the signature correct not expire only these but you need others also right like whats the purpose of this token
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )
    
    new_access_token = createAccessToken({
        "userId":payload["userId"],
        "role":payload["role"]
    })

    return {
               "access_token":new_access_token,
               "token-type":"Bearer"
            }  #standard way to use 


@app.post("/register/patient")
def patientDatabaseLogin(patientData:patientRegister, response:Response):
    patientDict = patientData.model_dump()
    hashedPassword = hash_password(patientData.password)
    patientData.password = hashedPassword
    patientDict["password"] = hashedPassword
    result = patientLogin(patientData=patientDict, hashedPassword=hashedPassword)
    userId = result["userId"]
    accessToken = createAccessToken({"userId":userId,
                                     "role":"patient"})
    refreshToken = createRefreshToken({"userId":userId,
                                     "role":"patient"})
    response.set_cookie(
        key="refresh_token",
        value=refreshToken,
        httponly=True,
        secure=False,      # True in production with HTTPS
        samesite="lax",
        max_age=60 * 60 * 24 * 30
    )
    return {"message":"User Registered"}




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
async def connect_hospitals(session_id:int = Query(..., description="The ID of the current consultation session"),
                      clinic_id: int = Query(..., description="The ID of the requesting clinic"),
                      department: str = Query(..., description="The department stream (e.g., Cardiology)")):
    try:
        results = emergency_connect_hospitals(session_id=session_id, clinic_id=clinic_id, department=department)
        
        for result in results:
            await connections[result[0]].send_text()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal sever issue: {str(e)}")
    
connections = {}
@app.websocket("/ws/doctor")
async def make_connections_doctor(websocket:WebSocket):
    doctor_id = websocket.query_params["doctor_id"]
    await websocket.accept()
    connections[doctor_id] = websocket
    result = make_available_doctor(doctor_id=doctor_id)
    return result

    






































    
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



