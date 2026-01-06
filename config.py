import os

class Config:
    # Cấu hình Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Đường dẫn thư mục
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'students.db')
    MODELS_PATH = os.path.join(BASE_DIR, 'models')
    
    # Cấu hình upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Cấu hình nhận diện khuôn mặt
    FACE_RECOGNITION_TOLERANCE = 0.6  # Độ chính xác (0.0 - 1.0, càng thấp càng nghiêm ngặt)
    FACE_DETECTION_MODEL = 'hog'  # 'hog' hoặc 'cnn' (cnn chính xác hơn nhưng chậm hơn)
    
    @staticmethod
    def init_app():
        """Khởi tạo các thư mục cần thiết"""
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
        os.makedirs(Config.MODELS_PATH, exist_ok=True)