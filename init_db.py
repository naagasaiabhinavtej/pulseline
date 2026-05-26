import sqlite3
import os
def init_db():
    sql_blueprint_path = "schema.sql"
    database_file_name = "medical_platform.db"
    if not os.path.exists(sql_blueprint_path):
        print(f"❌ Error: Could not find '{sql_blueprint_path}' in this folder.")
        print("Please create your 'schema.sql' file first before running this script.")
        return
    print(f"🏗️  Reading blueprint from {sql_blueprint_path}...")
    try:
        with open("schema.sql", "r") as sql_file:
            sql_script = sql_file.read()
        conn = sqlite3.connect(database_file_name)
        cursor = conn.cursor()
        cursor.executescript(sql_script)
        conn.commit()
        conn.close()   
        print(f"🎉 Success! '{database_file_name}' created perfectly with all 4 tables & indexes.")        
    except sqlite3.Error as e:
        print(f"❌ Database Initialization Failed due to SQL Error: {e}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")

if __name__ == "__main__":
    init_db()