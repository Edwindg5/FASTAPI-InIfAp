# src/AnalisisQuimicosPendientes/interfaces/analisis_quimicos_router.py
from fastapi import APIRouter, UploadFile, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.AnalisisQuimicosPendientes.application.analisis_quimicos_service import procesar_excel_y_guardar

router = APIRouter(prefix="/analisis-quimicos", tags=["Análisis Químicos"])

@router.post("/upload-excel/")
async def upload_excel(
    file: UploadFile, 
    correo_usuario: str = Form(..., description="Correo electrónico del usuario que sube el archivo"),
    db: Session = Depends(get_db)
):
    """
    Procesa y almacena un archivo Excel con datos de análisis químicos.
    
    Args:
        file: Archivo Excel a procesar
        correo_usuario: Correo electrónico del usuario (debe existir en la tabla users)
        db: Sesión de base de datos
    
    Returns:
        Resumen del procesamiento incluyendo estadísticas y errores
    """
    # Validar que el archivo sea Excel
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400, 
            detail="El archivo debe ser un Excel (.xlsx o .xls)"
        )
    
    # Validar que el correo no esté vacío
    if not correo_usuario or not correo_usuario.strip():
        raise HTTPException(
            status_code=400, 
            detail="El correo del usuario es obligatorio"
        )
    
    try:
        file_bytes = await file.read()
        resumen = procesar_excel_y_guardar(file_bytes, correo_usuario.strip(), db)
        
        # Si la validación del usuario falló, devolver error HTTP
        if not resumen.get("success", False) and "no encontrado" in resumen.get("error", ""):
            raise HTTPException(
                status_code=404,
                detail=resumen.get("error")
            )
        
        return {
            "msg": "Archivo procesado exitosamente",
            **resumen
        }
    
    except HTTPException:
        raise  # Re-lanzar excepciones HTTP
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )