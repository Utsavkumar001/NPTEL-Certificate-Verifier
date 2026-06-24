"""
SQLite database layer.

Tables:
  students           - student accounts
  faculty            - faculty accounts (created by admin only)
  admins             - admin accounts
  course_requests    - student course requests + faculty approval
  certificates       - uploaded + verified certificate records
  used_certificates  - tracks which cert IDs have been claimed
"""

import sqlite3
from pathlib import Path
from app.config import BASE_DIR

DB_PATH = str(BASE_DIR / "data" / "nptel.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        roll        TEXT UNIQUE NOT NULL,
        class       TEXT NOT NULL,
        semester    TEXT NOT NULL,
        school      TEXT NOT NULL,
        department  TEXT NOT NULL,
        password    TEXT NOT NULL,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS faculty (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT NOT NULL,
        emp_id          TEXT UNIQUE NOT NULL,
        school          TEXT NOT NULL,
        department      TEXT NOT NULL,
        password        TEXT NOT NULL,
        requests_open   INTEGER DEFAULT 0,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS admins (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT UNIQUE NOT NULL,
        password    TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS course_requests (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id      INTEGER NOT NULL,
        course_name     TEXT NOT NULL,
        nptel_course_id TEXT NOT NULL,
        status          TEXT DEFAULT 'pending',
        faculty_remarks TEXT,
        approved_by     INTEGER,
        confirmed       INTEGER DEFAULT 0,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id)
    );

    CREATE TABLE IF NOT EXISTS certificates (
        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id              INTEGER NOT NULL,
        course_request_id       INTEGER NOT NULL,
        certificate_id          TEXT UNIQUE NOT NULL,
        course_name             TEXT,
        course_code             TEXT,
        credits                 INTEGER,
        weeks                   INTEGER,
        certificate_status      TEXT,
        credit_transfer_status  TEXT,
        rejection_reason        TEXT,
        credits_processed       INTEGER DEFAULT 0,
        uploaded_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id)
    );

    CREATE TABLE IF NOT EXISTS used_certificates (
        certificate_id  TEXT PRIMARY KEY,
        student_roll    TEXT NOT NULL,
        used_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    try:
        c.execute("ALTER TABLE faculty ADD COLUMN requests_open INTEGER DEFAULT 0")
        conn.commit()
    except Exception:
        pass

    from app.auth import hash_password
    existing = c.execute("SELECT id FROM admins WHERE username='admin'").fetchone()
    if not existing:
        c.execute(
            "INSERT INTO admins (username, password) VALUES (?, ?)",
            ("admin", hash_password("admin123")),
        )

    conn.commit()
    conn.close()


def create_student(name, roll, cls, semester, school, department, hashed_pw):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO students (name,roll,class,semester,school,department,password) VALUES (?,?,?,?,?,?,?)",
            (name, roll, cls, semester, school, department, hashed_pw),
        )
        conn.commit()
        return True, None
    except sqlite3.IntegrityError:
        return False, "Roll number already registered."
    finally:
        conn.close()


def get_student_by_roll(roll):
    conn = get_conn()
    row = conn.execute("SELECT * FROM students WHERE roll=?", (roll,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_student_by_id(sid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_faculty(name, emp_id, school, department, hashed_pw):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO faculty (name,emp_id,school,department,password) VALUES (?,?,?,?,?)",
            (name, emp_id, school, department, hashed_pw),
        )
        conn.commit()
        return True, None
    except sqlite3.IntegrityError:
        return False, "Employee ID already exists."
    finally:
        conn.close()


def get_faculty_by_empid(emp_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM faculty WHERE emp_id=?", (emp_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_faculty_by_id(fid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM faculty WHERE id=?", (fid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_faculty_by_department(department):
    conn = get_conn()
    row = conn.execute("SELECT * FROM faculty WHERE department=?", (department,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_faculty():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id,name,emp_id,school,department,requests_open,created_at FROM faculty ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_requests_open(faculty_id, value: int):
    conn = get_conn()
    conn.execute("UPDATE faculty SET requests_open=? WHERE id=?", (value, faculty_id))
    conn.commit()
    conn.close()


def get_admin_by_username(username):
    conn = get_conn()
    row = conn.execute("SELECT * FROM admins WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_course_request(student_id, course_name, nptel_course_id):
    conn = get_conn()
    conn.execute(
        "INSERT INTO course_requests (student_id,course_name,nptel_course_id) VALUES (?,?,?)",
        (student_id, course_name, nptel_course_id),
    )
    conn.commit()
    conn.close()


def get_all_requests_for_student(student_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM course_requests WHERE student_id=? ORDER BY created_at DESC",
        (student_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_request_by_id(request_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM course_requests WHERE id=?", (request_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_request_status(request_id, status, faculty_id, remarks=None):
    conn = get_conn()
    conn.execute(
        "UPDATE course_requests SET status=?, approved_by=?, faculty_remarks=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (status, faculty_id, remarks, request_id),
    )
    conn.commit()
    conn.close()


def confirm_request(request_id):
    conn = get_conn()
    conn.execute(
        "UPDATE course_requests SET confirmed=1, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (request_id,),
    )
    conn.commit()
    conn.close()


def get_certificate_by_request(course_request_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM certificates WHERE course_request_id=?",
        (course_request_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_faculty_department_students(department, semester=None):
    conn = get_conn()
    query = """
        SELECT
            s.id, s.name, s.roll, s.class, s.semester,
            cr.id AS req_id, cr.course_name, cr.nptel_course_id,
            cr.status AS req_status, cr.faculty_remarks, cr.confirmed,
            cert.id AS cert_id, cert.certificate_status,
            cert.credit_transfer_status, cert.credits, cert.credits_processed
        FROM students s
        LEFT JOIN course_requests cr ON cr.student_id = s.id
        LEFT JOIN certificates cert ON cert.course_request_id = cr.id
        WHERE s.department = ?
    """
    params = [department]
    if semester:
        query += " AND s.semester = ?"
        params.append(semester)
    query += " ORDER BY s.name, cr.created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_students_full(school=None, department=None, semester=None):
    conn = get_conn()
    query = """
        SELECT
            s.id, s.name, s.roll, s.class, s.semester, s.school, s.department,
            cr.id AS req_id, cr.course_name, cr.nptel_course_id,
            cr.status AS req_status, cr.confirmed,
            cert.id AS cert_id, cert.certificate_status,
            cert.credit_transfer_status, cert.credits, cert.credits_processed
        FROM students s
        LEFT JOIN course_requests cr ON cr.student_id = s.id
        LEFT JOIN certificates cert ON cert.course_request_id = cr.id
        WHERE 1=1
    """
    params = []
    if school:
        query += " AND s.school=?"
        params.append(school)
    if department:
        query += " AND s.department=?"
        params.append(department)
    if semester:
        query += " AND s.semester=?"
        params.append(semester)
    query += " ORDER BY s.school, s.department, s.name, cr.created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_certificate(student_id, course_request_id, certificate_id, course_name,
                     course_code, credits, weeks, cert_status, credit_status, rejection_reason):
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO certificates
                (student_id, course_request_id, certificate_id, course_name,
                 course_code, credits, weeks, certificate_status,
                 credit_transfer_status, rejection_reason)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (student_id, course_request_id, certificate_id, course_name,
               course_code, credits, weeks, cert_status, credit_status, rejection_reason))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_certificate_by_student(student_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM certificates WHERE student_id=? ORDER BY uploaded_at DESC LIMIT 1",
        (student_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_total_credits(student_id):
    conn = get_conn()
    row = conn.execute(
        """SELECT COALESCE(SUM(c.credits),0) as total 
           FROM certificates c 
           WHERE c.student_id=? 
           AND c.credit_transfer_status='ELIGIBLE' 
           AND c.credits_processed=1""",
        (student_id,)
    ).fetchone()
    conn.close()
    return row["total"] if row else 0


def mark_credits_processed(cert_id):
    conn = get_conn()
    conn.execute("UPDATE certificates SET credits_processed=1 WHERE id=?", (cert_id,))
    conn.commit()
    conn.close()


def is_cert_used(certificate_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT certificate_id FROM used_certificates WHERE certificate_id=?",
        (certificate_id,)
    ).fetchone()
    conn.close()
    return row is not None


def mark_cert_used(certificate_id, student_roll):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO used_certificates (certificate_id, student_roll) VALUES (?,?)",
            (certificate_id, student_roll)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()
        
def delete_faculty_by_id(faculty_id):
    conn = get_conn()
    conn.execute("DELETE FROM faculty WHERE id=?", (faculty_id,))
    conn.commit()
    conn.close()
    
def delete_certificate_by_request(course_request_id):
    conn = get_conn()
    # Also remove from used_certificates so student can reuse the same cert if needed
    row = conn.execute(
        "SELECT certificate_id FROM certificates WHERE course_request_id=?",
        (course_request_id,)
    ).fetchone()
    if row:
        conn.execute(
            "DELETE FROM used_certificates WHERE certificate_id=?",
            (row["certificate_id"],)
        )
    conn.execute(
        "DELETE FROM certificates WHERE course_request_id=?",
        (course_request_id,)
    )
    conn.commit()
    conn.close()
    
def update_student_semester(student_id, semester):
    conn = get_conn()
    conn.execute("UPDATE students SET semester=? WHERE id=?", (semester, student_id))
    conn.commit()
    conn.close()


def reset_user_password(user_type, user_id, hashed_pw):
    conn = get_conn()
    if user_type == "student":
        conn.execute("UPDATE students SET password=? WHERE id=?", (hashed_pw, user_id))
    elif user_type == "faculty":
        conn.execute("UPDATE faculty SET password=? WHERE id=?", (hashed_pw, user_id))
    elif user_type == "admin":
        conn.execute("UPDATE admins SET password=? WHERE id=?", (hashed_pw, user_id))
    conn.commit()
    conn.close()