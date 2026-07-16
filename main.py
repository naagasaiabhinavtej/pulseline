import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Query, WebSocket, Response, Depends, RequestValidationError, WebSocketDisconnect
from crud import create_patient_session, complete_patient_session, emergency_connect_hospitals, make_available_doctor, patientLogin,doctorLogin, checkPatientId, checkDoctorId, checkDoctorClinicId
from datetime import datetime
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from auth import createAccessToken, createRefreshToken, decodeToken, hash_password, validate_password, getCurrentUser
from schema import patientRegister, doctorRegister, LoginRequest, MakeSessionRequest, NewMessage
from utils import makeAvatarIdP
from fastapi.responses import JSONResponse
from uuid import uuid4
from pathlib import Path
import shutil
UPLOAD_DIR = Path("uploads/chat")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


app = FastAPI(title="Rural Clinic Telemedicine Platform")

app.add_middleware(
    CORSMiddleware, 
    allow_origins = ["*"],
    allow_credentials = True,
    allow_headers = ["*"],
    allow_methods = ["*"],
)

class ConnectionManager:
    def __init__(self):
        self.activeConnections = {}
    async def connect(self, userId:int,websocket:WebSocket, role:str):
        self.activeConnections[userId] = {
            "websocket": websocket,
            "role": role
        }
    def disconnect(self, userId:int):
        self.activeConnections.pop(userId, None)       #do nothing if not exists
    def get(self,userId: int):
        return self.activeConnections.get(userId)
    async def message(self, userId:int, message:dict):
        websocket = self.activeConnections.get(userId)
        if websocket:
            await websocket.send_json(message)

socket = ConnectionManager()

@app.websocket("/ws")
async def websocketEndpoint(websocket:WebSocket):
    await websocket.accept()
    userId = None
    try:
        data = await websocket.receive_json()
        if data.get("type") != "authenticate":
            await websocket.close()
            return
        accessToken = data["accessToken"]
        payload = decodeToken(accessToken)
        userId = payload["userId"]
        role = payload["role"]
        await socket.connect(userId, websocket)
        while True:
            message = await websocket.receive_json()
            if message["type"] == "new_message":
                data = NewMessage(**message)         #gives the message in object form now
                try:

                # -------------------------
                    # Validate incoming data
                    # -------------------------
                    data = NewMessage.model_validate(message)

                    uploaded_files = []

                    # -------------------------
                    # Save uploaded files
                    # -------------------------
                    for file in data.files:

                        extension = Path(file.file_name).suffix

                        stored_name = f"{uuid4().hex}{extension}"

                        file_path = UPLOAD_DIR / stored_name

                        with open(file_path, "wb") as f:
                            f.write(base64.b64decode(file.file_data))

                        uploaded_files.append({
                            "file_name": file.file_name,
                            "file_path": str(file_path)
                        })

                    # -------------------------
                    # Insert into database
                    # -------------------------
                    result = create_session_message(
                        session_id=data.sessionId,
                        sender_id=userId,
                        text=data.text,
                        files=uploaded_files,
                        timestamp=data.timestamp
                    )

                    # -------------------------
                    # Success response
                    # -------------------------
                    await websocket.send_json({
                        "type": "delivered",
                        "tempId": data.tempId,
                        "messageId": result["messageId"]
                    })

                except Exception as e:

                    # remove already uploaded files
                    for file in uploaded_files:

                        try:
                            Path(file["file_path"]).unlink(missing_ok=True)
                        except Exception:
                            pass

                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                            

                except WebSocketDisconnect:
                    if userId is not None:
                        socket.disconnect(userId)
                except Exception:
                    if userId is not None:
                        socket.disconnect(userId)
                    await websocket.close(code=1008)
                    return

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):

    error = exc.errors()[0]

    return JSONResponse(
        status_code=422,
        content={
            "type": "ValidationError",
            "field": error["loc"][-1],               #tuple
            "message": error["msg"]
        }
    )

@app.get("/refresh")
def refresh_token(request:Request):  #request is the entire piece of data or what you send to backend no need ot send the cookie if sent in htppsonlycookie
    refreshToken = request.cookies.get(
        "refreshToken"
    )
    if not refreshToken:
        raise HTTPException(
            status_code=401,
            detail="Refresh Token Missing"
        )
    payload = decodeToken(refreshToken)
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
    try:
        patientDict = patientData.model_dump()
        patientDict.update({"avatarId":makeAvatarIdP(patientData.age, patientData.gender)})
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
            key="refreshToken",
            value=refreshToken,
            httponly=True,
            secure=False,      # True in production with HTTPS
            samesite="lax",
            max_age=60 * 60 * 24 * 30
        )
        return {"message":"User Registered"}
    except:
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while registering user"
        )


@app.post("/register/doctor")
def doctorDatabaseLogin(doctorData:doctorRegister, response:Response):
    try:
        doctorDict = doctorData.model_dump()           #to make an object to dictonary use model_dump()
        hashedPassword = hash_password(doctorData.password)
        doctorDict["password"] = hashedPassword
        doctorDict.update({"avatarId":"first"})
        result = doctorLogin(doctorDict)
        userId = result[userId]
        accessToken = createAccessToken({"userId":userId,
                                         "role":"doctor"})
        refreshToken = createRefreshToken({"userId":userId,
                                         "role":"doctor"})
        response.set_cookie(
            key="refreshToken",
            value=refreshToken,
            httponly=True,
            secure=False,      # True in production with HTTPS
            samesite="lax",
            max_age=60 * 60 * 24 * 30
        )
        return {"message":"User Registered"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while registering user"
        )

@app.post("/login")
def user_database_login(user:LoginRequest, response:Response):
    if user.person == "doctor":
        result = checkDoctorId(user.id)
    elif user.person == "patient":
        result = checkPatientId(user.id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    userId, passwordHash = result

    if not validate_password(user.password, passwordHash):
        raise HTTPException(
            status_code=401,
            detail="Incorrect password"
        )

    accessToken = createAccessToken(
        {
            "userId": userId,
            "role": user.person
        }
    )
    refreshToken = createRefreshToken(
        {
            "userId": userId,
            "role": user.person
        }
    )
    response.set_cookie(
        key="refreshToken",
        value=refreshToken,
        httponly=True,
        secure=False,      # True in production
        samesite="lax",
        max_age=60 * 60 * 24 * 30
    )
    return {
        "message":"user logged in successfully"
    }



@app.get("/loading")
def loading(request: Request):

    refreshToken = request.cookies.get("refreshToken")

    if refreshToken is None:
        raise HTTPException(
            status_code=401,
            detail="Not logged in"
        )

    payload = decodeToken(refreshToken)

    return {
        "userId": payload["userId"],
        "type": payload["type"]
    }

@app.post("/makeSession")
def createSession(data:MakeSessionRequest, currentUser=Depends(getCurrentUser)):
    doctorId = currentUser["userId"]

    if doctorId != data.doctorId:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized"
        )
    
    result1 = checkPatientId(data.healthId)
    result2 = checkDoctorId(doctorId)
    result3 = checkDoctorClinicId(doctorId, data.clinicId)
    if not result1:
        return {"type":"errorInDetails",
                "errorPlace":"healthId"}
    if not result2:
        return {"type":"errorInDetails",
                "errorPlace":"doctorId"}
    if not result3:
        return {"type":"errorInDetails",
                "errorPlace":"clinicId"}
    if result1 and result2 and result3:
        return {"type":"validDetails"}

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



