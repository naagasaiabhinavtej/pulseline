import sqlite3
from typing import Optional
import math
import logging
from datetime import datetime, date

database_path = "medical_platform.db"

logger = logging.getLogger(__name__)


def patientLogin(patientData:dict):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        patientData["height"] = float(patientData["height"])
        patientData["weight"] = float(patientData["weight"])
        cursor.execute("""
                            INSERT INTO patients
                            (health_id,
                            password,
                            name,
                            avatarId,
                            date_of_birth,
                            gender,
                            blood_group,
                            height,
                            weight,
                            medical_history,
                            allergies,
                            emergency_contact)
                            VALUES
                            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (patientData["health_id"],
                             patientData["password"],
                            patientData["name"],
                            patientData["avatarId"],
                            patientData["date_of_birth"],
                            patientData["gender"],
                            patientData["blood_group"],
                            patientData["height"],
                            patientData["weight"],
                            patientData["medical_history"],
                            patientData["allergies"],
                            patientData["emergency_contact"]))
        userId = cursor.lastrowid
        
        conn.commit()
        return{
            "userId":userId,
            "message":"Details Uploaded"
        }

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Error while creating user")
        raise e
    finally:
        conn.close()

def doctorLogin(doctorDict:dict):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        doctorDict.assigned_clinic_id = int(doctorDict.assigned_clinic_id)
        curs.execute("""
                        INSERT INTO doctors
                        (
                            name,
                            avatarId,
                            specialization,
                            contact_number,
                            assigned_clinic_id
                        )
                        VALUES
                        (?,?,?,?,?)
                        """, 
                        (doctorDict["name"],
                        doctorDict["avatarId"],
                        doctorDict["specialization"],
                        doctorDict["contact_number"],
                        doctorDict["assigned_clinic_id"]))
        userId = curs.lastrowid
        conn.commit()
        return {"userId":userId,
                "message":"Details Uploaded"}

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Error while creating user")
        raise e
    finally:
        conn.close()


def checkPatientId(health_id:str):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        health_id = int(health_id)
        curs.execute("""
                        SELECT health_id, password
                        FROM patients
                        WHERE health_id=?
                    """, (health_id,))
        result = curs.fetchone()
        return result
    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Error while checking the User")
        raise e
    finally:
        if conn:
            conn.close()
def checkDoctorId(doctor_id:str):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        doctor_id = int(doctor_id)
        curs.execute("""
                        SELECT doctor_id, password
                        FROM doctors
                        WHERE doctor_id=?
                    """, (doctor_id,))
        result = curs.fetchone()
        return result
    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Error while checking the User")
        raise e
    finally:
        if conn:
            conn.close()

def checkDoctorClinicId(doctorId:str, clinicId:str):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        doctorId = int(doctorId)
        clinicId = int(clinicId)
        curs.execute("""
                        SELECT doctor_id, password
                        FROM doctors
                        WHERE doctor_id=? AND clinic_id=?
                    """, (doctorId,clinicId))
        result = curs.fetchone()
        return result
    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Error while checking the Details of clinic and doctor")
        raise e
    finally:
        if conn:
            conn.close()

def checkSessionUser(sessionId:int, userId:int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        sessionId = int(sessionId)
        userId = int(userId)
        curs.execute("""
                        SELECT 
                        CASE 
                        WHEN health_id=? THEN "patient"
                        WHEN assigned_doctor_id=? THEN "doctor1"
                        WHEN referred_doctor_id=? THEN "doctor2"
                        END AS role
                        FROM consultation_sessions
                        WHERE session_id=? AND 
                        (health_id=? OR assigned_doctor_id=? OR referred_doctor_id=?) 
                    """, (userId, userId, userId,
                        sessionId,
                        userId, userId, userId))
        result = curs.fetchone()
        if result is None:
            return None
        return {
            "myRole": result[0]
        }
    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Error while checking the Details of user")
        raise e
    finally:
        if conn:
            conn.close()
def checkUserPermissionToEndSession(doctorId: int, sessionId: int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()

        curs.execute("""
            SELECT session_id
            FROM consultation_sessions
            WHERE session_id = ?
            AND (
                (is_referred = 0 AND assigned_doctor_id = ?)
                OR
                (is_referred = 1 AND referred_doctor_id = ?)
            )
        """, (sessionId, doctorId, doctorId))

        result = curs.fetchone()

        return result

    except Exception:
        if conn:
            conn.rollback()
        logger.exception("Error while checking session end permission")
        raise

    finally:
        if conn:
            conn.close()
def getSessionUsers(sessionId:int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        sessionId = int(sessionId)
        curs.execute("""
                        SELECT health_id, assigned_doctor_id, referred_doctor_id
                        FROM consultation_sessions
                        WHERE session_id=? 
                    """, (sessionId,))
        result = curs.fetchone()
        if result is None:
            return []   # wrote this because user in None will raise error
        return [user for user in result if result is not None]
    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Error while checking the Details of users in session")
        raise e
    finally:
        if conn:
            conn.close()
def getReport(sessionId: int, userId: int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row
        curs = conn.cursor()

        curs.execute("""
            SELECT
                uploaded_file_path AS reportPath,
                content_type
            FROM consultation_sessions
            WHERE session_id = ?
              AND health_id = ?
              AND uploaded_file_path IS NOT NULL
        """, (sessionId, userId))

        result = curs.fetchone()

        if result is None:
            return None

        return dict(result)

    except Exception:
        if conn:
            conn.rollback()
        logger.exception("Error getting report")
        return None

    finally:
        if conn:
            conn.close()
def updateRefferedDoctorDetails(sessionId:int, doctorId:int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row
        curs = conn.cursor()

        curs.execute("""
                        UPDATE consultation_sessions
                        SET
                            referred_doctor_id=?,
                            is_referred=1,
                            session_status='inReferral'
                        WHERE session_id=?
                    """, (doctorId, sessionId))

        if curs.rowcount == 0:
            conn.rollback()
            return None

        curs.execute("""
                        SELECT
                            name
                        FROM doctors
                        WHERE doctor_id=?
                    """, (doctorId,))

        result = curs.fetchone()

        conn.commit()

        return {
            "Doctor2name": result["name"]
        }

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Error updating referred doctor")
        return None

    finally:
        if conn:
            conn.close()
def getPatientMedicalData(patientId:int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row
        curs = conn.cursor()
        curs.execute("""
                        SELECT
                            health_id,
                            name,
                            avatarId,
                            date_of_birth,
                            gender,
                            blood_group,
                            height,
                            weight,
                            right_eye,
                            left_eye,
                            right_ear,
                            left_ear,
                            medical_history,
                            allergies,
                            emergency_contact
                        FROM patients
                        WHERE health_id=?
                    """, (patientId,))
        patient = curs.fetchone()
        if patient is None:
            return None
        curs.execute("""
                        SELECT
                            created_at,
                            department,
                            blood_pressure,
                            blood_sugar,
                            temperature,
                            heart_rate
                        FROM consultation_sessions
                        WHERE health_id=?
                        ORDER BY created_at DESC
                    """, (patientId,))
        sessions = curs.fetchall()
        return {
            "HealthID": patient["health_id"],
            "PatientName": patient["name"],
            "patientAvatarId": patient["avatarId"],
            "dateOfBirth": patient["date_of_birth"],
            "Gender": patient["gender"],
            "BloodGroup": patient["blood_group"],
            "Height": patient["height"],
            "Weight": patient["weight"],
            "RightEye": patient["right_eye"],
            "LeftEye": patient["left_eye"],
            "RightEarHearing": patient["right_ear"],
            "LeftEarHearing": patient["left_ear"],
            "EmergencyContact": patient["emergency_contact"],
            "MedicalHistory": patient["medical_history"],
            "Allergies": patient["allergies"],
            "sessionsData": [                     #see how list comprehension is useful
                {
                    "createdAt": session["created_at"],
                    "department": session["department"],
                    "bloodPressure": session["blood_pressure"],
                    "bloodSugar": session["blood_sugar"],
                    "temperature": session["temperature"],
                    "heartRate": session["heart_rate"]
                }
                for session in sessions
            ]
        }
    except Exception as e:
        logger.exception("Error getting patient medical data")
        return None
    finally:
        if conn:
            conn.close()
def getDoctorDetails(doctorId: int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row
        curs = conn.cursor()
        curs.execute("""
            SELECT
                doctor_id,
                name,
                avatarId,
                specialization
            FROM doctors
            WHERE doctor_id = ?
        """, (doctorId,))
        result = curs.fetchone()
        if result is None:
            return None
        return {
            "userId": result["doctor_id"],
            "name": result["name"],
            "avatarId": result["avatarId"],
            "specialization": result["specialization"]
        }
    except Exception:
        if conn:
            conn.rollback()
        logger.exception("Error while getting doctor details")
        return None
    finally:
        if conn:
            conn.close()
def getPatientDetails(patientId: int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        curs.execute("""
            SELECT
                name,
                avatarId,
                gender,
                CAST((julianday('now') - julianday(date_of_birth)) / 365.25 AS INTEGER) AS age
            FROM patients
            WHERE health_id = ?
        """, (patientId,))

        result = curs.fetchone()

        if result is None:
            return None

        return {
            "name": result[0],
            "avatarId": result[1],
            "gender": result[2],
            "age": result[3]
        }

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Error while getting patient details")
        return None

    finally:
        if conn:
            conn.close()
def createSessionMessage(sessionId:int, senderId:int, text:str, files:dict | None = None):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        curs.execute("""
                        INSERT INTO session_messages
                        (session_id, uploaded_by, message)
                        VALUES
                        (?,?,?)
                        """, (sessionId, senderId, text))
        messageId = curs.lastrowid
        attachmentId = None
        if files is not None:
            curs.execute("""
                        INSERT INTO session_attachments
                        (message_id, file_name, file_path)
                        VALUES
                        (?,?,?)
                        """, (messageId, files["fileName"], files["filePath"]))
            attachmentId = curs.lastrowid
        conn.commit()
        curs.execute("""
                        SELECT uploaded_at
                        FROM session_messages
                        WHERE message_id=?
                            """,(messageId,)) 
        timeStamp = curs.fetchone()[0]
        timeStamp = datetime.fromisoformat(timeStamp).strftime("%I:%M %p")
        curs.execute("""
            SELECT name, avatarId
            FROM patients
            WHERE health_id = ?
        """, (senderId,))

        sender = curs.fetchone()

        if sender is None:
            curs.execute("""
                SELECT name, avatarId
                FROM doctors
                WHERE doctor_id = ?
            """, (senderId,))

            sender = curs.fetchone()

        senderName = sender[0]
        avatarId = sender[1]
        return {
            "messageId": messageId,
            "attachmentId": attachmentId,
            "timestamp": timeStamp,
            "senderId": senderId,
            "senderName": senderName,
            "avatarId": avatarId,
            "text": text,
            "fileName": files["fileName"] if files else None,
            "date": datetime.fromisoformat(timeStamp).strftime("%d %b %Y")
        }
    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Error while adding the message into the database")
        raise e
    finally:
        if conn:
            conn.close()
def markMessageRead(messageId: int, userId: int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()

        # Prevent duplicate inserts
        curs.execute("""
            INSERT OR IGNORE INTO message_reads (message_id, user_id)
            VALUES (?, ?)
        """, (messageId, userId))

        # Get the session for this message
        curs.execute("""
            SELECT session_id
            FROM session_messages
            WHERE message_id = ?
        """, (messageId,))
        sessionId = curs.fetchone()[0]

        # Get all participants
        curs.execute("""
            SELECT
                health_id,
                assigned_doctor_id,
                referred_doctor_id
            FROM consultation_sessions
            WHERE session_id = ?
        """, (sessionId,))

        participants = [x for x in curs.fetchone() if x is not None]
        totalParticipants = len(participants)

        # Count how many have read
        curs.execute("""
            SELECT COUNT(*)
            FROM message_reads
            WHERE message_id = ?
        """, (messageId,))

        readCount = curs.fetchone()[0]

        conn.commit()

        return {
            "read": readCount == totalParticipants,
            "sessionId": sessionId
        }

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Error marking message as read")
        raise

    finally:
        if conn:
            conn.close()
def updateMedicalDataDB(patientId, data):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE patients
        SET
            height=?,
            weight=?,
            right_eye=?,
            left_eye=?,
            right_ear_hearing=?,
            left_ear_hearing=?,
            emergency_contact=?,
            medical_history=?,
            allergies=?
        WHERE patient_id=?
        """,
        (
            data.Height,
            data.Weight,
            data.RightEye,
            data.LeftEye,
            data.RightEarHearing,
            data.LeftEarHearing,
            data.EmergencyContact,
            data.MedicalHistory,
            data.Allergies,
            patientId
        ))
        conn.commit()
        updated = cursor.rowcount      
        #gives no of rows affected by previous sql query
        return updated > 0
    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Error while adding the message into the database")
        raise e   
    finally:
        if conn:
            conn.close()

#read the below funciton for sure
def getPreviousSessions(patientId: int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row
        curs = conn.cursor()
        curs.execute("""
            SELECT
                p.name AS patient_name,
                p.avatar_id AS patient_avatar,
                cs.session_id,
                cs.department,
                cs.issue,
                cs.bp,
                cs.hr,
                cs.temperature,
                cs.bs,
                cs.additional_vitals,
                cs.start_time,
                cs.end_time,
                cs.reffered_doctor_id,
                d1.name AS doctor1_name,
                d1.avatar_id AS doctor1_avatar,
                c1.name AS doctor1_hospital,
                d2.name AS doctor2_name,
                d2.avatar_id AS doctor2_avatar,
                c2.name AS doctor2_hospital
            FROM consultation_sessions cs
            JOIN patients p
                ON cs.health_id = p.health_id
            JOIN doctors d1
                ON cs.assigned_doctor_id = d1.doctor_id
            JOIN clinics c1
                ON d1.clinic_id = c1.clinic_id
            LEFT JOIN doctors d2         
                ON cs.reffered_doctor_id = d2.doctor_id
            LEFT JOIN clinics c2
                ON d2.clinic_id = c2.clinic_id
            WHERE
                cs.health_id = ?
                AND cs.status = 'completed'
            ORDER BY cs.end_time DESC
        """, (patientId,))
        #left join because doctor2 can be null too and also if join is sued then the sessions where doctor2 is not used is gone
        rows = curs.fetchall()
        if not rows:
            return None
        previousSessions = []
        patientName = rows[0]["patient_name"]
        avatarId = rows[0]["patient_avatar"]
        for row in rows:
            start = row["start_time"]
            end = row["end_time"]
            try:
                start = datetime.fromisoformat(start).strftime("%d %b %Y")
            except:
                start = start or ""
            try:
                end = datetime.fromisoformat(end).strftime("%d %b %Y")
            except:
                end = end or ""
            doctorTwo = None
            if row["doctor2_name"] is not None:
                doctorTwo = {
                    "name": row["doctor2_name"] or "",
                    "hospital": row["doctor2_hospital"] or "",
                    "avatarId": row["doctor2_avatar"] or "first"
                }
            previousSessions.append({
                "sessionId": row["session_id"],
                "department": row["department"] or "",
                "date": f"{start} → {end}",
                "issue": row["issue"] or "",
                "bp": row["bp"] or "---",
                "hr": row["hr"] or "---",
                "temperature": row["temperature"] or "---",
                "bs": row["bs"] or "---",
                "additionalVitals": row["additional_vitals"] or "",
                "isReferred": row["reffered_doctor_id"] is not None,
                "doctorOne": {
                    "name": row["doctor1_name"] or "Unknown Doctor",
                    "hospital": row["doctor1_hospital"] or "",
                    "avatarId": row["doctor1_avatar"] or "first"
                },
                "doctorTwo": doctorTwo
            })
        return {
            "patientName": patientName,
            "avatarId": avatarId,
            "previousSessions": previousSessions
        }
    except Exception:
        logger.exception("Error fetching previous sessions")
        return None
    finally:
        if conn:
            conn.close() 


def getReportSubmissionData(sessionId:int, doctorId:int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()

        curs.execute("""
            SELECT
                cs.session_id,
                cs.created_at,

                cs.assigned_doctor_id,
                cs.referred_doctor_id,

                d1.name,
                d2.name,

                p.name,
                p.gender,
                p.date_of_birth,
                p.avatarId

            FROM consultation_sessions cs

            JOIN patients p
                ON cs.health_id = p.health_id

            JOIN doctors d1
                ON cs.assigned_doctor_id = d1.doctor_id

            LEFT JOIN doctors d2
                ON cs.referred_doctor_id = d2.doctor_id

            WHERE
                cs.session_id = ?
                AND cs.session_status IN ('active','inReferral')
                AND (
                    (cs.is_referred = 0
                     AND cs.assigned_doctor_id = ?)
                    OR
                    (cs.is_referred = 1
                     AND cs.referred_doctor_id = ?)
                )
        """, (
            sessionId,
            doctorId,
            doctorId
        ))

        row = curs.fetchone()

        if row is None:
            return None


        # Calculate age
        dob = datetime.strptime(
            row[8],
            "%Y-%m-%d"
        ).date()

        today = date.today()

        age = (
            today.year
            - dob.year
            - (
                (today.month, today.day)
                <
                (dob.month, dob.day)
            )
        )


        start = datetime.fromisoformat(row[1])


        # Decide current doctor name
        if row[3] == doctorId:
            currentDoctorName = row[5]   # referred doctor
        else:
            currentDoctorName = row[4]   # assigned doctor


        return {
            "doctorName": currentDoctorName,
            "doctor1Name": row[4],
            "doctor2Name": row[5],
            "patientName": row[6],
            "patientAvatar": row[9],
            "age": age,
            "gender": row[7],
            "ageGender": f"{age} / {row[7]}",
            "startDate": start.strftime("%Y-%m-%d"),
            "startTime": start.strftime("%H:%M:%S")
        }


    except Exception:
        logger.exception(
            "Error while fetching report submission details"
        )
        raise

    finally:
        if conn:
            conn.close()
        
#still have this to complete but almost completed
def getDoctorHomeData(doctorId):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row #makes the result[name] no need of result[0] 
        curs = conn.cursor()
        # Doctor details
        curs.execute("""
            SELECT
                name,
                avatarId
            FROM doctors
            WHERE doctor_id = ?
        """, (doctorId,))
        doctor = curs.fetchone()
        if doctor is None:
            return None
        # Active sessions where doctor is either doctor1 or doctor2
        curs.execute("""
            SELECT
                cs.session_id,
                cs.created_at,
                p.name AS patient_name,
                p.date_of_birth,
                p.gender,
                p.avatarId AS patient_avatar
            FROM consultation_sessions cs
            JOIN patients p
                ON cs.health_id = p.health_id
            WHERE 
                (cs.assigned_doctor_id = ?
                OR cs.referred_doctor_id = ?)
                AND cs.session_status IN ('active', 'inReferral')
            ORDER BY cs.created_at DESC
        """, (doctorId, doctorId))
        rows = curs.fetchall()
        currentSessions = []
        for row in rows:
            dob = datetime.strptime(
                row["date_of_birth"],
                "%Y-%m-%d"
            ).date()
            today = date.today()
            age = (
                today.year
                - dob.year
                - (
                    (today.month, today.day)
                    <
                    (dob.month, dob.day)
                )
            )
            start = datetime.fromisoformat(
                row["created_at"]
            )
            currentSessions.append({
                "sessionId": row["session_id"],
                "patientName": row["patient_name"],
                "patientAge": age,
                "patientGender": row["gender"],
                "avatarId": row["patient_avatar"],
                "sessionStartDate":
                    start.strftime("%b %d, %Y"),
                "sessionStartTime":
                    start.strftime("%I:%M %p")
            })
        return {
            "doctorName": doctor["name"],
            "avatar": doctor["avatarId"],
            "currentSessions": currentSessions
        }
    except Exception:
        logger.exception("Error while fetching doctor home data")
        raise
    finally:
        if conn:
            conn.close()
def getSessionMessages(session_id: int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()

        curs.execute("""
            SELECT
                sm.message_id,
                sm.sender_id,
                sm.message,
                sm.created_at,
                sa.file_name,
                sa.file_path,
                sa.content_type,
                CASE
                    WHEN sm.sender_id = cs.health_id THEN p.name
                    WHEN sm.sender_id = cs.assigned_doctor_id THEN d1.name
                    WHEN sm.sender_id = cs.reffered_doctor_id THEN d2.name
                END AS sender_name,
                CASE
                    WHEN sm.sender_id = cs.health_id THEN p.avatar_id
                    WHEN sm.sender_id = cs.assigned_doctor_id THEN d1.avatar_id
                    WHEN sm.sender_id = cs.reffered_doctor_id THEN d2.avatar_id
                END AS sender_avatar,
                CASE
                    WHEN sm.sender_id = cs.health_id THEN 'patient'
                    WHEN sm.sender_id = cs.assigned_doctor_id THEN 'doctor'
                    WHEN sm.sender_id = cs.reffered_doctor_id THEN 'doctor'
                END AS sender_role
            FROM session_messages sm
            JOIN consultation_sessions cs
            ON sm.session_id = cs.session_id
            JOIN patients p
            ON cs.health_id = p.health_id
            JOIN doctors d1
            ON cs.assigned_doctor_id = d1.doctor_id
            LEFT JOIN doctors d2
            ON cs.reffered_doctor_id = d2.doctor_id
            LEFT JOIN session_attachments sa
            ON sm.message_id = sa.message_id
            WHERE sm.session_id = ? 
            AND cs.session_status IN ("active", "isReferral")
            ORDER BY sm.created_at ASC
        """, (session_id,))
        messages = curs.fetchall()
        return messages
    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception(f"Error fetching session messages: {e}")
        return None
    finally:
        if conn:
            conn.close()       
#still have this to complete but almost completed
def getDoctorDashboardData(doctorId):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        conn.row_factory = sqlite3.Row
        curs = conn.cursor()
        curs.execute("""
            SELECT
                d.doctor_id,
                d.name,
                d.contact_number,
                d.specialization,
                d.avatarId,
                d.total_cases_solved,
                c.clinic_id,
                c.name AS clinic_name,
                c.type,
                c.scale,
                c.speciality_stream,
                c.address,
                c.latitude,
                c.longitude,
                c.emergency_hotline
            FROM doctors d
            JOIN clinics c
                ON d.assigned_clinic_id = c.clinic_id
            WHERE d.doctor_id = ?
        """, (doctorId,))
        result = curs.fetchone()
        if result is None:
            return None
        return {
            "doctorId": result["doctor_id"],
            "doctorName": result["name"],
            "contactNumber": result["contact_number"],
            "specialization": result["specialization"],
            "avatarId": result["avatarId"],
            "totalCasesSolved": result["total_cases_solved"],
            "clinic": {
                "clinicId": result["clinic_id"],
                "clinicName": result["clinic_name"],
                "type": result["type"],
                "scale": result["scale"],
                "specialityStream": result["speciality_stream"],
                "address": result["address"],
                "latitude": result["latitude"],
                "longitude": result["longitude"],
                "emergencyHotline": result["emergency_hotline"]
            }
        }
    except Exception:
        logger.exception("Error while fetching doctor dashboard details")
        raise
    finally:
        if conn:
            conn.close()

#even this still have to do 
def getPatientSessions(patientId):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        # Patient details
        curs.execute("""
            SELECT
                name,
                avatarId
            FROM patients
            WHERE health_id = ?
        """, (patientId,))
        patient = curs.fetchone()
        if patient is None:
            return None
        # Patient sessions
        curs.execute("""
            SELECT
                cs.session_id,
                cs.created_at,
                d.name,
                d.specialization,
                d.avatarId
            FROM consultation_sessions cs
            JOIN doctors d
                ON cs.assigned_doctor_id = d.doctor_id
            WHERE cs.health_id = ?
              AND cs.session_status IN ('active', 'inReferral')
            ORDER BY cs.created_at DESC
        """, (patientId,))
        rows = curs.fetchall()
        currentSessions = []
        for row in rows:
            start = datetime.fromisoformat(row[1])
            currentSessions.append({
                "sessionId": row[0],
                "doctorName": row[2],
                "doctorSpeciality": row[3],
                "avatarId": row[4],
                "sessionStartDate": start.strftime("%b %d, %Y"),
                "sessionStartTime": start.strftime("%I:%M %p")
            })
        return {
            "patientName": patient[0],
            "avatar": patient[1],
            "currentSessions": currentSessions
        }
    except Exception:
        logger.exception("Error while fetching patient sessions")
        raise
    finally:
        if conn:
            conn.close()

# dont forget to give here for the below function the content type newly updated
def makeSession(doctorid:int, patientId:int, department:str, clinicid:int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        clinicid = int(clinicid)
        patientId = int(patientId)  
        doctorid = int(doctorid)
        curs.execute("""
                    INSERT INTO consultation_sessions
                    (health_id, clinic_id, assigned_doctor_id, department, session_status)
                    VALUES
                    (?,?,?,?,"active")
                        """, (patientId, clinicid, doctorid, department))
        conn.commit()
        newsession_id = curs.lastrowid
        return{
            "sessionId" : newsession_id,
            "message" : "Session created successfully"
        }
    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Error while creating consultation session")
        raise 
    finally:
        if conn:
            conn.close()
def getSessionDetails(sessionId: int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()

        curs.execute("""
            SELECT
                p.name,
                d.name,
                cs.created_at,
                c.name
            FROM consultation_sessions cs
            JOIN patients p
                ON cs.health_id = p.health_id
            JOIN doctors d
                ON cs.assigned_doctor_id = d.doctor_id
            JOIN clinics c
                ON cs.clinic_id = c.clinic_id
            WHERE cs.session_id = ?
        """, (sessionId,))

        result = curs.fetchone()

        if result is None:
            return None

        return {
            "patientName": result[0],
            "doctor1Name": result[1],
            "createdAt": result[2],
            "clinicName": result[3]
        }

    except Exception as e:
        logger.exception("Error while fetching session details")
        raise

    finally:
        if conn:
            conn.close()
def getReadCount(messageId: int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()

        curs.execute("""
            SELECT COUNT(*)
            FROM message_reads
            WHERE message_id = ?
        """, (messageId,))

        return curs.fetchone()[0]

    except Exception as e:
        logger.exception("Error while getting read count")
        raise

    finally:
        if conn:
            conn.close()
def getAttachmentDetails(userId: int, attachmentId: int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()

        curs.execute("""
            SELECT
                sa.file_name,
                sa.file_path
            FROM session_attachments sa
            JOIN session_messages sm
                ON sa.message_id = sm.message_id
            JOIN consultation_sessions cs
                ON sm.session_id = cs.session_id
            WHERE sa.attachment_id = ?
              AND (
                    cs.health_id = ?
                 OR cs.assigned_doctor_id = ?
                 OR cs.referred_doctor_id = ?
              )
        """, (attachmentId, userId, userId, userId))

        result = curs.fetchone()

        if result is None:
            return None

        return {
            "fileName": result[0],
            "filePath": result[1]
        }

    except Exception as e:
        logger.exception("Error while fetching attachment details")
        raise

    finally:
        if conn:
            conn.close()
def getReport(sessionId: int, userId: int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        curs.execute("""
            SELECT
                uploaded_file_path,
                content_type
            FROM consultation_sessions
            WHERE session_id = ?
              AND health_id = ?
              AND session_status = 'completed'
        """, (sessionId, userId))
        result = curs.fetchone()
        if result is None:
            return None
        return {
            "reportPath": result[0],
            "content_type": result[1]
        }
    except Exception:
        logger.exception("Error while fetching report details")
        raise

    finally:
        if conn:
            conn.close()
def updateNotes(sessionId: int, userId: int, notes: str):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()

        curs.execute("""
            UPDATE consultation_sessions
            SET notes = ?
            WHERE session_id = ?
              AND health_id = ?
              AND session_status in ('active', 'inReferral')
        """, (notes, sessionId, userId))

        conn.commit()

        return curs.rowcount > 0

    except Exception:
        if conn:
            conn.rollback()
        logger.exception("Error while updating session notes")
        raise

    finally:
        if conn:
            conn.close()
def checkSessionId(sessionId: int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        curs.execute("""
            SELECT
                assigned_doctor_id,
                referred_doctor_id
            FROM consultation_sessions
            WHERE session_id = ?
        """, (sessionId,))
        result = curs.fetchone()
        if result is None:  #this because other wise dictornay is not said to be none
            return None
        return {
            "doctor1Id": result[0],
            "doctor2Id": result[1]
        }
    except Exception as e:
        logger.exception("Error while checking session ID")
        raise
    finally:
        if conn:
            conn.close()
#dont use None things first 
def complete_patient_session(
    session_id: int,
    doctor_id: int,
    chief_complaint: str,
    additional_vitals: str,
    uploaded_filepath: str,
    content_type: str,
    resolved_time: str,
    blood_pressure: str = None,
    blood_sugar: float = None,
    temperature: float = None,
    heart_rate: int = None
):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        # Complete session
        curs.execute("""
            UPDATE consultation_sessions
            SET
                chief_complaint = ?,
                additional_vitals = ?,
                uploaded_file_path = ?,
                content_type = ?,
                blood_pressure = ?,
                blood_sugar = ?,
                temperature = ?,
                heart_rate = ?,
                session_status = 'completed',
                resolved_at = ?
            WHERE session_id = ?
        """,
        (
            chief_complaint,
            additional_vitals,
            uploaded_filepath,
            content_type,
            blood_pressure,
            blood_sugar,
            temperature,
            heart_rate,
            resolved_time,
            session_id
        ))
        if curs.rowcount == 0:
            return None
        # Increase doctor's solved cases
        #see how we can make functions there itself
        curs.execute("""
            UPDATE doctors
            SET total_cases_solved = total_cases_solved + 1  
            WHERE doctor_id = ?
        """, (doctor_id,))
        conn.commit()
        return {
            "message": "Session completed successfully"
        }
    except Exception:
        if conn:
            conn.rollback()
        logger.exception("Error while completing session")
        raise
    finally:
        if conn:
            conn.close()
    

def caluculate_distance(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return float('inf')
    a1 = math.radians(lat1)
    b1 = math.radians(lon1)
    a2 = math.radians(lat2)
    b2 = math.radians(lon2)
    diff1 = a1 - a2
    diff2 = b1 - b2
    a = (math.sin(diff1/2))**2
    b = math.cos(a1)*math.cos(a2)*(math.sin(diff2/2))**2
    return 2*6371*(math.asin(math.sqrt(a+b)))
def getEmergencyDoctors(session_id: int, emergency_time):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        curs.execute("""
            SELECT d.doctor_id
            FROM doctors AS d
            JOIN clinics AS c
            ON d.assigned_clinic_id = c.clinic_id
            JOIN consultation_sessions AS cs
            ON cs.session_id = ?
            JOIN clinics AS patient_clinic
            ON cs.clinic_id = patient_clinic.clinic_id
            WHERE d.is_available = 1
            AND d.specialization = cs.department
            AND c.clinic_type IN (
                'Corporate_Multi_Specialty',
                'Single_Specialty_Hospital'
            )
            AND
            (
                (
                    datetime('now') < datetime(?, '+30 minutes')
                    AND
                    calculate_distance(
                        patient_clinic.longitude,
                        patient_clinic.latitude,
                        c.longitude,
                        c.latitude
                    ) <= 100
                )
                OR
                (
                    datetime('now') >= datetime(?, '+30 minutes')
                )
            )
        """, (
            session_id,
            emergency_time,
            emergency_time
        ))
        doctors = curs.fetchall()
        return doctors
    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception(f"Error fetching emergency doctors: {e}")
        return None
    finally:
        if conn:
            conn.close()

def getSessionDetailsToConnect(sessionId: int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()

        curs.execute("""
            SELECT
                cs.assigned_doctor_id,
                p.name,
                c.name,
                cs.department,
                cs.created_at
            FROM consultation_sessions cs
            JOIN patients p
                ON cs.health_id = p.health_id
            JOIN clinics c
                ON cs.clinic_id = c.clinic_id
            WHERE cs.session_id = ?
              AND cs.is_referred = 0
        """, (sessionId,))

        result = curs.fetchone()

        if result is None:
            return None

        return {
            "doctorId": result[0],
            "patientName": result[1],
            "clinicName": result[2],
            "department": result[3],
            "timestamp": result[4]
        }

    except Exception:
        logger.exception("Error while fetching session details for emergency")
        raise

    finally:
        if conn:
            conn.close()

def checkSessionEmergency(sessionId: int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()

        curs.execute("""
            SELECT is_referred
            FROM consultation_sessions
            WHERE session_id = ?
              AND is_referred = 1
        """, (sessionId,))

        result = curs.fetchone()

        return result

    except Exception:
        logger.exception("Error while checking session emergency status")
        raise

    finally:
        if conn:
            conn.close()
