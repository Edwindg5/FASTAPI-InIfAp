# src/AnalisisQuimicosPendientes/interfaces/analisis_quimicos_router.py
from fastapi import APIRouter, UploadFile, Depends
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.AnalisisQuimicosPendientes.application.analisis_quimicos_service import procesar_excel_y_guardar

router = APIRouter(prefix="/analisis-quimicos", tags=["Análisis Químicos"])

@router.post("/upload-excel/")
async def upload_excel(file: UploadFile, db: Session = Depends(get_db)):
    file_bytes = await file.read()
    resumen = procesar_excel_y_guardar(file_bytes, db)
    return {
        "msg": "Archivo procesado",
        **resumen
    }
