# src/municipios/infrastructure/municipios_model.py
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from src.core.database import Base

class Municipios(Base):
    __tablename__ = "municipios"
    
    id_municipio = Column(Integer, primary_key=True, autoincrement=True)
    clave_estado = Column(Integer, nullable=True)
    clave_municipio = Column(Integer, nullable=True)
    nombre = Column(String(100), nullable=True)
    
    # Relaciones
    analisis_quimicos_pendientes = relationship("AnalisisQuimicosPendientes", back_populates="municipio")
    analisis_suelos_pendientes = relationship("AnalisisSuelosPendientes", back_populates="municipio")