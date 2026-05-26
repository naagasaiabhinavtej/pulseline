-- patients table
CREATE TABLE patients (
    health_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(20) NOT NULL,
    blood_group VARCHAR(10),
    height REAL, -- Stored in cm
    weight REAL, -- Stored in kg
    eye_sight VARCHAR(150), 
    hearing VARCHAR(150),   
    medical_history TEXT,  
    allergies TEXT,        
    emergency_contact VARCHAR(150)
);
CREATE INDEX idx_patients_health_id ON patients(health_id);

--local clinics table
CREATE TABLE clinics (
    clinic_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(150) NOT NULL,
    location VARCHAR(150) NOT NULL,
    clinic_type VARCHAR(100) NOT NULL DEFAULT 'General Medicine',
    facility_scale VARCHAR(50) NOT NULL DEFAULT 'Rural Spoke',
    contact_number VARCHAR(15),
);
CREATE INDEX idx_clinics_type ON clinics(clinic_type);
CREATE INDEX idx_clinics_scale ON clinics(facility_scale);

--doctor table
 CREATE TABLE doctors (
    doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    specialization VARCHAR(100) NOT NULL, 
    contact_number VARCHAR(15),
    is_available BOOLEAN DEFAULT 1, 
    assigned_clinic_id INTEGER,
    FOREIGN KEY (assigned_clinic_id) REFERENCES clinics(clinic_id)
);
CREATE INDEX idx_doctors_specialization ON doctors(specialization);

--the data of issue
CREATE TABLE consultation_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    health_id VARCHAR(50) NOT NULL,
    clinic_id INTEGER NOT NULL,          
    assigned_doctor_id INTEGER,          
    logged_nurse_name VARCHAR(100) NOT NULL,
    blood_pressure VARCHAR(20), 
    blood_sugar REAL,           
    temperature REAL,           
    heart_rate INTEGER,         
    chief_complaint TEXT NOT NULL,       
    uploaded_report_path VARCHAR(255), 
    additional_vitals TEXT DEFAULT '{}', 
    session_status VARCHAR(20) DEFAULT 'queued',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    FOREIGN KEY (health_id) REFERENCES patients(health_id),
    FOREIGN KEY (clinic_id) REFERENCES clinics(clinic_id),
    FOREIGN KEY (assigned_doctor_id) REFERENCES doctors(doctor_id)
);
CREATE INDEX idx_sessions_status ON consultation_sessions(session_status);


