# src/AnalisisSuelosPendientes/interfaces/analisis_suelos_router.py
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

@router.get("/{analisis_id}", response_model=AnalisisSuelosResponse)
def get_analisis_suelos_by_id(
    analisis_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene un análisis de suelos específico por ID
    """
    analisis = AnalisisSuelosService.get_analisis_suelos_by_id(db, analisis_id)
    if not analisis:
        raise HTTPException(status_code=404, detail="Análisis de suelos no encontrado")
    return analisis

@router.post("/", response_model=AnalisisSuelosResponse)
def create_analisis_suelos(
    analisis_data: AnalisisSuelosCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo análisis de suelos pendiente
    """
    return AnalisisSuelosService.create_analisis_suelos(db=db, analisis_data=analisis_data)

@router.delete("/{analisis_id}")
def delete_analisis_suelos(
    analisis_id: int,
    db: Session = Depends(get_db)
):
    """
    Elimina un análisis de suelos por ID
    """
    deleted = AnalisisSuelosService.delete_analisis_suelos(db, analisis_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Análisis de suelos no encontrado")
    return {"message": "Análisis de suelos eliminado exitosamente"}