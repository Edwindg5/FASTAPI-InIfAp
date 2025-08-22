# src/AnalisisSuelosValidados/interfaces/suelos_validados_router.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, EmailStr
from src.core.database import get_db
from src.AnalisisSuelosValidados.application.analisis_suelos_validados_service import AnalisisSuelosValidadosService

router = APIRouter(
    prefix="/api/v1/suelos-validados",
    tags=["Análisis de Suelos Validados"]
)

# Schemas
class ValidarPorCorreoRequest(BaseModel):
    correo_usuario: EmailStr

class ValidarPorCorreoResponse(BaseModel):
    success: bool
    message: str
    validados: int = None
    usuario: dict = None

class AnalisisSuelosValidadosResponse(BaseModel):
    id: int
    municipio_cuadernillo: str = None
    localidad_cuadernillo: str = None
    nombre_productor: str = None
    nombre_tecnico: str = None
    cultivo_anterior: str = None
    cultivo_establecer: str = None
    fecha_muestreo: str = None
    fecha_validacion: str = None
    fecha_creacion: str = None
    
    class Config:
        from_attributes = True

class EstadisticasResponse(BaseModel):
    total_validados: int
    por_municipio: List[dict]

# Endpoints
@router.post("/validar-por-correo", response_model=ValidarPorCorreoResponse)
def validar_analisis_por_correo(
    request: ValidarPorCorreoRequest,
    db: Session = Depends(get_db)
):
    """
    Valida todos los análisis pendientes de un usuario específico por su correo.
    Mueve los datos a la tabla validados y los elimina de pendientes.
    """
    service = AnalisisSuelosValidadosService(db)
    resultado = service.validar_analisis_por_correo(request.correo_usuario)
    
    if not resultado["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=resultado["message"]
        )
    
    return ValidarPorCorreoResponse(
        success=resultado["success"],
        message=resultado["message"],
        validados=resultado.get("validados"),
        usuario=resultado.get("usuario")
    )

@router.get("/todos", response_model=List[AnalisisSuelosValidadosResponse])
def obtener_todos_validados(db: Session = Depends(get_db)):
    """
    Obtiene todos los análisis de suelos validados.
    """
    service = AnalisisSuelosValidadosService(db)
    validados = service.obtener_todos_validados()
    
    return [
        AnalisisSuelosValidadosResponse(
            id=v.id,
            municipio_cuadernillo=v.municipio_cuadernillo,
            localidad_cuadernillo=v.localidad_cuadernillo,
            nombre_productor=v.nombre_productor,
            nombre_tecnico=v.nombre_tecnico,
            cultivo_anterior=v.cultivo_anterior,
            cultivo_establecer=v.cultivo_establecer,
            fecha_muestreo=str(v.fecha_muestreo) if v.fecha_muestreo else None,
            fecha_validacion=str(v.fecha_validacion) if v.fecha_validacion else None,
            fecha_creacion=str(v.fecha_creacion) if v.fecha_creacion else None
        )
        for v in validados
    ]

@router.get("/por-correo/{correo_usuario}", response_model=List[AnalisisSuelosValidadosResponse])
def obtener_validados_por_correo(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los análisis validados de un usuario específico por su correo.
    """
    service = AnalisisSuelosValidadosService(db)
    validados = service.obtener_validados_por_correo(correo_usuario)
    
    if not validados:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron análisis validados para este usuario"
        )
    
    return [
        AnalisisSuelosValidadosResponse(
            id=v.id,
            municipio_cuadernillo=v.municipio_cuadernillo,
            localidad_cuadernillo=v.localidad_cuadernillo,
            nombre_productor=v.nombre_productor,
            nombre_tecnico=v.nombre_tecnico,
            cultivo_anterior=v.cultivo_anterior,
            cultivo_establecer=v.cultivo_establecer,
            fecha_muestreo=str(v.fecha_muestreo) if v.fecha_muestreo else None,
            fecha_validacion=str(v.fecha_validacion) if v.fecha_validacion else None,
            fecha_creacion=str(v.fecha_creacion) if v.fecha_creacion else None
        )
        for v in validados
    ]

@router.get("/estadisticas", response_model=EstadisticasResponse)
def obtener_estadisticas(db: Session = Depends(get_db)):
    """
    Obtiene estadísticas de los análisis validados.
    """
    service = AnalisisSuelosValidadosService(db)
    stats = service.obtener_estadisticas_validados()
    
    return EstadisticasResponse(
        total_validados=stats["total_validados"],
        por_municipio=stats["por_municipio"]
    )