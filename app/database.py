from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///faces.db"

# Khởi tạo engine và session với cơ sở dữ liệu SQLite
# connect_args={"check_same_thread": False} bắt buộc để uvicorn xử lý đa luồng an toàn với SQLite
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 1. Bảng lưu thông tin tài khoản đăng nhập quản trị
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

# 2. Bảng lưu khuôn mặt đã được đăng ký (tên và vector nhúng 128 chiều dạng text json)
class FaceRecord(Base):
    __tablename__ = "faces"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    embedding = Column(Text, nullable=False)
    created_at = Column(String, nullable=True)  # Ngày đăng ký
    created_by = Column(String, nullable=True)  # Người thực hiện đăng ký

# 3. Bảng lưu nhật ký sự kiện hệ thống (Xâm nhập, ngã, người lạ, số đếm)
class SystemEventLog(Base):
    __tablename__ = "system_events"
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, index=True, nullable=False)  # 'intrusion', 'fall', 'face', 'counter'
    message = Column(Text, nullable=False)
    camera_id = Column(String, index=True, nullable=False)
    image_path = Column(String, nullable=True)  # Đường dẫn ảnh cảnh báo
    timestamp = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# Tạo toàn bộ các bảng trong SQLite nếu chưa tồn tại
Base.metadata.create_all(bind=engine)

# Tiến hành di cư schema (migrations) an toàn cho SQLite đối với các cột mới
from sqlalchemy import text
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE faces ADD COLUMN created_at VARCHAR(50)"))
        conn.commit()
except Exception:
    pass

try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE faces ADD COLUMN created_by VARCHAR(100)"))
        conn.commit()
except Exception:
    pass
