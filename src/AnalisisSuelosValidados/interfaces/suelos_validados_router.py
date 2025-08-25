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
    nombre_archivo: str = None

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
    resultado = service.validar_analisis_por_correo(request.correo_usuario, request.nombre_archivo)
    
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
        
class EliminarValidadosResponse(BaseModel):
    success: bool
    message: str
    usuario: str = None
    usuario_id: int = None
    eliminados: int

# NUEVO ENDPOINT DELETE para eliminar análisis de suelos validados
@router.delete("/validados/eliminar/{correo_usuario}", response_model=EliminarValidadosResponse)
def eliminar_validados_usuario(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Elimina TODOS los análisis de suelos validados de un usuario por su correo.
    
    Args:
        correo_usuario (str): Correo electrónico del usuario
        
    Returns:
        EliminarValidadosResponse: Resultado de la eliminación
        
    Raises:
        HTTPException: Si ocurre un error durante la eliminación
    """
    try:
        print(f"=== ENDPOINT DELETE SUELOS VALIDADOS PARA: {correo_usuario} ===")
        
        # Crear instancia del servicio y llamar al método de eliminación
        service = AnalisisSuelosValidadosService(db)
        resultado = service.eliminar_analisis_validados_por_correo(correo_usuario)
        
        if not resultado["success"]:
            # Si el usuario no existe, devolver 404
            if "no encontrado" in resultado["message"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=resultado["message"]
                )
            else:
                # Otros errores, devolver 500
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=resultado["message"]
                )
        
        # Eliminación exitosa
        print(f"✅ Eliminación de suelos validados exitosa: {resultado['eliminados']} registros")
        
        return EliminarValidadosResponse(
            success=resultado["success"],
            message=resultado["message"],
            usuario=resultado.get("usuario"),
            usuario_id=resultado.get("usuario_id"),
            eliminados=resultado["eliminados"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error crítico en endpoint delete suelos validados: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar análisis de suelos validados del usuario: {str(e)}"
        )
        
@router.get("/validados/exportar-excel-usuario-archivo/{user_id}")
def exportar_validados_por_usuario_y_archivo(
    user_id: int,
    nombre_archivo: str,
    db: Session = Depends(get_db)
):
    """
    Exporta análisis validados de un usuario específico filtrados por nombre de archivo.
    
    Args:
        user_id (int): ID del usuario
        nombre_archivo (str): Nombre del archivo para filtrar (query parameter)
        
    Returns:
        StreamingResponse: Archivo Excel con los datos filtrados
    """
    try:
        # Obtener datos del servicio
        service = AnalisisSuelosValidadosService(db)
        resultado = service.obtener_validados_por_user_id_y_archivo(user_id, nombre_archivo)
        
        if not resultado["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=resultado["message"]
            )
        
        # Crear el archivo Excel
        excel_service = ExcelExportValidadosService()
        excel_buffer = excel_service.exportar_validados_a_excel(
            datos=resultado["datos"],
            usuario_info=resultado["usuario_info"],
            correo_usuario=resultado["usuario_info"]["correo"]
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
        
        # Nombre del archivo con información específica
        fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
        usuario_info = resultado["usuario_info"]
        nombre_usuario = f"{usuario_info.get('nombre', '')}{usuario_info.get('apellido', '')}"
        nombre_descarga = f"Validados_Usuario{user_id}_{nombre_usuario}_{nombre_archivo}_{fecha_actual}.xlsx"
        
        response = StreamingResponse(
            io.BytesIO(excel_buffer.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={nombre_descarga}"
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