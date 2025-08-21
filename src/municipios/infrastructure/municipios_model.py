# src/municipios/infrastructure/municipios_model.py
from sqlalchemy import Column, Integer, String
from src.core.database import Base

class Municipios(Base):
    __tablename__ = "municipios"
    
    id_municipio = Column(Integer, primary_key=True, autoincrement=True)
    clave_estado = Column(Integer, nullable=True)
    clave_municipio = Column(Integer, nullable=True)
    nombre = Column(String(100), nullable=True)
    
    # SIN RELACIONES para evitar conflictos de configuración
    # Puedes acceder a los análisis relacionados usando joins cuando sea necesario