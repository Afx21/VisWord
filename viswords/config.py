import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'viswords-secret-key-2025'
    
    # 豆包API配置
    ARK_API_KEY = os.environ.get('ARK_API_KEY') or "您的豆包API密钥"
    DOUBAO_API_URL = "https://ark.cn-beijing.volces.com/api/v3"
    DOUBAO_MODEL = "doubao-seed-1-6-lite-251015"
    
    # 数据库配置
    DATABASE = 'viswords.db'
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    
    @staticmethod
    def init_app(app):
        pass