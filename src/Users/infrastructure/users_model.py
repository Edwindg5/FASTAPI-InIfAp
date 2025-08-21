# src/Users/infrastructure/users_model.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.core.database import Base

class Users(Base):
    __tablename__ = "users"
    
    ID_user = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=True)
    apellido = Column(String(100), nullable=True)
    correo = Column(String(150), nullable=False, unique=True)
    numero_telefonico = Column(String(20), nullable=True)
    password = Column(String(255), nullable=True)
    rol_id_FK = Column(Integer, ForeignKey("rol.id_rol"), nullable=True)
    
