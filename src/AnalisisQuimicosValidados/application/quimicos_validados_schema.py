# src/AnalisisQuimicosValidados/application/quimicos_validados_schema.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class AnalisisQuimicoValidadoBase(BaseModel):
    municipio_id_FK: Optional[int] = None
    user_id_FK: Optional[int] = None
    municipio: Optional[str] = None
    localidad: Optional[str] = None
    nombre_productor: Optional[str] = None
    cultivo_anterior: Optional[str] = None
    arcilla: Optional[Decimal] = None
    limo: Optional[Decimal] = None
    arena: Optional[Decimal] = None
    textura: Optional[str] = None
    da: Optional[Decimal] = None
    ph: Optional[Decimal] = None
    mo: Optional[Decimal] = None
    fosforo: Optional[Decimal] = None
    n_inorganico: Optional[Decimal] = None
    k: Optional[Decimal] = None
    mg: Optional[Decimal] = None
    ca: Optional[Decimal] = None
    na: Optional[Decimal] = None
    al: Optional[Decimal] = None
    cic: Optional[Decimal] = None
    cic_calculada: Optional[Decimal] = None
    h: Optional[Decimal] = None
    azufre: Optional[Decimal] = None
    hierro: Optional[Decimal] = None
    cobre: Optional[Decimal] = None
    zinc: Optional[Decimal] = None
    manganeso: Optional[Decimal] = None
    boro: Optional[Decimal] = None
    columna1: Optional[str] = None
    columna2: Optional[str] = None
    ca_mg: Optional[Decimal] = None
    mg_k: Optional[Decimal] = None
    ca_k: Optional[Decimal] = None
    ca_mg_k: Optional[Decimal] = None
    k_mg: Optional[Decimal] = None
    # ¡NUEVO CAMPO AGREGADO!
    nombre_archivo: Optional[str] = None

class AnalisisQuimicoValidadoCreate(AnalisisQuimicoValidadoBase):
    pass

class AnalisisQuimicoValidadoResponse(AnalisisQuimicoValidadoBase):
    id: int
    fecha_validacion: Optional[datetime] = None
    fecha_creacion: Optional[datetime] = None

    class Config:
        from_attributes = True

class AnalisisPendienteResponse(BaseModel):
    id: int
    municipio_id_FK: Optional[int] = None
    user_id_FK: Optional[int] = None
    municipio: Optional[str] = None
    localidad: Optional[str] = None
    nombre_productor: Optional[str] = None
    cultivo_anterior: Optional[str] = None
    arcilla: Optional[Decimal] = None
    limo: Optional[Decimal] = None
    arena: Optional[Decimal] = None
    textura: Optional[str] = None
    da: Optional[Decimal] = None
    ph: Optional[Decimal] = None
    mo: Optional[Decimal] = None
    fosforo: Optional[Decimal] = None
    n_inorganico: Optional[Decimal] = None
    k: Optional[Decimal] = None
    mg: Optional[Decimal] = None
    ca: Optional[Decimal] = None
    na: Optional[Decimal] = None
    al: Optional[Decimal] = None
    cic: Optional[Decimal] = None
    cic_calculada: Optional[Decimal] = None
    h: Optional[Decimal] = None
    azufre: Optional[Decimal] = None
    hierro: Optional[Decimal] = None
    cobre: Optional[Decimal] = None
    zinc: Optional[Decimal] = None
    manganeso: Optional[Decimal] = None
    boro: Optional[Decimal] = None
    columna1: Optional[str] = None
    columna2: Optional[str] = None
    ca_mg: Optional[Decimal] = None
    mg_k: Optional[Decimal] = None
    ca_k: Optional[Decimal] = None
    ca_mg_k: Optional[Decimal] = None
    k_mg: Optional[Decimal] = None
    estatus: Optional[str] = None
    comentario_invalido: Optional[str] = None
    # ¡CAMPO YA EXISTE EN PENDIENTES!
    nombre_archivo: Optional[str] = None
    fecha_creacion: Optional[datetime] = None

    class Config:
        from_attributes = True

class ValidacionRequest(BaseModel):
    analisis_ids: List[int]
    comentario_validacion: Optional[str] = None

class ValidacionResponse(BaseModel):
    success: bool
    message: str
    validados: int
    errores: List[dict] = []

class UserAnalisisResponse(BaseModel):
    user_id: int
    correo_usuario: str
    nombre_usuario: Optional[str] = None
    total_pendientes: int
    analisis_pendientes: List[AnalisisPendienteResponse]

    class Config:
        from_attributes = True