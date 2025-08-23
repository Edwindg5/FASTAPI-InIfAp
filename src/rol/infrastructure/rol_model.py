# src/rol/infrastructure/rol_model.py
from sqlalchemy import Column, Integer, String
from src.core.database import Base

class Rol(Base):
    __tablename__ = "rol"

    id_rol = Column(Integer, primary_key=True, index=True, autoincrement=True)
    titulo = Column(String(50), nullable=True)