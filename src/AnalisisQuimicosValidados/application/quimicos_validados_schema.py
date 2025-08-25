# src/AnalisisQuimicosValidados/application/quimicos_validados_schema.py
from pydantic import BaseModel, Field
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
        
class AnalisisValidadoListResponse(BaseModel):
    """Schema para la respuesta de listado de análisis validados"""
    id: int
    nombre_usuario: Optional[str] = None
    correo_usuario: str
    estatus: str
    nombre_archivo: Optional[str] = None
    fecha_validacion: Optional[str] = None
    fecha_creacion: Optional[str] = None

    class Config:
        from_attributes = True

class ListadoValidadosResponse(BaseModel):
    """Schema para la respuesta completa del listado"""
    success: bool
    message: str
    data: List[AnalisisValidadoListResponse]
    total: int
    limit: int
    offset: int
    timestamp: str
    
class AnalisisPendienteSimplificadoResponse(BaseModel):
    """Schema simplificado para análisis pendientes - solo campos esenciales"""
    id: int
    nombre_archivo: Optional[str] = None
    fecha_creacion: Optional[str] = None
    estatus: Optional[str] = None

    class Config:
        from_attributes = True

class UserAnalisisSimplificadoResponse(BaseModel):
    """Schema simplificado para respuesta de usuario con pendientes"""
    user_id: int
    correo_usuario: str
    nombre_usuario: Optional[str] = None
    total_pendientes: int
    analisis_pendientes: List[AnalisisPendienteSimplificadoResponse]

    class Config:
        from_attributes = True
        
class ArchivoPendienteResponse(BaseModel):
    """Schema para archivo pendiente agrupado"""
    nombre_archivo: str
    cantidad_analisis: int
    fecha_primer_registro: Optional[str] = None
    fecha_ultimo_registro: Optional[str] = None

    class Config:
        from_attributes = True

class UserAnalisisAgrupadoResponse(BaseModel):
    """Schema para respuesta de usuario con análisis agrupados por archivo"""
    user_id: int
    correo_usuario: str
    nombre_usuario: Optional[str] = None
    total_pendientes: int
    total_archivos: int
    archivos_pendientes: List[ArchivoPendienteResponse]

    class Config:
        from_attributes = True
        
        
class ValidacionPorArchivoRequest(BaseModel):
    """
    Schema para el request de validación por correo y nombre de archivo
    """
    nombre_archivo: str = Field(..., description="Nombre del archivo a validar")
    comentario_validacion: Optional[str] = Field(None, description="Comentario opcional de validación")
    
    class Config:
        schema_extra = {
            "example": {
                "nombre_archivo": "datos_analisis.xlsx",
                "comentario_validacion": "Validación aprobada por administrador"
            }
        }

class ValidacionArchivoResponse(BaseModel):
    """
    Schema para la respuesta de validación por archivo
    """
    status: str = Field(..., description="Estado de la validación: 'validado', 'sin_pendientes', etc.")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "validado"
            }
        }
        
class EliminacionConAdminRequest(BaseModel):
    """
    Schema para el request de eliminación con validación de administrador
    """
    nombre_archivo: str = Field(..., description="Nombre del archivo a eliminar")
    admin_id: int = Field(..., description="ID del administrador que autoriza la eliminación")
    user_id_objetivo: Optional[int] = Field(None, description="ID específico del usuario propietario (opcional)")
    
    class Config:
        schema_extra = {
            "example": {
                "nombre_archivo": "ggggg.xlsx",
                "admin_id": 1,
                "user_id_objetivo": 1
            }
        }

class EliminacionConAdminResponse(BaseModel):
    """
    Schema para la respuesta de eliminación con validación de admin
    """
    success: bool
    message: str
    usuario: str
    archivo: str
    eliminados: int
    autorizado_por: Optional[dict] = None
    detalles: Optional[dict] = None
    user_ids_encontrados: Optional[List[int]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Se eliminaron exitosamente 71 registros del archivo 'ggggg.xlsx'",
                "usuario": "Denzel@gmail.com",
                "archivo": "ggggg.xlsx",
                "eliminados": 71,
                "autorizado_por": {
                    "admin_id": 1,
                    "admin_nombre": "Admin User",
                    "admin_correo": "admin@sistema.com"
                }
            }
        }
        
class AnalisisValidadoAgrupadoResponse(BaseModel):
    """Schema para análisis validados agrupados por archivo"""
    nombre_usuario: Optional[str] = None
    correo_usuario: str
    nombre_archivo: Optional[str] = None
    cantidad_analisis: int
    estatus: str
    fecha_validacion: Optional[str] = None
    fecha_creacion: Optional[str] = None
    rango_fechas: Optional[dict] = None

    class Config:
        from_attributes = True

class ListadoValidadosAgrupadosResponse(BaseModel):
    """Schema para la respuesta completa del listado agrupado"""
    success: bool
    message: str
    data: List[AnalisisValidadoAgrupadoResponse]
    total: int
    timestamp: str