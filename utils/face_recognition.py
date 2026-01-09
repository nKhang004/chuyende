import face_recognition
import cv2
import numpy as np
import pickle
import os
from config import Config

class FaceRecognizer:
    def __init__(self):
        self.known_face_encodings = []
        self.known_student_ids = []
        self.encodings_file = os.path.join(Config.MODELS_PATH, 'face_encodings.pkl')
        self.load_encodings()
    
    def load_encodings(self):
        """Load dữ liệu encoding đã lưu"""
        if os.path.exists(self.encodings_file):
            with open(self.encodings_file, 'rb') as f:
                data = pickle.load(f)
                self.known_face_encodings = data['encodings']
                self.known_student_ids = data['student_ids']
    
    def save_encodings(self):
        """Lưu dữ liệu encoding"""
        data = {
            'encodings': self.known_face_encodings,
            'student_ids': self.known_student_ids
        }
        with open(self.encodings_file, 'wb') as f:
            pickle.dump(data, f)
    
    def register_face(self, image_path, student_id):
        """Đăng ký khuôn mặt mới"""
        # Đọc ảnh
        image = face_recognition.load_image_file(image_path)
        
        # Tìm vị trí khuôn mặt
        face_locations = face_recognition.face_locations(image, model=Config.FACE_DETECTION_MODEL)
        
        if len(face_locations) == 0:
            return False, "Không tìm thấy khuôn mặt trong ảnh"
        
        if len(face_locations) > 1:
            return False, "Phát hiện nhiều hơn 1 khuôn mặt trong ảnh"
        
        # Tạo encoding
        face_encodings = face_recognition.face_encodings(image, face_locations)
        
        if len(face_encodings) > 0:
            face_encoding = face_encodings[0]
            
            # KIỂM TRA MÃ SV ĐÃ TỒN TẠI CHƯA (THAY VÌ KIỂM TRA KHUÔN MẶT)
            if student_id in self.known_student_ids:
                return False, f"Mã sinh viên {student_id} đã được đăng ký"
            
            # Thêm vào danh sách
            self.known_face_encodings.append(face_encoding)
            self.known_student_ids.append(student_id)
            self.save_encodings()
            
            return True, "Đăng ký khuôn mặt thành công"
        
        return False, "Không thể tạo encoding cho khuôn mặt"
    
    def recognize_face(self, image_path):
        """Nhận diện khuôn mặt từ ảnh"""
        if len(self.known_face_encodings) == 0:
            return None, "Chưa có dữ liệu khuôn mặt nào được đăng ký"
        
        # Đọc ảnh
        image = face_recognition.load_image_file(image_path)
        
        # Tìm khuôn mặt
        face_locations = face_recognition.face_locations(image, model=Config.FACE_DETECTION_MODEL)
        
        if len(face_locations) == 0:
            return None, "Không tìm thấy khuôn mặt trong ảnh"
        
        # Tạo encoding
        face_encodings = face_recognition.face_encodings(image, face_locations)
        
        recognized_students = []
        
        for face_encoding in face_encodings:
            # So sánh với database
            matches = face_recognition.compare_faces(
                self.known_face_encodings, 
                face_encoding,
                tolerance=Config.FACE_RECOGNITION_TOLERANCE
            )
            
            if True in matches:
                # Tìm khuôn mặt khớp nhất
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                best_match_idx = np.argmin(face_distances)
                
                if matches[best_match_idx]:
                    confidence = 1 - face_distances[best_match_idx]
                    
                    # THÊM KIỂM TRA: Chỉ chấp nhận nếu độ tin cậy >= 60%
                    if confidence >= 0.60:
                        student_id = self.known_student_ids[best_match_idx]
                        recognized_students.append({
                            'student_id': student_id,
                            'confidence': float(confidence)
                        })
        
        if recognized_students:
            return recognized_students, "Nhận diện thành công"
        
        return None, "Không nhận diện được khuôn mặt"
    
    def recognize_face_from_frame(self, frame):
        """Nhận diện khuôn mặt từ frame video (cho webcam)"""
        if len(self.known_face_encodings) == 0:
            return [], []
        
        # Resize frame để xử lý nhanh hơn
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Tìm khuôn mặt
        face_locations = face_recognition.face_locations(rgb_small_frame, model='hog')
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        
        student_ids = []
        face_locations_scaled = []
        
        for face_encoding, face_location in zip(face_encodings, face_locations):
            matches = face_recognition.compare_faces(
                self.known_face_encodings,
                face_encoding,
                tolerance=Config.FACE_RECOGNITION_TOLERANCE
            )
            
            student_id = "Unknown"
            
            if True in matches:
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                best_match_idx = np.argmin(face_distances)
                
                if matches[best_match_idx]:
                    student_id = self.known_student_ids[best_match_idx]
            
            student_ids.append(student_id)
            
            # Scale lại tọa độ về kích thước gốc
            top, right, bottom, left = face_location
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4
            face_locations_scaled.append((top, right, bottom, left))
        
        return student_ids, face_locations_scaled
    
    def delete_face_encoding(self, student_id):
        """Xóa encoding của sinh viên"""
        if student_id in self.known_student_ids:
            idx = self.known_student_ids.index(student_id)
            self.known_face_encodings.pop(idx)
            self.known_student_ids.pop(idx)
            self.save_encodings()
            return True
        return False