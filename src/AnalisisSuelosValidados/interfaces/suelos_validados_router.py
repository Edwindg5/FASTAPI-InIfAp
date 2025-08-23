# src/AnalisisSuelosValidados/interfaces/suelos_validados_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, EmailStr
from src.core.database import get_db
from src.AnalisisSuelosValidados.application.analisis_suelos_validados_service import AnalisisSuelosValidadosService
from src.AnalisisSuelosValidados.infrastructure.excel_export_service import ExcelExportService
from src.AnalisisSuelosValidados.infrastructure.excel_export_validados_service import ExcelExportValidadosService
import io
from datetime import datetime

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

class TodosAnalisisPendientesResponse(BaseModel):
    success: bool
    message: str = None
    total_registros: int
    total_usuarios: int
    usuarios_con_pendientes: List[str] = []
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
                    datos=resultado["datos"]
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


# ENDPOINT 3: Exportar TODOS los análisis pendientes de TODOS los usuarios a Excel
@router.get("/pendientes/exportar-excel-todos")
def exportar_todos_pendientes_excel(
    db: Session = Depends(get_db)
):
    """
    Exporta TODOS los análisis pendientes de TODOS los usuarios a un archivo Excel.
    Incluye información detallada de cada usuario propietario de los análisis.
    """
    try:
        # Obtener todos los datos del servicio
        service = AnalisisSuelosValidadosService(db)
        resultado = service.obtener_todos_los_pendientes_detallados()
        
        if not resultado["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=resultado["message"]
            )
        
        # Crear el archivo Excel
        excel_service = ExcelExportService()
        excel_buffer = excel_service.exportar_todos_pendientes_a_excel(
            datos=resultado["datos"],
            total_usuarios=resultado.get("total_usuarios", 0),
            usuarios_con_pendientes=resultado.get("usuarios_con_pendientes", [])
        )
        
        if not excel_buffer:
            # Si falla la exportación completa, intentar con versión simple
            try:
                excel_buffer = excel_service.crear_excel_simple_todos(
                    datos=resultado["datos"]
                )
            except Exception as simple_error:
                print(f"Error también en Excel simple de todos: {str(simple_error)}")
                
            if not excel_buffer:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error al generar el archivo Excel"
                )
        
        # Configurar respuesta de descarga
        excel_buffer.seek(0)
        
        # Nombre del archivo con información general
        fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"Todos_Analisis_Pendientes_{resultado.get('total_usuarios', 0)}_usuarios_{resultado.get('total_registros', 0)}_registros_{fecha_actual}.xlsx"
        
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

# ENDPOINT 4: Obtener vista previa de todos los análisis pendientes (opcional)
@router.get("/pendientes/todos", response_model=TodosAnalisisPendientesResponse)
def obtener_todos_pendientes(
    db: Session = Depends(get_db),
    limite: int = 100
):
    """
    Obtiene todos los análisis pendientes de todos los usuarios.
    Útil para vista previa antes de exportar a Excel.
    
    Args:
        limite: Número máximo de registros a devolver (por defecto 100)
    """
    try:
        service = AnalisisSuelosValidadosService(db)
        resultado = service.obtener_todos_los_pendientes_detallados()
        
        if not resultado["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=resultado["message"]
            )
        
        # Limitar los datos si es necesario
        datos_limitados = resultado["datos"][:limite] if limite > 0 else resultado["datos"]
        
        return TodosAnalisisPendientesResponse(
            success=resultado["success"],
            message=resultado["message"],
            total_registros=resultado["total_registros"],
            total_usuarios=resultado["total_usuarios"],
            usuarios_con_pendientes=resultado.get("usuarios_con_pendientes", []),
            datos=datos_limitados
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )
        
class AnalisisValidadosResponse(BaseModel):
    success: bool
    message: str = None
    total_registros: int
    usuario_info: dict = None
    datos: List[dict] = []

class TodosAnalisisValidadosResponse(BaseModel):
    success: bool
    message: str = None
    total_registros: int
    total_usuarios: int
    usuarios_con_validados: List[str] = []
    datos: List[dict] = []

# ENDPOINT 5: Exportar análisis validados de un usuario a Excel
@router.get("/validados/exportar-excel/{correo_usuario}")
def exportar_validados_excel(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Exporta todos los análisis validados de un usuario específico a un archivo Excel.
    """
    try:
        # Obtener datos del servicio
        service = AnalisisSuelosValidadosService(db)
        resultado = service.obtener_validados_detallados_por_correo(correo_usuario)
        
        if not resultado["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=resultado["message"]
            )
        
        # Crear el archivo Excel
        excel_service = ExcelExportValidadosService()
        excel_buffer = excel_service.exportar_validados_a_excel(
            datos=resultado["datos"],
            usuario_info=resultado.get("usuario_info", {}),
            correo_usuario=correo_usuario
        )
        
        if not excel_buffer:
            # Si falla la exportación completa, intentar con versión simple
            try:
                excel_buffer = excel_service.crear_excel_simple(
                    datos=resultado["datos"]
                )
            except Exception as simple_error:
                print(f"Error también en Excel simple de validados: {str(simple_error)}")
                
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
        nombre_archivo = f"Analisis_Validados_{nombre_usuario}_{apellido_usuario}_{correo_usuario.replace('@', '_').replace('.', '_')}.xlsx"
        
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


# ENDPOINT 6: Exportar TODOS los análisis validados de TODOS los usuarios a Excel
@router.get("/validados/exportar-excel-todos")
def exportar_todos_validados_excel(
    db: Session = Depends(get_db)
):
    """
    Exporta TODOS los análisis validados de TODOS los usuarios a un archivo Excel.
    Incluye información detallada de cada usuario propietario de los análisis.
    """
    try:
        # Obtener todos los datos del servicio
        service = AnalisisSuelosValidadosService(db)
        resultado = service.obtener_todos_los_validados_detallados()
        
        if not resultado["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=resultado["message"]
            )
        
        # Crear el archivo Excel
        excel_service = ExcelExportValidadosService()
        excel_buffer = excel_service.exportar_todos_validados_a_excel(
            datos=resultado["datos"],
            total_usuarios=resultado.get("total_usuarios", 0),
            usuarios_con_validados=resultado.get("usuarios_con_validados", [])
        )
        
        if not excel_buffer:
            # Si falla la exportación completa, intentar con versión simple
            try:
                excel_buffer = excel_service.crear_excel_simple_todos(
                    datos=resultado["datos"]
                )
            except Exception as simple_error:
                print(f"Error también en Excel simple de todos los validados: {str(simple_error)}")
                
            if not excel_buffer:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error al generar el archivo Excel"
                )
        
        # Configurar respuesta de descarga
        excel_buffer.seek(0)
        
        # Nombre del archivo con información general
        fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"Todos_Analisis_Validados_{resultado.get('total_usuarios', 0)}_usuarios_{resultado.get('total_registros', 0)}_registros_{fecha_actual}.xlsx"
        
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

# ENDPOINT 7: Obtener vista previa de análisis validados de un usuario (opcional)
@router.get("/validados/{correo_usuario}", response_model=AnalisisValidadosResponse)
def obtener_validados_por_usuario(
    correo_usuario: str,
    db: Session = Depends(get_db),
    limite: int = 100
):
    """
    Obtiene todos los análisis validados de un usuario específico.
    Útil para vista previa antes de exportar a Excel.
    
    Args:
        correo_usuario: Correo del usuario
        limite: Número máximo de registros a devolver (por defecto 100)
    """
    try:
        service = AnalisisSuelosValidadosService(db)
        resultado = service.obtener_validados_detallados_por_correo(correo_usuario)
        
        if not resultado["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=resultado["message"]
            )
        
        # Limitar los datos si es necesario
        datos_limitados = resultado["datos"][:limite] if limite > 0 else resultado["datos"]
        
        return AnalisisValidadosResponse(
            success=resultado["success"],
            message=resultado["message"],
            total_registros=resultado["total_registros"],
            usuario_info=resultado.get("usuario_info"),
            datos=datos_limitados
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

# ENDPOINT 8: Obtener vista previa de todos los análisis validados (opcional)
@router.get("/validados", response_model=TodosAnalisisValidadosResponse)
def obtener_todos_los_validados(
    db: Session = Depends(get_db),
    limite: int = 100
):
    """
    Obtiene todos los análisis validados de todos los usuarios.
    Útil para vista previa antes de exportar a Excel.
    
    Args:
        limite: Número máximo de registros a devolver (por defecto 100)
    """
    try:
        service = AnalisisSuelosValidadosService(db)
        resultado = service.obtener_todos_los_validados_detallados()
        
        if not resultado["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=resultado["message"]
            )
        
        # Limitar los datos si es necesario
        datos_limitados = resultado["datos"][:limite] if limite > 0 else resultado["datos"]
        
        return TodosAnalisisValidadosResponse(
            success=resultado["success"],
            message=resultado["message"],
            total_registros=resultado["total_registros"],
            total_usuarios=resultado["total_usuarios"],
            usuarios_con_validados=resultado.get("usuarios_con_validados", []),
            datos=datos_limitados
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )