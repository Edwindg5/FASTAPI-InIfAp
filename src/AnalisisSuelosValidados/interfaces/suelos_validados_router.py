# src/AnalisisSuelosValidados/interfaces/suelos_validados_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, EmailStr
from src.core.database import get_db
from src.AnalisisSuelosValidados.application.analisis_suelos_validados_service import AnalisisSuelosValidadosService
from src.AnalisisSuelosValidados.infrastructure.excel_export_service import ExcelExportService
import io

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

class AnalisisPendienteResponse(BaseModel):
    success: bool
    message: str = None
    total_registros: int
    usuario_info: dict = None
    datos: List[dict] = []

# ENDPOINT 1: Validar análisis por correo
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


# ENDPOINT 2: Exportar análisis pendientes a Excel
@router.get("/pendientes/exportar-excel/{correo_usuario}")
def exportar_pendientes_excel(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Exporta todos los análisis pendientes de un usuario específico a un archivo Excel.
    """
    try:
        # Obtener datos del servicio
        service = AnalisisSuelosValidadosService(db)
        resultado = service.obtener_pendientes_detallados_por_correo(correo_usuario)
        
        if not resultado["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=resultado["message"]
            )
        
        # Crear el archivo Excel
        excel_service = ExcelExportService()
        excel_buffer = excel_service.exportar_pendientes_a_excel(
            datos=resultado["datos"],
            usuario_info=resultado.get("usuario_info", {}),
            correo_usuario=correo_usuario
        )
        
        if not excel_buffer:
            # Si falla la exportación completa, intentar con versión simple
            try:
                excel_buffer = excel_service.crear_excel_simple(
                    datos=resultado["datos"],
                    usuario_info=resultado.get("usuario_info", {}),
                    correo_usuario=correo_usuario
                )
            except Exception as simple_error:
                print(f"Error también en Excel simple: {str(simple_error)}")
                
            if not excel_buffer:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error al generar el archivo Excel"
                )
        
        # Configurar respuesta de descarga
        excel_buffer.seek(0)
        
        # Nombre del archivo con información del usuario
        usuario_info = resultado.get("usuario_info", {})
        nombre_usuario = usuario_info.get("nombre", "Usuario")
        apellido_usuario = usuario_info.get("apellido", "")
        nombre_archivo = f"Analisis_Pendientes_{nombre_usuario}_{apellido_usuario}_{correo_usuario.replace('@', '_').replace('.', '_')}.xlsx"
        
        response = StreamingResponse(
            io.BytesIO(excel_buffer.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={nombre_archivo}"
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )