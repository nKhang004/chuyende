from flask import Flask, render_template, request, jsonify, redirect, url_for, Response
import cv2
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from config import Config
from utils.database import Database
from utils.face_recognition import FaceRecognizer

app = Flask(__name__)
app.config.from_object(Config)
Config.init_app()

# Khởi tạo
db = Database()
face_recognizer = FaceRecognizer()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Trang chủ"""
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Đăng ký sinh viên mới"""
    if request.method == 'POST':
        # Lấy thông tin từ form
        student_id = request.form.get('student_id')
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        class_name = request.form.get('class')
        
        # Kiểm tra file ảnh
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'Không có file ảnh'})
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Chưa chọn file'})
        
        if file and allowed_file(file.filename):
            # Lưu file
            filename = secure_filename(f"{student_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg")
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            # Đăng ký khuôn mặt
            success, message = face_recognizer.register_face(filepath, student_id)
            
            if success:
                # Thêm vào database
                db_success, db_message = db.add_student(
                    student_id, name, email, phone, class_name, filename
                )
                
                if db_success:
                    return jsonify({'success': True, 'message': 'Đăng ký sinh viên thành công'})
                else:
                    # Xóa encoding nếu thêm vào DB thất bại
                    face_recognizer.delete_face_encoding(student_id)
                    os.remove(filepath)
                    return jsonify({'success': False, 'message': db_message})
            else:
                os.remove(filepath)
                return jsonify({'success': False, 'message': message})
        
        return jsonify({'success': False, 'message': 'File không hợp lệ'})
    
    return render_template('register.html')

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    """Điểm danh bằng upload ảnh"""
    if request.method == 'POST':
        if 'image' not in request.files:
            return jsonify({'success': False, 'message': 'Không có file ảnh'})
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Chưa chọn file'})
        
        if file and allowed_file(file.filename):
            # Lưu file tạm
            filename = secure_filename(f"attendance_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg")
            filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
            file.save(filepath)
            
            # Nhận diện khuôn mặt
            recognized, message = face_recognizer.recognize_face(filepath)
            
            if recognized:
                results = []
                for student_info in recognized:
                    student_id = student_info['student_id']
                    confidence = student_info['confidence']
                    
                    # Lấy thông tin sinh viên
                    student = db.get_student(student_id)
                    
                    if student:
                        # Kiểm tra độ tin cậy
                        if confidence < 0.70:
                            warning = " (Độ tin cậy thấp - Cần xác nhận)"
                        else:
                            warning = ""
                        
                        # Điểm danh
                        success, att_message = db.mark_attendance(student_id, filename)
                        results.append({
                            'student_id': student_id,
                            'name': student['name'],
                            'confidence': f"{confidence:.2%}",
                            'status': 'success' if success else 'already_marked',
                            'message': att_message + warning,
                            'confidence_level': 'high' if confidence >= 0.70 else 'low'
                        })
                
                return jsonify({'success': True, 'students': results})
            else:
                os.remove(filepath)
                return jsonify({'success': False, 'message': message})
        
        return jsonify({'success': False, 'message': 'File không hợp lệ'})
    
    return render_template('attendance.html')

@app.route('/history')
def history():
    """Xem lịch sử điểm danh"""
    date = request.args.get('date')
    records = db.get_attendance_history(date)
    return render_template('history.html', records=records)

@app.route('/students')
def students():
    """Danh sách sinh viên"""
    all_students = db.get_all_students()
    return jsonify(all_students)

@app.route('/students/manage')
def manage_students():
    """Trang quản lý sinh viên"""
    all_students = db.get_all_students()
    return render_template('manage_students.html', students=all_students)

@app.route('/students/delete/<student_id>', methods=['POST'])
def delete_student(student_id):
    """Xóa sinh viên"""
    # Xóa khỏi database
    success, message = db.delete_student(student_id)
    
    if success:
        # Xóa face encoding
        face_recognizer.delete_face_encoding(student_id)
        
        # Xóa ảnh (tùy chọn)
        student = db.get_student(student_id)
        if student and student.get('image_path'):
            image_path = os.path.join(Config.UPLOAD_FOLDER, student['image_path'])
            if os.path.exists(image_path):
                os.remove(image_path)
        
        return jsonify({'success': True, 'message': message})
    
    return jsonify({'success': False, 'message': message})

# API cho webcam real-time
camera = None

def generate_frames():
    """Generator để stream video từ webcam"""
    global camera
    camera = cv2.VideoCapture(0)
    
    while True:
        success, frame = camera.read()
        if not success:
            break
        
        # Nhận diện khuôn mặt
        student_ids, face_locations = face_recognizer.recognize_face_from_frame(frame)
        
        # Vẽ khung và tên
        for (top, right, bottom, left), student_id in zip(face_locations, student_ids):
            # Vẽ khung
            color = (0, 255, 0) if student_id != "Unknown" else (0, 0, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            
            # Vẽ tên
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            cv2.putText(frame, student_id, (left + 6, bottom - 6), 
                       cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 255), 1)
        
        # Encode frame
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """Stream video"""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture_attendance', methods=['POST'])
def capture_attendance():
    """Điểm danh từ webcam"""
    global camera
    if camera is None or not camera.isOpened():
        return jsonify({'success': False, 'message': 'Camera chưa được khởi động'})
    
    # Chụp frame hiện tại
    success, frame = camera.read()
    if not success:
        return jsonify({'success': False, 'message': 'Không thể chụp ảnh'})
    
    # Lưu ảnh
    filename = f"webcam_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
    cv2.imwrite(filepath, frame)
    
    # Nhận diện
    recognized, message = face_recognizer.recognize_face(filepath)
    
    if recognized:
        results = []
        for student_info in recognized:
            student_id = student_info['student_id']
            student = db.get_student(student_id)
            
            if student:
                success, att_message = db.mark_attendance(student_id, filename)
                results.append({
                    'student_id': student_id,
                    'name': student['name'],
                    'status': 'success' if success else 'already_marked',
                    'message': att_message
                })
        
        return jsonify({'success': True, 'students': results})
    
    os.remove(filepath)
    return jsonify({'success': False, 'message': message})

@app.route('/stop_camera')
def stop_camera():
    """Dừng camera"""
    global camera
    if camera is not None:
        camera.release()
        camera = None
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)