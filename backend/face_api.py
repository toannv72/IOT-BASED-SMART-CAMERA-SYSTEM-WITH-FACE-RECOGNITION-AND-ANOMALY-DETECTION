import os
import json
import torch
import numpy as np
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image
import io

# --- Khởi tạo Database ---
# Lưu database trong thư mục backend
DB_PATH = os.path.join(os.path.dirname(__file__), "faces.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class FaceRecord(Base):
    __tablename__ = "faces"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    embedding = Column(Text) # Lưu numpy array dạng JSON string

Base.metadata.create_all(bind=engine)

# --- Khởi tạo AI Models (FaceNet) ---
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Loading FaceNet Backend models on {device}...")
mtcnn = MTCNN(keep_all=False, device=device) # Chỉ lấy 1 khuôn mặt bự nhất
resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

app = FastAPI(title="Face Registration API (Backend Layer)")

def get_embedding(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    face = mtcnn(img)
    if face is None:
        return None
    face = face.unsqueeze(0).to(device)
    embedding = resnet(face).detach().cpu().numpy()[0]
    return embedding

@app.post("/register")
async def register_face(name: str = Form(...), file: UploadFile = File(...)):
    image_bytes = await file.read()
    embedding = get_embedding(image_bytes)
    
    if embedding is None:
        raise HTTPException(status_code=400, detail="Không tìm thấy khuôn mặt nào trong ảnh!")
    
    emb_json = json.dumps(embedding.tolist())
    
    db = SessionLocal()
    new_face = FaceRecord(name=name, embedding=emb_json)
    db.add(new_face)
    db.commit()
    db.refresh(new_face)
    db.close()
    
    return {"message": "Đăng ký thành công!", "id": new_face.id, "name": new_face.name}

@app.get("/faces")
def get_all_faces():
    db = SessionLocal()
    faces = db.query(FaceRecord).all()
    db.close()
    return [{"id": f.id, "name": f.name} for f in faces]

@app.get("/embeddings")
def get_embeddings():
    db = SessionLocal()
    faces = db.query(FaceRecord).all()
    db.close()
    
    result = []
    for f in faces:
        result.append({
            "id": f.id,
            "name": f.name,
            "embedding": json.loads(f.embedding)
        })
    return result

@app.delete("/faces/{face_id}")
def delete_face(face_id: int):
    db = SessionLocal()
    face = db.query(FaceRecord).filter(FaceRecord.id == face_id).first()
    if not face:
        db.close()
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(face)
    db.commit()
    db.close()
    return {"message": "Đã xóa thành công!"}

if __name__ == "__main__":
    import uvicorn
    # Chạy ở port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
