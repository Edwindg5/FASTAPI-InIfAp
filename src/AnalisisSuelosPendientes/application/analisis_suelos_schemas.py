# src/AnalisisSuelosPendientes/application/analisis_suelos_schemas.py
from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from typing import Any, Dict, Optional, List, Literal

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
    processing_time_seconds: float = 0.0  
    errors: List[str] = []
    municipios_not_found: List[str] = []

class UsuarioConPendientesResponse(BaseModel):
    """Schema para mostrar usuarios con análisis pendientes"""
    user_id: int
    nombre_usuario: Optional[str] = None
    apellido_usuario: Optional[str] = None
    correo_usuario: Optional[str] = None
    total_pendientes: int
    ultimo_analisis_fecha: Optional[datetime] = None
    municipios_involucrados: List[str] = []
    
    class Config:
        from_attributes = True

class ResumenUsuariosPendientesResponse(BaseModel):
    """Schema para el resumen completo de usuarios con pendientes"""
    total_usuarios_con_pendientes: int
    usuarios: List[UsuarioConPendientesResponse]

# NUEVOS SCHEMAS PARA COMENTARIOS INVÁLIDOS
class ComentarioInvalidoCreate(BaseModel):
    """Schema para crear comentario inválido"""
    admin_id: int
    correo_usuario: EmailStr
    comentario_invalido: str
    
    class Config:
        from_attributes = True

class ComentarioInvalidoResponse(BaseModel):
    """Schema de respuesta para comentario creado"""
    message: str
    comentario_id: int
    correo_usuario: str
    comentario_invalido: str
    registros_afectados: int
    fecha_comentario: datetime
    
class EstadisticasGeneralesResponse(BaseModel):
    """Schema para estadísticas generales del sistema"""
    total_analisis_pendientes: int
    total_usuarios_con_pendientes: int
    municipios_mas_frecuentes: List[Dict[str, Any]] = []
    usuarios_con_mas_pendientes: List[Dict[str, Any]] = []
    fecha_consulta: datetime
    
    class Config:
        from_attributes = True

class MunicipioFrecuenteResponse(BaseModel):
    """Schema para municipios más frecuentes"""
    municipio: str
    total: int

class UsuarioTopResponse(BaseModel):
    """Schema para usuarios con más pendientes"""
    correo: str
    total_pendientes: int
    
class EliminarPendientesResponse(BaseModel):
    """Schema de respuesta para eliminación de pendientes"""
    message: str
    correo_usuario: str
    user_id: int
    registros_eliminados: int
    total_antes: int
    fecha_eliminacion: datetime
    
    class Config:
        from_attributes = True
        
class UsuarioConValidadosResponse(BaseModel):
    """Schema para mostrar usuarios con análisis validados"""
    user_id: int
    nombre_usuario: Optional[str] = None
    apellido_usuario: Optional[str] = None
    correo_usuario: Optional[str] = None
    total_validados: int
    ultimo_analisis_fecha: Optional[datetime] = None
    municipios_involucrados: List[str] = []
    
    class Config:
        from_attributes = True

class ResumenUsuariosValidadosResponse(BaseModel):
    """Schema para el resumen completo de usuarios con validados"""
    total_usuarios_con_validados: int
    usuarios: List[UsuarioConValidadosResponse]

class UsuarioInfoResponse(BaseModel):
    """Schema para información básica del usuario"""
    user_id: int
    nombre_completo: str
    correo: str

class AnalisisValidadoDetalleResponse(BaseModel):
    """Schema para detalle de un análisis validado"""
    id: int
    numero: Optional[int] = None
    fecha_creacion: datetime
    municipio_cuadernillo: Optional[str] = None
    localidad_cuadernillo: Optional[str] = None
    clave_estatal: Optional[int] = None
    clave_municipio: Optional[int] = None
    cultivo_establecer: Optional[str] = None
    nombre_tecnico: Optional[str] = None
    nombre_productor: Optional[str] = None
    fecha_muestreo: Optional[date] = None
    estatus: str
    nombre_revisor: Optional[str] = None

class AnalisisValidadosPorCorreoResponse(BaseModel):
    """Schema para análisis validados de un usuario específico"""
    usuario_info: UsuarioInfoResponse
    total_validados: int
    analisis_validados: List[AnalisisValidadoDetalleResponse]
    municipios_involucrados: List[str] = []
    ultimo_analisis_fecha: Optional[datetime] = None
    message: str

