# src/AnalisisSuelosPendientes/application/analisis_suelos_schemas.py
from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

class AnalisisSuelosBase(BaseModel):
    municipio_id_FK: Optional[int] = None
    numero: Optional[int] = None
    clave_estatal: Optional[int] = None
    estado_cuadernillo: Optional[str] = None
    clave_municipio: Optional[int] = None
    clave_munip: Optional[str] = None
    municipio_cuadernillo: Optional[str] = None
    clave_localidad: Optional[str] = None
    localidad_cuadernillo: Optional[str] = None
    recuento_curp_renapo: Optional[int] = None
    extraccion_edo: Optional[str] = None
    clave: Optional[str] = None
    ddr: Optional[str] = None
    cader: Optional[str] = None
    coordenada_x: Optional[str] = None
    coordenada_y: Optional[str] = None
    elevacion_msnm: Optional[int] = None
    profundidad_muestreo: Optional[str] = None
    fecha_muestreo: Optional[date] = None
    parcela: Optional[str] = None
    cultivo_anterior: Optional[str] = None
    cultivo_establecer: Optional[str] = None
    manejo: Optional[str] = None
    tipo_vegetacion: Optional[str] = None
    nombre_tecnico: Optional[str] = None
    tel_tecnico: Optional[str] = None
    correo_tecnico: Optional[str] = None
    nombre_productor: Optional[str] = None
    tel_productor: Optional[str] = None
    correo_productor: Optional[str] = None
    muestra: Optional[str] = None
    reemplazo: Optional[str] = None
    nombre_revisor: Optional[str] = None
    estatus: Optional[str] = None
    comentario_invalido: Optional[str] = None
    user_id_FK: Optional[int] = None

class AnalisisSuelosCreate(AnalisisSuelosBase):
    pass

class AnalisisSuelosResponse(AnalisisSuelosBase):
    id: int
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    message: str
    records_processed: int
    success_count: int
    error_count: int
    errors: list = []