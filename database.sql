-- patients table
CREATE TABLE patients (
    health_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(20) NOT NULL CHECK (gender IN ('male', 'female', 'other')),
    blood_group VARCHAR(10) CHECK (blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    height REAL, -- Stored in cm
    weight REAL, -- Stored in kg
    eye_sight VARCHAR(150), 
    hearing VARCHAR(150),   
    medical_history TEXT,  
    allergies TEXT,        
    emergency_contact VARCHAR(150),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- CREATE INDEX idx_patients_health_id ON patients(health_id);

--local clinics table
CREATE TABLE clinics (
    clinic_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(150) NOT NULL,
    location VARCHAR(150) NOT NULL,
    latitude REAL NOT NULL,          -- GPS Latitude (e.g., 16.5062)
    longitude REAL NOT NULL,         -- GPS Longitude (e.g., 80.6480)
    clinic_type VARCHAR(100) NOT NULL DEFAULT 'PHC_CHC'
        CHECK (clinic_type IN (
            'PHC_CHC', 
            'Govt_General_Hospital', 
            'Corporate_Multi_Specialty', 
            'Single_Specialty_Hospital', 
            'Private_Clinic'
        )),
        
    facility_scale VARCHAR(50) NOT NULL DEFAULT 'Rural Spoke'
        CHECK (facility_scale IN ('Rural Spoke', 'Urban Node', 'Major Hub')),
        
    specialty_stream VARCHAR(50) DEFAULT NULL
        CHECK (specialty_stream IN (
            'General_Medicine', 'Ophthalmology', 'Otolaryngology', 'Cardiology',
            'Orthopedics', 'Neurology', 'Gastroenterology', 'Dermatology',
            'OB-GYN', 'Pediatrics', 'Psychiatry', 'Urology'
        )),
    contact_number VARCHAR(15)
);
CREATE INDEX idx_clinics_type ON clinics(clinic_type);
CREATE INDEX idx_clinics_scale ON clinics(facility_scale);

--doctor table
 CREATE TABLE doctors (
    doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    specialization VARCHAR(100) CHECK (specialization in ('General_Medicine', 'Ophthalmology', 'Otolaryngology', 'Cardiology',
            'Orthopedics', 'Neurology', 'Gastroenterology', 'Dermatology',
            'OB-GYN', 'Pediatrics', 'Psychiatry', 'Urology')), 
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
    blood_pressure VARCHAR(20), 
    blood_sugar REAL,           
    temperature REAL,           
    heart_rate INTEGER,  
    department VARCHAR(50) CHECK (department in (
        'General_Medicine',   -- 1. General & Common Illnesses
        'Ophthalmology',      -- 2. Eyes & Vision
        'Otolaryngology',     -- 3. Ear, Nose, & Throat (ENT)
        'Cardiology',         -- 4. Heart & Blood Pressure
        'Orthopedics',        -- 5. Bones, Joints, & Muscles
        'Neurology',          -- 6. Brain & Nerves
        'Gastroenterology',   -- 7. Stomach & Digestion
        'Dermatology',        -- 8. Skin, Hair, & Nails
        'OB-GYN',             -- 9. Women's Health & Pregnancy
        'Pediatrics',         -- 10. Kids & Infants
        'Psychiatry',         -- 11. Mental Health & Wellness
        'Urology'             -- 12. Urinary & Men's Health
    )),       
    chief_complaint TEXT NOT NULL,       
    -- uploaded_report_path VARCHAR(255), 
    additional_vitals TEXT DEFAULT '{}', 
    session_status VARCHAR(20) DEFAULT 'started',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    referred_hospital_id INTEGER DEFAULT NULL,
    referred_doctor_id INTEGER DEFAULT NULL,
    FOREIGN KEY (referred_hospital_id) REFERENCES clinics(clinic_id),
    FOREIGN KEY (health_id) REFERENCES patients(health_id),
    FOREIGN KEY (clinic_id) REFERENCES clinics(clinic_id),
    FOREIGN KEY (assigned_doctor_id) REFERENCES doctors(doctor_id),
    FOREIGN KEY (referred_doctor_id) REFERENCES doctors(doctor_id)
);
CREATE INDEX idx_sessions_status ON consultation_sessions(session_status);

CREATE TABLE session_attachments (
    attachment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    uploaded_by VARCHAR(50) NOT NULL CHECK (uploaded_by IN ('local_clinic', 'major_hospital')),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES consultation_sessions(session_id)
);

CREATE INDEX idx_attachment_session ON session_attachments(session_id);

CREATE TABLE session_messages(
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    uploaded_by VARCHAR(50) NOT NULL CHECK (uploaded_by IN ('local_clinic', 'major_hospital')),
    message TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES consultation_sessions(session_id)
);

CREATE INDEX idx_message_session ON session_messages(session_id);
