# src/AnalisisQuimicosValidados/application/validacion_simple_schema.py
from pydantic import BaseModel
from typing import Optional

class ValidacionSimpleResponse(BaseModel):
    """
    Respuesta simple para validación de análisis
    """
    status: str  # "validado", "sin_pendientes", "error"

class ValidacionCompletaResponse(BaseModel):
    """
    Respuesta completa para validación de análisis con más detalles
    """
    status: str
    usuario: str
    total_validados: int
    administrador_id: int = 1

class ValidacionSinPendientesResponse(BaseModel):
    """
    Respuesta cuando el usuario no tiene pendientes
    """
    status: str
    usuario: str
    message: str

class ValidacionPorCorreoRequest(BaseModel):
    """
    Request opcional para validación por correo
    """
    comentario_validacion: Optional[str] = None