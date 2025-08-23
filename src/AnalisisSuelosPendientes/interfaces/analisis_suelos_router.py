# Actualización del router - src/AnalisisSuelosPendientes/interfaces/analisis_suelos_router.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List
from src.core.database import get_db
from src.AnalisisSuelosPendientes.application.analisis_suelos_service import AnalisisSuelosService
from src.AnalisisSuelosPendientes.application.analisis_suelos_schemas import (
    AnalisisSuelosResponse, 
    AnalisisSuelosCreate, 
    UploadResponse
)

router = APIRouter(
    prefix="/analisis-suelos-pendientes",
    tags=["Análisis de Suelos Pendientes"]
)

@router.post("/upload-excel", response_model=UploadResponse)
async def upload_excel_analisis_suelos(
    file: UploadFile = File(...),
    user_id: int = Query(..., description="ID del usuario que sube el archivo"),
    db: Session = Depends(get_db)
):
    """
    Sube un archivo Excel y extrae datos para análisis de suelos pendientes
    """
    # Validar el tipo de archivo
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400, 
            detail="El archivo debe ser de tipo Excel (.xlsx o .xls)"
        )

    try:
        # Leer el contenido del archivo
        file_content = await file.read()

        # Procesar el archivo
        result = AnalisisSuelosService.process_excel_file(
            file_content=file_content,
            user_id=user_id,
            db=db
        )

        return UploadResponse(**result)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo: {str(e)}")

@router.get("/", response_model=List[AnalisisSuelosResponse])
def get_analisis_suelos_pendientes(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de registros a retornar"),
    db: Session = Depends(get_db)
):
    """
    Obtiene la lista de análisis de suelos pendientes
    """
    analisis_list = AnalisisSuelosService.get_all_analisis_suelos(db, skip=skip, limit=limit)
    return analisis_list

# NUEVO ENDPOINT - Solo usuarios con estatus pendiente
@router.get("/usuario/{user_id}/pendientes", response_model=List[AnalisisSuelosResponse])
def get_analisis_suelos_pendientes_by_user(
    user_id: int,
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de registros a retornar"),
    db: Session = Depends(get_db)
):
    """
    Obtiene solo los análisis de suelos PENDIENTES de un usuario específico
    """
    analisis_list = AnalisisSuelosService.get_analisis_suelos_pendientes_by_user(
        db, user_id=user_id, skip=skip, limit=limit
    )
    
    if not analisis_list:
        raise HTTPException(
            status_code=404, 
            detail=f"No se encontraron análisis de suelos pendientes para el usuario {user_id}"
        )
    
    return analisis_list


# NUEVO ENDPOINT - Todos los usuarios con análisis pendientes
@router.get("/usuarios/con-pendientes")
def get_usuarios_con_analisis_pendientes(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de registros a retornar"),
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los usuarios que tienen análisis de suelos pendientes
    con resumen de información de cada usuario
    """
    usuarios_con_pendientes = AnalisisSuelosService.get_usuarios_con_analisis_pendientes(
        db, skip=skip, limit=limit
    )
    
    if not usuarios_con_pendientes:
        raise HTTPException(
            status_code=404, 
            detail="No se encontraron usuarios con análisis de suelos pendientes"
        )
    
    return {
        "total_usuarios_con_pendientes": len(usuarios_con_pendientes),
        "usuarios": usuarios_con_pendientes
    }