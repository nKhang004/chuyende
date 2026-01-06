import sqlite3
from datetime import datetime
from config import Config

class Database:
    def __init__(self):
        self.db_path = Config.DATABASE_PATH
        self.init_database()
    
    def get_connection(self):
        """Tạo kết nối đến database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Trả về dict thay vì tuple
        return conn
    
    def init_database(self):
        """Khởi tạo các bảng trong database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Bảng sinh viên
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                class TEXT,
                image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Bảng điểm danh
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                image_path TEXT,
                status TEXT DEFAULT 'present',
                FOREIGN KEY (student_id) REFERENCES students(student_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_student(self, student_id, name, email=None, phone=None, class_name=None, image_path=None):
        """Thêm sinh viên mới"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO students (student_id, name, email, phone, class, image_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (student_id, name, email, phone, class_name, image_path))
            conn.commit()
            return True, "Thêm sinh viên thành công"
        except sqlite3.IntegrityError:
            return False, "Mã sinh viên đã tồn tại"
        finally:
            conn.close()
    
    def get_student(self, student_id):
        """Lấy thông tin sinh viên"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM students WHERE student_id = ?', (student_id,))
        student = cursor.fetchone()
        conn.close()
        return dict(student) if student else None
    
    def get_all_students(self):
        """Lấy danh sách tất cả sinh viên"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM students ORDER BY name')
        students = cursor.fetchall()
        conn.close()
        return [dict(student) for student in students]
    
    def mark_attendance(self, student_id, image_path=None):
        """Điểm danh sinh viên"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Kiểm tra đã điểm danh hôm nay chưa
        today = datetime.now().date()
        cursor.execute('''
            SELECT * FROM attendance 
            WHERE student_id = ? AND DATE(check_in_time) = ?
        ''', (student_id, today))
        
        if cursor.fetchone():
            conn.close()
            return False, "Sinh viên đã điểm danh hôm nay"
        
        # Thêm điểm danh mới
        cursor.execute('''
            INSERT INTO attendance (student_id, image_path)
            VALUES (?, ?)
        ''', (student_id, image_path))
        conn.commit()
        conn.close()
        return True, "Điểm danh thành công"
    
    def get_attendance_history(self, date=None):
        """Lấy lịch sử điểm danh"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if date:
            cursor.execute('''
                SELECT a.*, s.name, s.class 
                FROM attendance a
                JOIN students s ON a.student_id = s.student_id
                WHERE DATE(a.check_in_time) = ?
                ORDER BY a.check_in_time DESC
            ''', (date,))
        else:
            cursor.execute('''
                SELECT a.*, s.name, s.class 
                FROM attendance a
                JOIN students s ON a.student_id = s.student_id
                ORDER BY a.check_in_time DESC
                LIMIT 100
            ''')
        
        records = cursor.fetchall()
        conn.close()
        return [dict(record) for record in records]