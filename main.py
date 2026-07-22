import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Query, WebSocket, Response, Depends, RequestValidationError, WebSocketDisconnect
from crud import create_patient_session, complete_patient_session, emergency_connect_hospitals, make_available_doctor, patientLogin,doctorLogin, checkPatientId, checkDoctorId, checkDoctorClinicId, createSessionMessage
from datetime import datetime, timedelta
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from auth import createAccessToken, createRefreshToken, decodeToken, hash_password, validate_password, getCurrentUser
from schema import patientRegister, doctorRegister, LoginRequest, MakeSessionRequest, NewMessage, Notes, AcceptEmergency
from utils import makeAvatarIdP
from fastapi.responses import JSONResponse, FileResponse
from uuid import uuid4
from pathlib import Path
import shutil
import base64
from enum import Enum
import asyncio

UPLOAD_DIR = Path("uploads/chat")
os.makedirs(UPLOAD_DIR, exist_ok = True)
#dont give the same names of websocket to all the users

app = FastAPI(title="Rural Clinic Telemedicine Platform")

app.add_middleware(
    CORSMiddleware, 
    allow_origins = ["*"],
    allow_credentials = True,
    allow_headers = ["*"],
    allow_methods = ["*"],
)

class ConnectionType(Enum):
    ACTIVE = "active"
    SESSION = "session"
    CALL = "call"


class ConnectionManager:
    def __init__(self):
        self.activeConnections = {}
        self.SessionConnections = {}
        self.CallConnections = {}
    async def connect(self, userId:int,websocket:WebSocket, role:str, connectionType:ConnectionType,sessionId:int|None=None):
        
        if connectionType == ConnectionType.ACTIVE:
            self.activeConnections[userId] = {
                "websocket": websocket,
                "role": role
            }
        elif connectionType == ConnectionType.SESSION:
            if sessionId not in self.SessionConnections:
                self.SessionConnections[sessionId] = {}
            self.SessionConnections[sessionId][userId] = {
                "websocket": websocket,
                "role": role
            }
        elif connectionType == ConnectionType.CALL:
            if sessionId not in self.CallConnections:
                self.CallConnections[sessionId] = {}
            self.CallConnections[sessionId][userId] = {
                "websocket": websocket,
                "role": role
            }
    def disconnect(self, userId:int):
        self.activeConnections.pop(userId, None)       #do nothing if not exists
    def get(self, connectionType:ConnectionType, userId: int|None=None, sessionId:int|None=None):  #make sure the compulsary ones comes first
        if connectionType == ConnectionType.ACTIVE:
            return self.activeConnections.get(userId)
        elif connectionType == ConnectionType.SESSION:
            return self.SessionConnections.get(sessionId, {})
        elif connectionType == ConnectionType.CALL:
            return self.CallConnections.get(sessionId)
    async def message(self, userId:int, message:dict):
        connection = self.activeConnections.get(userId)
        if connection:
            await connection.send_json(message)

socket = ConnectionManager()
pendingConnections = {
    "active": {},
    "session": {},
    "chat": {}
}
activeEmergencies = {}
pendingRequests = {}
@app.websocket("/ws")
async def websocketEndpoint(websocket:WebSocket):
    await websocket.accept()
    userId = None
    try:
        data = await websocket.receive_json()
        if data.get("type") != "connect":
            await websocket.close()
            return
        accessToken = data["accessToken"]
        payload = decodeToken(accessToken)
        userId = payload["userId"]
        role = payload["role"]
        sessionId = data.get("sessionId")
        if sessionId:
            result = checkDoctorClinicId(sessionId, doctorId)
            if result is None:
                raise HTTPException(
                    status_code=403,
                    detail="Unothorised user or session"
                )

        if data["page"] == "session" or data["page"] == "call":
            result = getRole(sessionId, userId)
            if result is None:
                if result is None:
                    await websocket.close(code=1008)
                    return
            await socket.connect(userId=userId, websocket=websocket, role=result["role"], connectionType=ConnectionType(data["page"]), sessionId=data.get("sessionId"))
        else:
            await socket.connect(userId=userId, websocket=websocket, role=role, connectionType=ConnectionType(data["page"]), sessionId=data.get("sessionId"))
        curr = datetime.now()
        pendingConnections[data["page"]][userId] = [notification for notification in pendingConnections[data["page"]].get(userId, []) if notification.get("expireAt", datetime.max)>curr]
        notifications = pendingConnections[data["page"]].get(userId, [])
        while notifications:           #because if user disconnects in middle then we will have the still the others
            pending = notifications[0]
            data = notifications[0].copy()
            data.pop("expireAt", None)
            await websocket.send_json(data)
            notifications.pop(0)
        pendingConnections[data["page"]].pop(userId, None)

        while True:
            message = await websocket.receive_json()
            if message["type"] == "new_message":
                data = NewMessage(**message)         #gives the message in object form now
                uploadedFile = None
                try:
                    data = NewMessage.model_validate(message)
                    uploadedFile = data.files
                    if uploadedFile is not None:
                        extension = Path(uploadedFile.name).suffix
                        stored_name = f"{uuid4().hex}{extension}"
                        filePath = UPLOAD_DIR / stored_name             #creates a new path 
                        with open(filePath, "wb") as f:
                            f.write(base64.b64decode(uploadedFile.data))            #we are using base64 because when frontend sends via websocket json cant stringify the bytes so hence the base64 format
                        uploadedFile = {
                            "fileName": uploadedFile.name,
                            "filePath": str(filePath)
                        }
                    
                    result = createSessionMessage(
                        sessionId=data.sessionId,
                        senderId=userId,
                        text=data.text,
                        files=uploadedFile,
                    )

                    await websocket.send_json({
                        "type": "delivered",
                        "tempId": data.tempId,
                        "messageId": result["messageId"],
                        "attachmentId":result["attachmentId"],
                        "timestamp":result["timestamp"]
                    })
                    participants = socket.get(connectionType=ConnectionType.SESSION, sessionId=data.sessionId)
                    for uid, info in participants.items():
                        if uid == userId:
                            continue

                        await info["websocket"].send_json(
                            {
                                "type": "sent",

                                "messageId": result["messageId"],

                                "sender_id": result["senderId"],
                                "senderName": result["senderName"],
                                "avatarId": result["avatarId"],

                                "chattext": result["text"],

                                "files": [{
                                    "attachmentId": result["attachmentId"],
                                    "file_name": result["fileName"]
                                }] if result.get("attachmentId") else [],

                                "timestamp": result["timestamp"],
                                "date": result["date"]
                            }
                        )


# {
#createSession should send this
#     "messageId": messageId,
#     "attachmentId": attachmentId,      # None if no file
#     "fileName": fileName,              # None if no file

#     "senderId": senderId,
#     "senderName": senderName,
#     "avatarId": avatarId,

#     "text": text,

#     "timestamp": timestamp,            # e.g. "10:31 AM"
#     "date": date,                      # e.g. "24 May 2025"

#     "sessionId": sessionId
# }
                except Exception as e:

                    # remove already uploaded files
                    if uploadedFile:

                        try:
                            Path(uploadedFile["filePath"]).unlink(missing_ok=True)
                        except Exception:
                            pass

                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
            elif message["type"] == "read":
                try:
                    result = markMessageRead(
                        messageId=message["messageId"],
                        userId=userId
                    )
                    if result.get("Read"):
                        participants = socket.get(
                            sessionId=sessionId,
                            connectionType=ConnectionType.SESSION
                        )
                        if participants:
                            sender = participants.get(result["senderId"])
                            if sender:
                                await sender["websocket"].send_json({
                                    "type": "read",
                                    "tempId": message["messageId"]
                                })   
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
            elif message["type"] == "reject_emergency":
                pass
            elif message["type"] == "accept_emergency":
                emergency = activeEmergencies.get(sessionId)    #{} is not none so be careful or simply if sessionId not in activeEmergencies
                if emergency is None:                                #if you dont know where to write what just have that order where what will happen first and decide
                    raise HTTPException(
                        status_code=404,
                        detail="Emergency Not Found"
                    )
                if activeEmergencies[sessionId]["assignedDoctor"] is not None:     #if 2 people clicks at a time
                    raise HTTPException(
                        status_code=409,
                        detail="Emergency already accepted"
                    )
                activeEmergencies[sessionId]["assignedDoctor"] = userId
                result = updateRefferedDoctorDetails(sessionId, userId)
                if result:
                    users = activeEmergencies[sessionId]["doctorList"]
                    for user in users:
                        #fill out here
                    activeEmergencies[sessionId]["event"].set()
                    participants = socket.get(ConnectionType.SESSION, sessionId=sessionId)
                    for user in participants:
                        await user["websocket"].send_json({
                            "type" : "doctor2Details",
                            "name": result["Doctor2name"]
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
        userId = result["userId"]
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
async def createSession(data:MakeSessionRequest, currentUser=Depends(getCurrentUser)):
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
    if data.healthId in pendingRequests:
        raise HTTPException(
            status_code=409,
            detail="Patient has been requested with other session"
        )
    pendingRequests[data.healthId] = {
        "event":asyncio.Event(),
        "doctorId":doctorId
    }
    try:
        await asyncio.wait_for( 
        pendingRequests[data.healthId]["event"].wait(),
        timeout=5*60
        )
        connection = socket.get(connectionType=ConnectionType.ACTIVE, userId=doctorId)
        if connection:
            #fill here what happens when user clicks success or when user rejects and other things


    except asyncio.TimeoutError:
        connection = socket.get(connectionType=ConnectionType.ACTIVE, userId=doctorId)
        if connection:
            await connection["websocket"].send_json({
                "type":"Expired"
            })
        else:
            pendingConnections[ConnectionType.SESSION].setdefault(doctorId, []).append(
                {
                    "type":"Expired"
                }
            )

            



    


@app.get("/session_detail/{sessionId}")
def giveDataSessionDetail(sessionId:int, currentUser=Depends(getCurrentUser)):
    result = checkSessionId(sessionId)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Session Not Found"
        )
    doctorId = currentUser["userId"]
    if doctorId not in {result.doctor1Id, result.doctor2Id}:
        raise HTTPException(
            status_code=403,
            detail="User Unauthorised"
        )
    userDetails = getDoctorDetails(doctorId)
    sessionDetails = getSessionDetails(sessionId)
    messages = getSessionMessages(sessionId)
    participantCount = 2
    if session.doctor2Id is not None:
        participantCount += 1
    for message in messages:

        readCount = getReadCount(message["messageId"])
        message["bluetick"] = (readCount == participantCount)
        
    result = {}
    result.update(userDetails)
    result.update(sessionDetails)
    result["messages"] = messages

    return result



@app.get("/download-file/{attachmentId}")
def giveFile(request:Request, attachmentId:int):
    refreshToken = request.cookies.get("refreshToken")
    if not refreshToken:
        raise(HTTPException(
            status_code=403,
            detail="Unauthorised"
        ))
    payload = decodeToken(refreshToken)
    if payload["type"] != "refresh":
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )
    userId = payload["userId"]
    result = getAttachmentDetails(userId=userId, attachmentId = attachmentId)
    if result is None:
        raise(HTTPException(
            status_code=404,
            detail="User Not Found"
        ))
    
    return FileResponse(path=result["filePath"], filename=result["fileName"])
    
@app.post("/logout")
def logout(response:Response):
    response.delete_cookie("refreshToken")       #doesnt give any erroos safely deletes even when there is no refreshToken
    return {
        "message": "Logged out successfully"
    }            #for the logout in frontend mostly it wont cause any error but if there is server issue and then if sends then in frontend it goes to login.html but later as refresh token is not deleted user is login simultaneously

@app.post("/notes/update")
def notesUpdate(data:Notes, currUser=Depends(getCurrentUser)):
    userId = currUser["userId"]
    sessionId = data.sessionId  #after pydantic you will get the object
    notes = data.notes
    result = updateNotes(sessionId=sessionId, userId=userId, notes=notes)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="User Not Found"
        )
    return {"message":"Notes Updatad Finally"}


async def emergencyWorkFlow(sessionId:int, doctorId:int, patientName:str, clinicName:str, deparment:str, timestamp:str):
    try:
        ldoctors = getLocalDoctors(doctorId, sessionId)
        for doctors in ldoctors:
            ws = socket.get(connectionType=ConnectionType.ACTIVE, userId=doctors)
            if ws:
                await ws["websocket"].send_json({
                    "type":"emergencyConnection",
                    "sessionId":sessionId,
                    "patientName":patientName,
                    "hospitalName":clinicName,
                    "problem":deparment,
                    "createdAt":timestamp
                })
            else:
                pendingConnections[ConnectionType.ACTIVE].setdefault(doctors, []).append({    #so that if key doesnt exist makes a list 
                    "type":"emergencyConnection",
                    "sessionId":sessionId,
                    "patientName":patientName,
                    "hospitalName":clinicName,
                    "problem":deparment,
                    "createdAt":timestamp,
                    "expireAt":datetime.now()+timedelta(minutes=30)
                })
        requestId = None
        connection = socket.get(connectionType=ConnectionType.SESSION, sessionId=sessionId)
        if connection:
            requestId = connection.get(doctorId)
            if requestId:
                await requestId["websocket"].send_json({
                    "type":"startedSearching"
                })
            else:
                pendingConnections[ConnectionType.SESSION].setdefault(doctorId, []).append({"type":"startedSearching"})
        try:
            await asyncio.wait_for(
                activeEmergencies[sessionId]["event"].wait(),
                timeout=30*60
            )
            # assignedDoctorId = activeEmergencies[sessionId]["assignedDoctor"]
            if requestId:
                await requestId["websocket"].send_json({
                    "type":"searchingSuccess"
                })
            else:
                pendingConnections[ConnectionType.SESSION].setdefault(doctorId, []).append({
                    "type": "searchingSuccess"
                })
            return {
                "message":"Emergency call sorted out"
            }
        except asyncio.TimeoutError:
            pass

        adoctors = getAllDoctors(doctorId, sessionId)
        for doctors in adoctors:
            ws = socket.get(connectionType=ConnectionType.ACTIVE, userId=doctors)
            if ws:
                await ws["websocket"].send_json({
                    "type":"emergencyConnection",
                    "sessionId":sessionId,
                    "patientName":patientName,
                    "hospitalName":clinicName,
                    "problem":deparment,
                    "createdAt":timestamp
                })
            else:
                pendingConnections[ConnectionType.ACTIVE].setdefault(doctors, []).append({
                    "type":"emergencyConnection",
                    "sessionId":sessionId,
                    "patientName":patientName,
                    "hospitalName":clinicName,
                    "problem":deparment,
                    "createdAt":timestamp,
                    "expireAt":datetime.now()+timedelta(minutes=30)
                })
        if requestId:
            await requestId["websocket"].send_json({
                "type":"startedExpanding"
            })
        else:
            pendingConnections[ConnectionType.SESSION].setdefault(doctorId, []).append({"type":"startedExpanding"})
        try:
            await asyncio.wait_for(
                activeEmergencies[sessionId]["event"].wait(),
                timeout=30*60
            )
            if requestId:
                await requestId["websocket"].send_json({
                    "type":"searchingSuccess"
                })
            else:
                pendingConnections[ConnectionType.SESSION].setdefault(doctorId, []).append({
                    "type": "searchingSuccess"
                })
            return {
                "message":"Emergency call sorted out"
            }
        except asyncio.TimeoutError:
            if requestId:
                await requestId["websocket"].send_json({
                    "type":"searchingFailed"
                })
            else:
                pendingConnections[ConnectionType.SESSION].setdefault(doctorId, []).append({"type":"searchingFailed"})
    finally:
        activeEmergencies.pop(sessionId, None)  #so that it will happen regardless of whtever will happen
        

@app.post("/sessions/emergency")
def makeEmergency(data:AcceptEmergency, currUser=Depends(getCurrentUser)):
    if currUser["role"] != "doctor":
        raise HTTPException(
            status_code=403,
            detail="Only doctors can start emergency"
        )
    sessionId = data.sessionId
    userId = currUser["userId"]
    result = checkDoctorClinicId(doctorId=userId, clinicId=sessionId)
    if result is None:
        raise HTTPException(
            status_code=403,
            detail="Unauthorised"
        )
    if activeEmergencies.get(sessionId):
        raise HTTPException(
            status_code=409,
            detail="Emergency already in progress"
        )
    activeEmergencies[sessionId] = {
        "event": asyncio.Event(),
        "assignedDoctor":None
    }
    res = getSessionDetailsToConnect(sessionId=sessionId)
    if res:
        asyncio.create_task(emergencyWorkFlow(sessionId=sessionId, doctorId=res["doctorId"], patientName=res["patientName"], clinicName=res["clinicName"], deparment=res["department"], timestamp=res["timestamp"]))
    return{                             #if you write { below return then it doesnt work
        "status":"started"
    }
    




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



