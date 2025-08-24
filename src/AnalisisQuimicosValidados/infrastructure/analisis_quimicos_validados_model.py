# src/AnalisisQuimicosValidados/infrastructure/analisis_quimicos_validados_model.py
from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base

class AnalisisQuimicosValidados(Base):
    __tablename__ = "analisis_quimicos_validados"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    municipio_id_FK = Column(Integer, ForeignKey("municipios.id_municipio"), nullable=True)
    user_id_FK = Column(Integer, ForeignKey("users.ID_user"), nullable=True)

    municipio = Column(String(100), nullable=True)
    localidad = Column(String(100), nullable=True)
    nombre_productor = Column(String(255), nullable=True)
    cultivo_anterior = Column(String(100), nullable=True)

    arcilla = Column(DECIMAL(10,2), nullable=True)
    limo = Column(DECIMAL(10,2), nullable=True)
    arena = Column(DECIMAL(10,2), nullable=True)
    textura = Column(String(50), nullable=True)
    da = Column(DECIMAL(10,2), nullable=True)
    ph = Column(DECIMAL(5,2), nullable=True)
    mo = Column(DECIMAL(10,2), nullable=True)
    fosforo = Column(DECIMAL(10,2), nullable=True)
    n_inorganico = Column(DECIMAL(10,2), nullable=True)
    k = Column(DECIMAL(10,2), nullable=True)
    mg = Column(DECIMAL(10,2), nullable=True)
    ca = Column(DECIMAL(10,2), nullable=True)
    na = Column(DECIMAL(10,2), nullable=True)
    al = Column(DECIMAL(10,2), nullable=True)
    cic = Column(DECIMAL(10,2), nullable=True)
    cic_calculada = Column(DECIMAL(10,2), nullable=True)
    h = Column(DECIMAL(10,2), nullable=True)
    azufre = Column(DECIMAL(10,2), nullable=True)
    hierro = Column(DECIMAL(10,2), nullable=True)
    cobre = Column(DECIMAL(10,2), nullable=True)
    zinc = Column(DECIMAL(10,2), nullable=True)
    manganeso = Column(DECIMAL(10,2), nullable=True)
    boro = Column(DECIMAL(10,2), nullable=True)

    columna1 = Column(String(100), nullable=True)
    columna2 = Column(String(100), nullable=True)
    ca_mg = Column(DECIMAL(10,2), nullable=True)
    mg_k = Column(DECIMAL(10,2), nullable=True)
    ca_k = Column(DECIMAL(10,2), nullable=True)
    ca_mg_k = Column(DECIMAL(10,2), nullable=True)
    k_mg = Column(DECIMAL(10,2), nullable=True)

    # ¡NUEVO CAMPO AGREGADO!
    nombre_archivo = Column(String(255), nullable=True)
    
    fecha_validacion = Column(DateTime, default=func.now())
    fecha_creacion = Column(DateTime, default=func.now())

    # Relaciones
    municipio_rel = relationship("Municipios", foreign_keys=[municipio_id_FK])
    user_rel = relationship("Users", foreign_keys=[user_id_FK])