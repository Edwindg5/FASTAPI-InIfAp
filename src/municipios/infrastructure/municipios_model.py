# src/Municipios/infrastructure/municipios_model.py
from sqlalchemy import Column, Integer, String
from src.core.database import Base

class Municipios(Base):
    __tablename__ = "municipios"

    id_municipio = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
