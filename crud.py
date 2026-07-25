import sqlite3
from typing import Optional
import math
import logging
from datetime import datetime

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
                            """, messageId)
        timeStamp = curs.fetchone()
        timeStamp = datetime.fromisoformat(timeStamp).strftime("%I:%M %p")
        return {
            "messageId":messageId,
            "attachmentId":attachmentId,
            "timeStamp":timeStamp
        }
    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Error while adding the message into the database")
        raise e
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


#you have to still update the down code      
def getPreviousSessions(patientId):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Check patient exists
    cursor.execute("""
        SELECT name, avatar_id
        FROM patients
        WHERE patient_id = ?
    """, (patientId,))

    patient = cursor.fetchone()

    if patient is None:
        conn.close()
        return None

    # Fetch previous sessions here...
    # ...

    conn.close()

    return {
        "patientName": patient[0],
        "avatarId": patient[1],
        "previousSessions": previousSessions
    }
#still there and also this is incorrect too as i dint give the doctor2 detials 
def getReportSubmissionData(sessionId, doctorId):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            s.session_id,
            s.start_time,

            d.doctor_id,
            d.name AS doctor_name,

            p.name AS patient_name,
            p.gender,
            p.date_of_birth,
            p.avatar_id

        FROM sessions s

        JOIN doctors d
            ON s.doctor_id = d.doctor_id

        JOIN patients p
            ON s.patient_id = p.patient_id

        WHERE
            s.session_id = ?
            AND s.doctor_id = ?
            AND s.status = 'Active'
    """, (sessionId, doctorId))

    row = cursor.fetchone()

    conn.close()

    if row is None:
        return None

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

    start = datetime.fromisoformat(row["start_time"])

    return {
        "doctorName": row["doctor_name"],

        "patientName": row["patient_name"],

        "patientAvatar": row["avatar_id"],

        "age": age,

        "gender": row["gender"],

        "ageGender": f"{age} / {row['gender']}",

        "startDate": start.strftime("%Y-%m-%d"),

        "startTime": start.strftime("%H:%M:%S")
    }
#still have this to complete but almost completed
def getDoctorHomeData(doctorId):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Doctor information
    cursor.execute("""
        SELECT
            name,
            avatar_id
        FROM doctors
        WHERE doctor_id = ?
    """, (doctorId,))

    doctor = cursor.fetchone()

    if doctor is None:
        conn.close()
        return None

    # Active sessions
    cursor.execute("""
        SELECT
            s.session_id,
            s.start_time,

            p.name,
            p.date_of_birth,
            p.gender,
            p.avatar_id

        FROM sessions s
        JOIN patients p
            ON s.patient_id = p.patient_id

        WHERE s.doctor_id = ?
        AND s.status = 'Active'

        ORDER BY s.start_time DESC
    """, (doctorId,))

    rows = cursor.fetchall()

    currentSessions = []

    for row in rows:

        dob = datetime.strptime(row["date_of_birth"], "%Y-%m-%d").date()

        today = date.today()

        age = (
            today.year
            - dob.year
            - (
                (today.month, today.day)
                < (dob.month, dob.day)
            )
        )

        start = datetime.fromisoformat(row["start_time"])

        currentSessions.append({
            "sessionId": row["session_id"],
            "patientName": row["name"],
            "patientAge": age,
            "patientGender": row["gender"],
            "avatarId": row["avatar_id"],
            "sessionStartdate": start.strftime("%b %d, %Y"),
            "sessionStarttime": start.strftime("%I:%M %p")
        })

    conn.close()

    return {
        "doctorName": doctor["name"],
        "avatar": doctor["avatar_id"],
        "currentSessions": currentSessions
    }
#still have this to complete but almost completed
def getDoctorDashboardData(doctorId):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            d.doctor_id,
            d.name,
            d.contact_number,
            d.specialization,
            d.avatar_id,
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
            ON d.clinic_id = c.clinic_id
        WHERE d.doctor_id = ?
    """, (doctorId,))

    row = cursor.fetchone()

    conn.close()

    if row is None:
        return None

    return {
        "doctorId": row["doctor_id"],
        "doctorName": row["name"],
        "contactNumber": row["contact_number"],
        "specialization": row["specialization"],
        "avatarId": row["avatar_id"],
        "totalCasesSolved": row["total_cases_solved"],

        "clinic": {
            "id": row["clinic_id"],
            "name": row["clinic_name"],
            "type": row["type"],
            "scale": row["scale"],
            "specialityStream": row["speciality_stream"],
            "address": row["address"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "emergencyHotline": row["emergency_hotline"]
        }
    }

#even this still have to do 
def getPatientSessions(patientId):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # patient information
    cur.execute("""
        SELECT patient_name,
               avatar_id
        FROM patients
        WHERE patient_id = ?
    """, (patientId,))

    patient = cur.fetchone()

    if patient is None:
        conn.close()
        return None
    sessions = []

    for row in cur.fetchall():

        dt = datetime.fromisoformat(row["start_time"])

        sessions.append({
            "sessionId": row["session_id"],
            "doctorName": row["doctor_name"],
            "doctorSpeciality": row["speciality"],
            "avatarId": row["avatar_id"],
            "sessionStartdate": dt.strftime("%b %d, %Y"),
            "sessionStarttime": dt.strftime("%I:%M %p")
        })

    conn.close()

    return {
        "patientName": patient["patient_name"],
        "avatar": patient["avatar_id"],
        "currentSessions": sessions
    }

# dont forget to give here for the below function the content type newly updated
def create_patient_session(health_id:str, clinic_id:str, department:str, assigned_doctor_id:str):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        clinic_id = int(clinic_id)
        assigned_doctor_id = int(assigned_doctor_id)
        curs.execute("""
                        SELECT name from patients
                        WHERE health_id = ?  
                        """, (health_id,))
        patient_row = curs.fetchone()
        patient_name = patient_row[0] if patient_row else "unknown Patient"
        
        curs.execute("SELECT name FROM clinics WHERE clinic_id = ?", (clinic_id,))
        clinic_row = curs.fetchone()
        clinic_name = clinic_row[0] if clinic_row else "Unknown Clinic"

        curs.execute("""
                    SELECT name FROM doctors
                    WHERE assigned_clinic_id = ? 
                      AND specialization = ? 
                      AND doctor_id = ? 
                      AND is_available = 1
                    """, (clinic_id, department, assigned_doctor_id))
        doctor_row = curs.fetchone()
        doctor_name = doctor_row[0] if doctor_row else "unknown Doctor"

        curs.execute("""
                    INSERT INTO consultation_sessions
                    (health_id, clinic_id, assigned_doctor_id, department, session_status)
                    VALUES
                    (?,?,?,?,"started")
                        """, (health_id, clinic_id, assigned_doctor_id, department))
        conn.commit()
        newsession_id = curs.lastrowid
        return{
            "session_id" : newsession_id,
            "patient_name" : patient_name,
            "clinic_name" : clinic_name,
            "doctor_name" : doctor_name,
            "message" : "Session created successfully"
        }
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()
def getDoctorDashboardData(doctorId):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            d.doctor_id,
            d.name,
            d.contact_number,
            d.specialization,
            d.avatar_id,
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
            ON d.clinic_id = c.clinic_id
        WHERE d.doctor_id = ?
    """, (doctorId,))

    row = cursor.fetchone()

    conn.close()

    if row is None:
        return None

    return {
        "doctorId": row["doctor_id"],
        "doctorName": row["name"],
        "contactNumber": row["contact_number"],
        "specialization": row["specialization"],
        "avatarId": row["avatar_id"],
        "totalCasesSolved": row["total_cases_solved"],

        "clinic": {
            "id": row["clinic_id"],
            "name": row["clinic_name"],
            "type": row["type"],
            "scale": row["scale"],
            "specialityStream": row["speciality_stream"],
            "address": row["address"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "emergencyHotline": row["emergency_hotline"]
        }
    }
#dont use None things first 
def complete_patient_session( 
    session_id:int,
    chief_complaint: str,
    additional_vitals: str,
    uploaded_filepath: str,
    resolved_time:str,
    blood_pressure: Optional[str] = None,
    blood_sugar: Optional[float] = None,
    temperature: Optional[float] = None,
    heart_rate: Optional[int] = None):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        curs.execute("""
                        UPDATE consultation_sessions
                        SET chief_complaint = ?, additional_vitals = ?, uploaded_file_path = ?, blood_pressure = ?, blood_sugar = ?, temperature = ?, heart_rate = ?, session_status = 'completed', resolved_at = ?
                        WHERE session_id = ?   
                    """, (chief_complaint, additional_vitals, uploaded_filepath, blood_pressure, blood_sugar, temperature, heart_rate, resolved_time, session_id))
        
        conn.commit()
        return{
            "message":"session completed successfully"
        }
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
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
    
def emergency_connect_hospitals(session_id:int, clinic_id:int, department:int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        # Arguments: (Name inside SQL, number of inputs, Python function name)
        conn.create_function("calculate_distance", 4, caluculate_distance)
        available = []
        curs.execute("""
                        SELECT a.clinic_id, b.doctor_id
                        FROM clinics as a
                        LEFT JOIN doctors as b
                        ON a.clinic_id = b.assigned_clinic_id
                        WHERE a.clinic_type IN ('Corporate_Multi_Specialty', 
                        'Single_Specialty_Hospital' 
                        ) AND a.specialty_stream = ? AND b.specialization = ?
                        AND b.is_available = True
                        AND (
                                ((SELECT created_at FROM consultation_sessions WHERE session_id = ?)>=datetime('now','-30 minutes')
                                AND calculate_distance(
                                                        (SELECT latitude FROM consultation_sessions WHERE session_id = ?),
                                                        (SELECT lONGItude FROM consultation_sessions WHERE session_id = ?),
                                                        a.latitude,
                                                        a.longitude
                                                    ) <= 50
                                OR
                                ( (SELECT created_at FROM consultation_sessions WHERE session_id = ?)<datetime('now','-30 minutes') )
                            )
                        """, department,department, session_id, session_id, session_id, session_id)
        conn.commit()
        rows = curs.fetchall() 
        for row in rows:
            available.append({
                "assigned_clinic_id":row[0],
                "assigned_doctor_id":row[1]
            })
        return available
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def make_available_doctor(doctor_id:int):
    conn = None
    try:
        conn = sqlite3.connect(database_path)
        curs = conn.cursor()
        curs.execute("""
                        UPDATE doctors
                        SET is_available = not is_available
                        WHERE doctor_id = ? AND is_available = True
                        """, (doctor_id,))
        conn.commit()
        return {"message":"success"}
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

















def trigger_emergency_escalation(session_id: int):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""
                        UPDATE consultation_sessions
                        SET session_status = "emergency"
                        WHERE session_id = ?                        
                        """, (session_id,))
        conn.commit()
        cursor.execute("""
                        SELECT 
                            s.session_id,
                            p.name AS patient_name,
                            c.name AS clinic_name,
                            s.chief_complaint,
                            s.additional_vitals,
                            s.uploaded_report_path
                        FROM consultation_sessions s
                        LEFT JOIN patients p ON s.health_id = p.health_id
                        LEFT JOIN Clinics c ON s.clinic_id = c.clinic_id
                        WHERE s.session_id = ?
                        """, (session_id,))
        row = cursor.fetchone()
        if row:
            emergency_packet = {
                "session_id": row[0],
                "patient_name": row[1] if row[1] else "Unknown Patient",
                "clinic_name": row[2] if row[2] else "Unknown Clinic",
                "chief_complaint": row[3],
                "file_updates": row[4] if (row[4] and row[4] != '{}') else "No automated report data generated",
                "image_path": row[5] if row[5] else "No image uploaded"
            }
            return emergency_packet
        return None
    except Exception as e:
        print(f"Database error during escalation: {e}")
        raise e
    finally:
        conn.close()

        