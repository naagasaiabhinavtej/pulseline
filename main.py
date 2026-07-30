import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request, Query, WebSocket, Response, Depends, RequestValidationError, WebSocketDisconnect
from crud import create_patient_session, complete_patient_session, emergency_connect_hospitals, make_available_doctor, patientLogin,doctorLogin, checkPatientId, checkDoctorId, checkDoctorClinicId, createSessionMessage, updateMedicalDataDB, getPreviousSessions, getPatientSessions, getDoctorDashboardData, getDoctorHomeData, getReportSubmissionData
from datetime import datetime, timedelta
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from auth import createAccessToken, createRefreshToken, decodeToken, hash_password, validate_password, getCurrentUser
from schema import patientRegister, doctorRegister, LoginRequest, MakeSessionRequest, NewMessage, Notes, AcceptEmergency, sessionResponse,  UpdateMedicalData
from utils import makeAvatarIdP, loadBmiData, APIException
from fastapi.responses import JSONResponse, FileResponse
from uuid import uuid4
from pathlib import Path
import shutil
import base64
from enum import Enum
import asyncio
#see disconnect edgecases or mistakes
#using path
UPLOAD_DIR = Path("uploads/chat")
os.makedirs(UPLOAD_DIR, exist_ok = True)
#dont give the same names of websocket to all the files
#using os
TO_UPLOAD_DIR = "folder"
os.makedirs(TO_UPLOAD_DIR, exist_ok = True)



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
    def disconnect(self, userId:int, connectionType:ConnectionType, sessionId:int|None = None):
        if connectionType == ConnectionType.ACTIVE:
            self.activeConnections.pop(userId, None)       #do nothing if not exists
        elif connectionType == ConnectionType.SESSION:
            if sessionId in self.SessionConnections:
                self.SessionConnections[sessionId].pop(userId, None)
        elif connectionType == ConnectionType.CALL:
            if sessionId in self.CallConnections:
                self.CallConnections[sessionId].pop(userId, None)
                if len(self.CallConnections[sessionId]) == 0:
                    del self.CallConnections[sessionId]
    def get(self, connectionType:ConnectionType, userId: int|None=None, sessionId:int|None=None):  #make sure the compulsary ones comes first
        if connectionType == ConnectionType.ACTIVE:
            return self.activeConnections.get(userId)
        elif connectionType == ConnectionType.SESSION:
            return self.SessionConnections.get(sessionId, {})
        elif connectionType == ConnectionType.CALL:
            return self.CallConnections.get(sessionId, {})
    def createSessionBlock(self, connectionType, sessionId):
        if connectionType == ConnectionType.SESSION:
            if sessionId not in self.SessionConnections:
                self.SessionConnections[sessionId] = {}

        elif connectionType == ConnectionType.CALL:
            if sessionId not in self.CallConnections:
                self.CallConnections[sessionId] = {}

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
    sessionId = None
    connectionType = None
    try:
        data = await websocket.receive_json()
        if data.get("type") != "connect":
            await websocket.close(code=1008)
            return
        accessToken = data["accessToken"]
        payload = decodeToken(accessToken)
        userId = payload["userId"]
        role = payload["role"]
        sessionId = data.get("sessionId")
        connectionType = data["page"]
        if sessionId:
            result = checkSessionUser(sessionId, userId)
            if result is None:
                await websocket.close(code=1008)
                return

        if data["page"] == "session" or data["page"] == "call":
            flag = False
            participants = socket.get(
                            connectionType=ConnectionType(data["page"]),
                            sessionId=data["sessionId"]
                        )
            if participants is None:
                flag = True
                socket.createSessionBlock(connectionType=ConnectionType(data["page"]), sessionId=data["sessionId"])
            await socket.connect(userId=userId, websocket=websocket, role=result["role"], connectionType=ConnectionType(data["page"]), sessionId=data.get("sessionId"))
            if data["page"] == "call":
                if flag == True:
                    users = getSessionUsers(sessionId=data["sessionId"])
                    connections = socket.get(connectionType=ConnectionType.CALL, sessionId=data["sessionId"])
                    for user in users:
                        if user == userId:
                            continue
                        else:
                            connection = connections.get(user, {})
                            if connection:
                                await connection["websocket"].send_json({"type":"call started"})
                            else:
                                pendingConnections["session"].setdefault(user, []).append(
                                    {
                                        "type":"call started"
                                    }
                                )
        else:
            await socket.connect(userId=userId, websocket=websocket, role=role, connectionType=ConnectionType(data["page"]))
        if data["page"] == "call":
            participants = socket.get(
                connectionType=ConnectionType.CALL,
                sessionId=sessionId
            )
            for uid, info in participants.items():
                if uid == userId:
                    continue

                await info["websocket"].send_json({
                    "type": "participant_joined",
                    "userId": userId,
                    "role": result["role"],
                    "initiator": True
                })
            for uid, info in participants.items():
                if uid == userId:
                    continue

                await websocket.send_json({
                    "type": "participant_joined",
                    "userId": uid,
                    "role": info["role"],
                    "initiator": False
                })

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
                    await websocket.send_json({
                        "type": "error",
                        "message": "Emergency not found"
                    })
                    continue
                if activeEmergencies[sessionId]["assignedDoctor"] is not None:     #if 2 people clicks at a time
                    await websocket.send_json({
                        "type": "error",
                        "message": "Emergency already accepted"
                    })
                    continue
                activeEmergencies[sessionId]["assignedDoctor"] = userId
                result = updateRefferedDoctorDetails(sessionId, userId)
                if result:
                    users = activeEmergencies[sessionId]["doctorList"]
                    for user in users:
                        connections = socket.get(connectionType=ConnectionType.ACTIVE, userId=user)
                        #fill out here
                    activeEmergencies[sessionId]["event"].set()
                    participants = socket.get(ConnectionType.SESSION, sessionId=sessionId)
                    for user in participants.values():
                        await user["websocket"].send_json({
                            "type" : "doctor2Details",
                            "name": result["Doctor2name"]
                        })
            elif message["type"] == "offer":
                if message.get("offer") is None:
                    await websocket.send_json({
                        "type":"error",
                        "message":"offer Missing"
                    })
                    continue
                if message.get("userId") is None:
                    await websocket.send_json({
                        "type":"error",
                        "message":"UserId missing"
                    })
                    continue
                targetUserId = message["userId"]
                connections = socket.get(connectionType=ConnectionType.CALL, sessionId=sessionId)
                if targetUserId in connections:
                    connection = connections[targetUserId]
                    await connection["websocket"].send_json({
                        "type":"offer",
                        "offer":message["offer"],
                        "userId":userId
                    })
                else:
                    await websocket.send_json({
                        "type":"error",
                        "message":"User Not Found"
                    })
            elif message["type"] == "answer":
                if message.get("answer") is None:
                    await websocket.send_json({
                        "type":"error",
                        "message":"Answer Missing"
                    })
                    continue
                if message.get("userId") is None:
                    await websocket.send_json({
                        "type":"error",
                        "message":"UserId missing"
                    })
                    continue
                targetUserId = message["userId"]
                connections = socket.get(connectionType=ConnectionType.CALL, sessionId=sessionId)
                if targetUserId in connections:
                    connection = connections[targetUserId]
                    await connection["websocket"].send_json({
                        "type":"answer",
                        "answer":message["answer"],
                        "userId":userId
                    })
                else:
                    await websocket.send_json({
                        "type":"error",
                        "message":"User Not Found"
                    })
            elif message["type"] == "ice-candidate":
                if message.get("candidate") is None:
                    await websocket.send_json({
                        "type":"error",
                        "message":"Candidate is missing"
                    })
                    continue
                if message.get("userId") is None:
                    await websocket.send_json({
                        "type":"error",
                        "message":"UserId missing"
                    })
                    continue
                targetUserId = message["userId"]
                connections = socket.get(connectionType=ConnectionType.CALL, sessionId=sessionId)
                if targetUserId in connections:
                    connection = connections[targetUserId]
                    await connection["websocket"].send_json({
                        "type":"ice-candidate",
                        "candidate":message["candidate"],
                        "userId":userId
                    })
                else:
                    await websocket.send_json({
                        "type":"error",
                        "message":"User Not Found"
                    })
            elif message["type"] == "leave_call":

                participants = socket.get(
                    connectionType=ConnectionType.CALL,
                    sessionId=sessionId
                )
                for uid, info in participants.items():
                    if uid != userId:
                        await info["websocket"].send_json({
                            "type":"participant_left",
                            "userId":userId
                        })
                socket.disconnect(
                    userId=userId,
                    connectionType=ConnectionType.CALL,
                    sessionId=sessionId
                    )
        
    except WebSocketDisconnect:
        if userId is not None:
            socket.disconnect(connectionType, userId, sessionId)
    except Exception as e:
        print(e)
        if userId is not None:
            socket.disconnect(connectionType, userId, sessionId)
        await websocket.close(code=1011)
        return

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):

    error = exc.errors()[0]

    return JSONResponse(
        status_code=422,
        content={
            "code": "ValidationError",
            "field": error["loc"][-1],               #tuple
            "detail": error["msg"]
        }
    )
@app.exception_handler(APIException) 
async def validate_response_error(request, exc):  #request is for the request which caused error
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "detail": exc.detail
        }
    )

@app.get("/refresh")
def refresh_token(request:Request):  #request is the entire piece of data or what you send to backend no need ot send the cookie if sent in htppsonlycookie
    refreshToken = request.cookies.get(
        "refreshToken"
    )
    if not refreshToken:
        raise APIException(
            status_code=401,
            code="MISSING_REFRESH_TOKEN",
            detail="Refresh Token Missing"
        )
    payload = decodeToken(refreshToken)
    if(payload.get("type")!="refresh"):                  #jwtdecode only sees the signature correct not expire only these but you need others also right like whats the purpose of this token
        raise APIException(
            status_code=401,
            code="INVALID_TOKEN",
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
        raise APIException(
            status_code=500,
            code="SERVER_ISSUE",
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
        raise APIException(
            status_code=500,
            code="SERVER_ISSUE",
            detail="Something went wrong while registering user"
        )

@app.post("/login")
def user_database_login(user:LoginRequest, response:Response):
    if user.person == "doctor":
        result = checkDoctorId(user.id)
    elif user.person == "patient":
        result = checkPatientId(user.id)

    if result is None:
        raise APIException(
            status_code=404,
            code="USER_MISSING",
            detail="User not found"
        )
    userId, passwordHash = result

    if not validate_password(user.password, passwordHash):
        raise APIException(
            status_code=401,
            code="INVALID_PASSWORD",
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
        raise APIException(
            status_code=401,
            code="REFRESH_TOKEN_MISSING",
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
        raise APIException(
            status_code=403,
            code="INVALID_USER",
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
        conn = socket.get(connectionType=ConnectionType.ACTIVE, userId=doctorId)
        if conn:
            conn.send_json({
                "type":"validDetails"
            })
        else:
            pendingConnections["active"].setdefault(doctorId, []).append({"type":"validDetails",
                                                                          "expireAt":datetime.now()+timedelta(minutes=5)})
    if data.healthId in pendingRequests:
        raise APIException(
            status_code=409,
            code="INVALID_REQUEST",
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
        status = pendingRequests[data.healthId]["status"]
        if status == "success":
            result = makeSession(doctorId=doctorId, patientId=data.healthId, department = data.department, clinicId= data.clinicId)
            if connection:
                await connection["websocket"].send_json({
                    "type":"Accepted",
                    "sessionId":result.sessionId
                })
            else:
                pendingConnections["active"].setdefault(doctorId, []).append({
                    "type":"Accepted",
                    "sessionId":result.sessionId
                })
            res = getSessionDetails(result.sessionId)
            if res is None:
                raise APIException(
                    status_code=404,
                    code="INVALID_SESSION",
                    detail="Session not found."
                )
            pconnection = socket.get(connectionType=ConnectionType.ACTIVE, userId=data.healthId)
            if pconnection:
                await pconnection["websocket"].send_json(
                    {
                        "type":"session_success_details",
                        "sessionId":result.sessionId,
                        "avatarId":data.pavatarId,
                        "patientName":data.patientName,
                        "patientAge":data.patientAge,
                        "patientGender":data.patientGender,
                        "sessionStartDate":data.createdAt.strftime("%d %b %Y"),            #22 july 2026
                        "sessionStartTime":data.createdAt.strftime("%I:%M %p")             # 7:45pm
                    }
                )
        elif status == "failure":
            if connection:
                        await connection["websocket"].send_json({
                            "type":"Rejected"
                        })
            else:
                pendingConnections["active"].setdefault(doctorId, []).append({
                    "type":"Rejected"
                })
            #fill here what happens when user clicks success or when user rejects and other things
    except asyncio.TimeoutError:
        connection = socket.get(connectionType=ConnectionType.ACTIVE, userId=doctorId)
        if connection:
            await connection["websocket"].send_json({
                "type":"Expired"
            })
        else:
            pendingConnections[ConnectionType.ACTIVE.value].setdefault(doctorId, []).append(
                {
                    "type":"Expired"
                }
            )
    finally:
        pendingRequests.pop(data.healthId, None)

            
@app.post("/sessionvalidation")
async def respondSession(data:sessionResponse, currentUser=Depends(getCurrentUser)):
    userId = currentUser["userId"]
    result1 = checkPatientId(userId)
    if result1 is None:
        raise APIException(
            status_code=404,
            code="USER_MISSING",
            detail="User Not Found"
        )
    res = pendingRequests.get(userId, [])
    if res is None:
        raise APIException(
            status_code=404,
            code="INVALID_REQUEST",
            detail="No session Requested for the User"
        )
    if data.message == "success":
        pendingRequests[userId]["status"] = "success"
        pendingRequests[userId]["event"].set()
    elif data.message == "failure":
        pendingRequests[userId]["status"] = "failure"
        pendingRequests[userId]["event"].set()

  
@app.get("/success-failure/sessionDetails/{sessionId}")
def giveSessionBasicDetails(sessionId:int, currentUser = Depends(getCurrentUser)):
    doctorId = currentUser["userId"]
    result1 = checkDoctorClinicId(sessionId=sessionId, doctorId=doctorId)
    if not result1:
        raise APIException(
            status_code=404,
            code="INVALID_SESSION",
            detail="Session Not Found"
        )
    result = getSessionDetails(sessionId)
    return {
        "patientName":result["patientName"],
        "sessionId":sessionId,
        "doctorName":result["doctorName"],
        "createdAt":result["createdAt"],
        "clinicName":result["clinicName"]
    }


@app.get("/session_detail/{sessionId}")
def giveDataSessionDetail(sessionId:int, currentUser=Depends(getCurrentUser)):
    result = checkSessionId(sessionId)
    if not result:
        raise APIException(
            status_code=404,
            code="INVALID_SESSION",
            detail="Session Not Found"
        )
    doctorId = currentUser["userId"]
    if doctorId not in {result.doctor1Id, result.doctor2Id}:
        raise APIException(
            status_code=403,
            code="INVALID_USER",
            detail="User Unauthorised"
        )
    userDetails = getDoctorDetails(doctorId)
    messages = getSessionMessages(sessionId)
    participantCount = 2
    if result.doctor2Id is not None:
        participantCount += 1
    for message in messages:

        readCount = getReadCount(message["messageId"])
        message["bluetick"] = (readCount == participantCount)
        
    res = {}
    res.update(userDetails)
    res.update(result)
    res["messages"] = messages

    return res

@app.get("/patient_session/{sessionId}")
def patientSessionDetail(sessionId: int, currentUser=Depends(getCurrentUser)):
    result = checkSessionId(sessionId)

    if not result:
        raise APIException(
            status_code=404,
            code="INVALID_SESSION",
            detail="Session Not Found"
        )

    patientId = currentUser["userId"]

    if patientId != result.patientId:
        raise APIException(
            status_code=403,
            code="INVALID_USER",
            detail="User Unauthorised"
        )

    userDetails = getPatientDetails(patientId)
    messages = getSessionMessages(sessionId)

    participantCount = 2
    if result.doctor2Id is not None:
        participantCount += 1

    for message in messages:
        readCount = getReadCount(message["messageId"])
        message["bluetick"] = (readCount == participantCount)

    res = {}
    res.update(userDetails)
    res.update(result)
    res["messages"] = messages

    return res

@app.get("/patient_waiting_room/{sessionId}")
def patientWaitingRoom(sessionId: int, currentUser=Depends(getCurrentUser)):
    # 1. Session exists?
    session = checkSessionId(sessionId)
    if not session:
        raise APIException(
            status_code=404,
            code="INVALID_SESSION",
            detail="Session Not Found"
        )

    # 2. Logged in user is the patient?
    patientId = currentUser["userId"]

    if patientId != session.patientId:
        raise APIException(
            status_code=403,
            code="INVALID_USER",
            detail="User Unauthorised"
        )

    # 3. Patient details
    patientDetails = getPatientDetails(patientId)
    # 4. Doctor details
    doctor1Details = getDoctorDetails(session.doctor1Id)
    doctor2Details = None
    if session.doctor2Id:
        doctor2Details = getDoctorDetails(session.doctor2Id)
    # 5. Active call details
    call = {
        "isCall": False,
        "participants": []
    }
    connections = socket.get(connectionType=ConnectionType.CALL, sessionId=sessionId)
    if connections:
        call["isCall"] = True
        for connection in connections:
            if connection["role"] == "patient":
                details = getPatientDetails(connection["userId"])
            else:
                details = getDoctorDetails(connection["userId"])
            call["participants"].append({
                "userId": connection["userId"],
                "role": connection["role"],
                "name": details["name"]
            })
    # 6. Build response
    result = {
        "userId": patientId,
        "name": patientDetails["name"],
        "avatarId": patientDetails["avatarId"],
        # Doctor displayed in banner
        "doctorName": doctor1Details["name"],
        "doctorAvatarId": doctor1Details["avatarId"],
        # Session
        "sessionId": session.sessionId,
        "startTime": session.startTime,
        # Patient information
        "patientName": patientDetails["name"],
        "patientAge": patientDetails["age"],
        "patientGender": patientDetails["gender"],
        # Assigned doctors
        "doctor1Name": doctor1Details["name"],
        "doctor2Name":
            doctor2Details["name"]
            if doctor2Details
            else None,
        # Video call state
        "call":call
    }
    return result
@app.get("/doctor_waiting_room/{sessionId}")
def doctorWaitingRoom(sessionId: int, currentUser=Depends(getCurrentUser)):
    # 1. Session exists?
    session = checkSessionId(sessionId)
    if not session:
        raise APIException(
            status_code=404,
            code="INVALID_SESSION",
            detail="Session Not Found"
        )
    doctorId = currentUser["userId"]
    if doctorId not in {session.doctor1Id, session.doctor2Id}:
        raise APIException(
            status_code=403,
            code="INVALID_USER",
            detail="User Unauthorised"
        )
    # Logged in doctor (profile card)
    loginDoctorDetails = getDoctorDetails(doctorId)
    # Actual doctor 1
    doctor1Details = getDoctorDetails(session.doctor1Id)
    # Actual doctor 2
    doctor2Details = None
    if session.doctor2Id:
        doctor2Details = getDoctorDetails(session.doctor2Id)
    # Patient
    patientDetails = getPatientDetails(session.patientId)
    # Call information
    call = {
        "isCall": False,
        "participants": []
    }
    connections = socket.get(
        connectionType=ConnectionType.CALL,
        sessionId=sessionId
    )
    if connections:
        call["isCall"] = True
        for connection in connections:
            if connection["role"] == "patient":
                details = getPatientDetails(
                    connection["userId"]
                )
            else:
                details = getDoctorDetails(
                    connection["userId"]
                )
            call["participants"].append(
                {
                    "userId": connection["userId"],
                    "role": connection["role"],
                    "name": details["name"]
                }
            )
    result = {
        # logged in doctor
        "userId": doctorId,
        "name": loginDoctorDetails["name"],
        "avatarId": loginDoctorDetails["avatarId"],
        # patient
        "patientAvatar": patientDetails["avatarId"],
        "patientName": patientDetails["name"],
        "patientAge": patientDetails["age"],
        "patientGender": patientDetails["gender"],
        # session
        "sessionId": session.sessionId,
        "startTime": session.startTime,
        # doctors in session
        "doctor1Id": session.doctor1Id,
        "doctor2Id": session.doctor2Id,
        "doctor1Name": doctor1Details["name"],
        "doctor2Name":
            doctor2Details["name"]
            if doctor2Details
            else None,
        # referral
        "isReferred": session.isReferred,
        # call
        "call": call
    }
    return result
@app.get("/download-file-chat/{attachmentId}")
def giveFile(request:Request, attachmentId:int):
    refreshToken = request.cookies.get("refreshToken")
    if not refreshToken:
        raise APIException(
            status_code=403,
            code="INVALID_USER",
            detail="Unauthorised"
        )
    payload = decodeToken(refreshToken)
    if payload["type"] != "refresh":
        raise APIException(
            status_code=401,
            code="INVALID_TOKEN",
            detail="Invalid token"
        )
    userId = payload["userId"]
    result = getAttachmentDetails(userId=userId, attachmentId = attachmentId)
    if result is None:
        raise APIException(
            status_code=404,
            code="USER_MISSING",  
            detail="User Not Found"
        )
    
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
        raise APIException(
            status_code=404,
            code="USER_MISSING",
            detail="User Not Found"
        )
    return {"message":"Notes Updatad Finally"}

@app.get("/download_report/{sessionId}")
async def download_report(
    sessionId: int,
    currentUser = Depends(getCurrentUser)
):
    userId = currentUser["userId"]
    # Only patients can download reports
    if currentUser["type"] != "patient":
        raise APIException(
            status_code=403,
            code="INVALID_USER",
            detail="Access denied."
        )

    report = getReport(sessionId, userId)      # checks if user is valid and gives the file
    if not report:
        raise APIException(
            status_code=403,
            code="USER_PROHIBITED",
            detail="User is Forbidden"
        )

    file_path = Path(report["reportPath"])

    if not file_path.exists():
        raise APIException(
            status_code=404,
            code="FILE_MISSING",
            detail="File missing."
        )

    return FileResponse(
        path=file_path,
        media_type=report["content_type"],
        filename=file_path.name
    )
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
                pendingConnections[ConnectionType.ACTIVE.value].setdefault(doctors, []).append({    #so that if key doesnt exist makes a list 
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
                pendingConnections[ConnectionType.ACTIVE.value].setdefault(doctors, []).append({
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
        raise APIException(
            status_code=403,
            code="INVALID_USER",
            detail="Only doctors can start emergency"
        )
    sessionId = data.sessionId
    userId = currUser["userId"]
    result = checkDoctorClinicId(doctorId=userId, clinicId=sessionId)
    if result is None:
        raise APIException(
            status_code=403,
            code="INVALID_USER",
            detail="Unauthorised"
        )
    res = checkSessionEmergency(sessionId)
    if res is not None:
        raise APIException(
            status_code=403,
            code="INVALID_REQUEST",
            detail="New Emergency cant be created"
        )
    if activeEmergencies.get(sessionId):
        raise APIException(
            status_code=409,
            code="EMERGENCY_EXISTS",
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
    

@app.get("/in_call")
# SELECT
#     CASE
#         WHEN patientId = ? THEN 'patient'
#         WHEN doctor1Id = ? THEN 'doctor1'
#         WHEN doctor2Id = ? THEN 'doctor2'
#     END AS myRole
# FROM sessions
# WHERE sessionId = ?
# AND (
#     patientId = ?
#     OR doctor1Id = ?
#     OR doctor2Id = ?
# );
def enterCall(sessionId:int, curr = Depends(getCurrentUser)):
    userId = curr["userId"]
    result = checkSessionUser(userId=userId, sessionId=sessionId)  
    if result is None:
        raise APIException(
            status_code=403,
            code="INVALID_USER",
            detail="Unauthorised user or session"
        )
    return {"userId":userId,
            "myRole":result["myRole"]}

@app.get("/report_submission")
async def reportSubmission(
    sessionId: int,
    currentUser=Depends(getCurrentUser)
):
    doctorId = currentUser["userId"]
    result1 = checkUserPermissionToEndSession(doctorId, sessionId)
    #should see if the user can modify the result submission or not
    if result1 is not None:
        raise APIException(
            status_code=403,
            code="INVALID_USER",
            detail="User Forbidden"
        )

    data = getReportSubmissionData(sessionId, doctorId)

    if data is None:
        raise APIException(
            status_code=404,
            code="INVALID_SESSION",
            detail="Session not found."
        )

    return data

@app.post("/submit_report")
async def submit_report(
    report: UploadFile = File(...),
    sessionId: int = Form(...),
    bloodPressure: str = Form(""),
    bloodSugar: str = Form(""),
    temperature: str = Form(""),
    heartRate: str = Form(""),
    chiefComplaint: str = Form(...),
    additionalVitals: str = Form(...),
    currentUser=Depends(getCurrentUser)
):
    userId = currentUser["userId"]
    # doing these because user can even change the html and submit so 
    result1 = checkUserPermissionToEndSession(userId, sessionId)
    #should see if the user can modify the result submission or not
    if result1 is not None:
        raise APIException(
            status_code=403,
            code="INVALID_USER",
            detail="User Forbidden"
        )
    # these are MIME types so remember these
    allowed = {
        "application/pdf",
        "image/png",
        "image/jpeg"
    }
    if report.content_type not in allowed:
        raise APIException(
            status_code=400,               #bad request means 400
            code="BAD_REQUEST",
            detail="Invalid file type."
        )
    contents = await report.read()
    if len(contents)>10*1024*1024:
        raise APIException(
            status_code=400,
            code="BAD_REQUEST",
            detail="Maximum size of file is 10mb"
        )
    file_path = None
    try:
        _, file_ext = os.path.splitext(report.filename)
        resolved_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_total_name = f"{str(sessionId)}_{resolved_time}{file_ext}"
        file_path = os.path.join(TO_UPLOAD_DIR, file_total_name)
        with open(file_path, "wb") as f:
            f.write(contents)
        result = complete_patient_session(session_id=int(sessionId), chief_complaint=chiefComplaint, additional_vitals=additionalVitals,uploaded_filepath=file_path,content_type=report.content_type, resolved_time=resolved_time, blood_pressure=bloodPressure, blood_sugar=bloodSugar,temperature=temperature, heart_rate=heartRate )
        #dont forget to make the session resolved and reffered
        #dont forget to increase the count of doctorId 
        if result is None:
            raise APIException(
                status_code=500,
                code="SERVER_ISSUE",
                detail="Unable to complete session."
            )
        connections = socket.get(connectionType=ConnectionType.SESSION, sessionId=sessionId)
        if connections:
            for users in connections:
                if users:
                    await users["websocket"].send_json({
                        "type":"sessionCompleted",
                        "sessionId":sessionId
                    })
        return {
            "message":"Session Completed Finally"
        }
    except APIException:
        raise
    except Exception as e:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        raise APIException(status_code=500,code="SERVER_ISSUE", detail=f"Internal server problem ")  #no need of priing the str because no need to say whats problem with the server
    
@app.post("/update_medical_data")
async def updateMedicalData(
    data: UpdateMedicalData,
    currentUser=Depends(getCurrentUser)
): 
    userId = currentUser["userId"]
    success = updateMedicalDataDB(userId, data)
    if not success:
        raise APIException(
            status_code=404,
            code="USER_MISSING",
            detail="Unable to update medical data as user is not found"
        )

    return {
        "message": "Medical data updated successfully"
    }
    
@app.get("/patient_medical_data")
async def patientMedicalData(currentUser=Depends(getCurrentUser)):
    patientId = currentUser["userId"]
    role = currentUser["role"]
    if role!="patient":
        raise APIException(
            status_code=403,
            code="INVALID_USER",
            detail="User Forbidden"
        )

    data = getPatientMedicalData(patientId)
    if data is None:
        raise APIException(
            status_code=404,
            code="USER_MISSING",
            detail="Patient not found"
        )
    gender = data["gender"]
    age = data["age"]
    if gender == "Male":
        if age < 2:
            file = "Excel/birth_2_boys.csv"
        elif age < 5:
            file = "Excel/2_5_boys.csv"
        elif age <= 19:
            file = "Excel/bmi-boys-perc-who2007-exp.csv"
        else:
            file = None
    else:
        if age < 2:
            file = "Excel/birth_2_girls.csv"
        elif age < 5:
            file = "Excel/2_5_girls.csv"
        elif age <= 19:
            file = "Excel/bmi-girls-perc-who2007-exp.csv"
        else:
            file = None
    data["file"] = loadBmiData(file) if file else None 
    return data

@app.get("/patient_previous_sessions")
async def patientPreviousSessions(currentUser=Depends(getCurrentUser)):
    if currentUser["role"] != "patient":
        raise APIException(
            status_code=403,
            code="INVALID_USER",
            detail="Only patients can access previous sessions."
        )

    patientId = currentUser["userId"]

    data = getPreviousSessions(patientId)

    if data is None:
        raise APIException(
            status_code=404,
            code="USER_MISSING",
            detail="Patient data not found."
        )

    return data

@app.get("/patient_sessions")
async def patientSessions(currentUser = Depends(getCurrentUser)):
    userId = currentUser["userId"]
    if currentUser["role"] != "patient":
            raise APIException(
                status_code=403,
                code="INVALID_USER",
                detail="Only patients can access previous sessions."
            ) 
    data = getPatientSessions(userId)
    if data is None:
        raise APIException(
            status_code=404,
            code="USER_MISSING",
            detail="Patient not found."
        )
    return data

@app.get("/doctor_dashboard")
async def doctorDashboard(currentUser=Depends(getCurrentUser)):
    if currentUser["role"] != "doctor":
        raise APIException(
            status_code=403,
            code="INVALID_USER",
            detail="Only doctors can access this page."
        )
    doctorId = currentUser["userId"]
    data = getDoctorDashboardData(doctorId)
    if data is None:
        raise APIException(
            status_code=404,
            code="USER_MISSING",
            detail="Doctor not found."
        )

    return data

@app.get("/index")
async def doctorIndex(currentUser=Depends(getCurrentUser)):
    if currentUser["role"] != "doctor":
        raise APIException(
            status_code=403,
            code="INVALID_USER",
            detail="Only doctors can access this page."
        )

    doctorId = currentUser["userId"]

    data = getDoctorHomeData(doctorId)

    if data is None:
        raise APIException(
            status_code=404,
            code="USER_MISSING",
            detail="Doctor not found."
        )

    return data


# def make_session(health_id:str = Form(...), clinic_id:str = Form(...), department:str = Form(...), assigned_doctor_id:str = Form(...)):
#     #make check when unkown patient_name comes or unknown_doc_name or clinic name comes
#     return create_patient_session(health_id, clinic_id, department, assigned_doctor_id)


# @app.post("/api/sessions/{session_id}/submit")
# async def complete_session(request:Request,chief_complaint:str = Form(...), additional_vitals:str = Form(...), uploaded_filepath:UploadFile = File(...),
#                             blood_pressure: Optional[str] = Form(None), blood_sugar: Optional[float] = Form(None), temperature:Optional[float] = Form(None), 
#                             heart_rate: Optional[int] = Form(None)):
#     file_path = None
#     try:
#         _, file_ext = os.path.splitext(uploaded_filepath.filename)
#         if not file_ext:
#             file_ext = '.jpg'
#         session_id = request.path_params.get("session_id")
#         resolved_time = datetime.now().strftime("%Y%m%d_%H%M%S")
#         file_total_name = f"{str(session_id)}_{resolved_time}{file_ext}"
#         file_path = os.path.join(TO_UPLOAD_DIR, file_total_name)
#         with open(file_path, "wb") as f:
#             content = await uploaded_filepath.read()
#             f.write(content)
#         result = complete_patient_session(session_id=int(session_id), chief_complaint=chief_complaint, additional_vitals=additional_vitals,uploaded_filepath=file_path,resolved_time=resolved_time, blood_pressure=blood_pressure, blood_sugar=blood_sugar,temperature=temperature, heart_rate=heart_rate )
#         return result
#     except Exception as e:
#         if file_path and os.path.exists(file_path):
#             os.remove(file_path)
#         raise APIException(status_code=500,code="SERVER_ISSUE", detail=f"Internal server problem : {str(e)}")
        

# @app.get("/api/sessions/emergency")
# async def connect_hospitals(session_id:int = Query(..., description="The ID of the current consultation session"),
#                       clinic_id: int = Query(..., description="The ID of the requesting clinic"),
#                       department: str = Query(..., description="The department stream (e.g., Cardiology)")):
#     try:
#         results = emergency_connect_hospitals(session_id=session_id, clinic_id=clinic_id, department=department)
        
#         for result in results:
#             await connections[result[0]].send_text()
#         return results
#     except Exception as e:
#         raise APIException(status_code=500, detail=f"Internal sever issue: {str(e)}")
    
# connections = {}
# @app.websocket("/ws/doctor")
# async def make_connections_doctor(websocket:WebSocket):
#     doctor_id = websocket.query_params["doctor_id"]
#     await websocket.accept()
#     connections[doctor_id] = websocket
#     result = make_available_doctor(doctor_id=doctor_id)
#     return result

    






































    
# @app.post("/api/sessions/{session_id}/escalate")
# async def escalate_session(session_id: int):
#     try:
#         emergency_data = trigger_emergency_escalation(session_id)

#         if not emergency_data:
#             raise HTTPException(
#                 status_code=404, 
#                 detail=f"Session with ID {session_id} not found."
#             )
            
#         return{
#             "status": "success",
#             "message": "Session escalated to emergency successfully.",
#             "data": emergency_data
#         }
        
#     except Exception as e:
#         raise HTTPException(
#             status_code=500, 
#             detail=f"Internal server error during escalation: {str(e)}"
#         )



