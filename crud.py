import sqlite3
from typing import Optional
import datetime

database_path = "medical_platform.db"

def create_patient_session(health_id:str, clinic_id:str, department:str, assigned_doctor_id:str):
    conn = sqlite3.connect(database_path)
    curs = conn.cursor()
    timenow = datetime.now().isoformat()
    try:
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
                    (health_id, clinic_id, assigned_doctor_id, department, session_status, created_at)
                    VALUES
                    (?,?,?,?,"started",?)
                        """, (health_id, clinic_id, assigned_doctor_id, department, timenow))
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
        conn.rollback()
        raise e
    finally:
        conn.close()

    
def create_patient_sessio(health_id:str, clinic_id:str, logged_nurse_name: str, file_path:str, additional_vitals:Optional[str] = None, chief_complaint:Optional[str] = None):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    try:
        cursor.execute("""SELECT name from patients where health_id = ?
                            """, (health_id,))
        patient_row = cursor.fetchone()
        # print(f"--- SQLITE INDEX CHECK: {patient_row[3]} ---")
        health_name = patient_row[0] if patient_row else "Unknown Patient"

        cursor.execute("SELECT name FROM Clinics WHERE clinic_id = ?", (clinic_id,))
        clinic_row = cursor.fetchone()
        clinic_name = clinic_row[0] if clinic_row else "Unknown Clinic"

        cursor.execute("""
                        INSERT INTO consultation_sessions
                        (health_id, clinic_id, logged_nurse_name, uploaded_report_path, 
                        chief_complaint, additional_vitals, session_status)
                        VALUES
                        (?,?,?,?,?,?,'queued')
                        """,
                        (
                            health_id, clinic_id, logged_nurse_name, file_path, 
                            chief_complaint, additional_vitals
                        )                        
                        )
        conn.commit()
        new_session_id = cursor.lastrowid
        return {
            "session_id": new_session_id,
            "health_name": health_name,
            "clinic_name": clinic_name,
            "message": "Session successfully queued with bundled vitals!"
        }        
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

        