# src/AnalisisSuelosPendientes/infrastructure/analisis_suelos_model.py
from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from sqlalchemy.orm import relationship
from src.core.database import Base

class AnalisisSuelosPendientes(Base):
    __tablename__ = "analisis_suelos_pendientes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    municipio_id_FK = Column(Integer, ForeignKey("municipios.id_municipio"), nullable=True)
    user_id_FK = Column(Integer, ForeignKey("users.ID_user"), nullable=True)
    numero = Column(Integer, nullable=True)
    clave_estatal = Column(Integer, nullable=True)
    estado_cuadernillo = Column(String(100), nullable=True)
    clave_municipio = Column(Integer, nullable=True)
    clave_munip = Column(String(10), nullable=True)
    municipio_cuadernillo = Column(String(100), nullable=True)
    clave_localidad = Column(String(10), nullable=True)
    localidad_cuadernillo = Column(String(100), nullable=True)
    recuento_curp_renapo = Column(Integer, nullable=True)
    extraccion_edo = Column(String(10), nullable=True)
    clave = Column(String(50), nullable=True)
    ddr = Column(String(100), nullable=True)
    cader = Column(String(100), nullable=True)
    coordenada_x = Column(String(50), nullable=True)
    coordenada_y = Column(String(50), nullable=True)
    elevacion_msnm = Column(Integer, nullable=True)
    profundidad_muestreo = Column(String(50), nullable=True)
    fecha_muestreo = Column(Date, nullable=True)
    parcela = Column(String(100), nullable=True)
    cultivo_anterior = Column(String(100), nullable=True)
    cultivo_establecer = Column(String(100), nullable=True)
    manejo = Column(String(100), nullable=True)
    tipo_vegetacion = Column(String(100), nullable=True)
    nombre_tecnico = Column(String(150), nullable=True)
    tel_tecnico = Column(String(20), nullable=True)
    correo_tecnico = Column(String(150), nullable=True)
    nombre_productor = Column(String(150), nullable=True)
    tel_productor = Column(String(20), nullable=True)
    correo_productor = Column(String(150), nullable=True)
    muestra = Column(String(50), nullable=True)
    reemplazo = Column(String(50), nullable=True)
    nombre_revisor = Column(String(150), nullable=True)
    estatus = Column(String(20), nullable=True)
    comentario_invalido = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=func.current_timestamp())
    nombre_archivo = Column(String(255), nullable=True)
    
