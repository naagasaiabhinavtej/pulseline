import sqlite3
from typing import Optional
import math
# import datetime

database_path = "medical_platform.db"

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

        