# Actualización del route - src/AnalisisSuelosPendientes/interfaces/analisis_suelos_router.py

from datetime import datetime
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List
from src.AnalisisSuelosPendientes.infrastructure.analisis_suelos_model import AnalisisSuelosPendientes
from src.core.database import get_db
from src.AnalisisSuelosPendientes.application.analisis_suelos_service import AnalisisSuelosService
from src.AnalisisSuelosPendientes.application.usuarios_pendientes_service import UsuariosPendientesService
from src.AnalisisSuelosPendientes.application.eliminar_pendientes_service import EliminarPendientesService
from src.AnalisisSuelosPendientes.application.analisis_suelos_schemas import EliminarPendientesResponse
from src.AnalisisSuelosPendientes.application.usuarios_validados_service import UsuariosValidadosService
from src.AnalisisSuelosPendientes.application.analisis_suelos_schemas import (
    AnalisisSuelosResponse, 
    AnalisisSuelosCreate, 
    UploadResponse,
    ComentarioInvalidoCreate,
    ComentarioInvalidoResponse,
    ResumenUsuariosPendientesResponse,
    ResumenUsuariosValidadosResponse,
    AnalisisValidadosPorCorreoResponse,
)
from fastapi.responses import StreamingResponse



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


@router.post("/comentario-invalido", response_model=ComentarioInvalidoResponse)
def crear_comentario_invalido(
    comentario_data: ComentarioInvalidoCreate,
    db: Session = Depends(get_db)
):
    """
    Crea un comentario inválido para todos los análisis de suelos pendientes de un usuario.
    
    **Restricciones:**
    - Solo administradores (rol_id = 1) pueden usar este endpoint
    - El comentario se aplica a TODOS los análisis pendientes del usuario
    
    **Parámetros:**
    - admin_id: ID del administrador que crea el comentario
    - correo_usuario: Correo del usuario al que se le asignará el comentario
    - comentario_invalido: Texto del comentario inválido
    """
    try:
        resultado = AnalisisSuelosService.crear_comentario_invalido(
            db=db,
            admin_id=comentario_data.admin_id,
            correo_usuario=comentario_data.correo_usuario,
            comentario_invalido=comentario_data.comentario_invalido
        )
        
        return ComentarioInvalidoResponse(**resultado)
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
    
@router.get("/usuarios-con-pendientes", response_model=ResumenUsuariosPendientesResponse)
def obtener_usuarios_con_pendientes(
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los usuarios que tienen análisis de suelos pendientes.
    
    **Retorna:**
    - Lista completa de usuarios con análisis pendientes
    - Total de registros pendientes por usuario
    - Municipios involucrados por usuario
    - Fecha del último análisis de cada usuario
    
    **Ordenado por:** Usuarios con más registros pendientes primero
    """
    try:
        resultado = UsuariosPendientesService.get_usuarios_con_pendientes(db)
        return ResumenUsuariosPendientesResponse(**resultado)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo usuarios con pendientes: {str(e)}")


@router.get("/descargar-excel/{user_id}")
def descargar_excel_usuario_pendientes(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Descarga un archivo Excel con todos los análisis pendientes de un usuario específico.
    
    **Funcionalidades:**
    - Exporta TODOS los registros pendientes del usuario
    - Incluye hoja de resumen con información del usuario
    - Formato Excel (.xlsx) optimizado con columnas auto-ajustadas
    - Ordenado por fecha de creación (más recientes primero)
    
    **Parámetros:**
    - user_id: ID del usuario cuyos datos pendientes se descargarán
    
    **Retorna:**
    - Archivo Excel como descarga directa
    - Nombre de archivo incluye ID del usuario y fecha de generación
    
    **Errores posibles:**
    - 404: Usuario no encontrado
    - 400: Usuario no tiene análisis pendientes
    - 500: Error generando el archivo
    """
    try:
        # Generar Excel
        excel_bytes = UsuariosPendientesService.generar_excel_por_usuario(db, user_id)
        
        # Obtener información del usuario para el nombre del archivo
        from src.Users.infrastructure.users_model import Users
        usuario = db.query(Users).filter(Users.ID_user == user_id).first()
        
        if not usuario:
            raise HTTPException(status_code=404, detail=f"Usuario con ID {user_id} no encontrado")
        
        # Crear nombre de archiv
        nombre_usuario = f"{usuario.nombre or ''}{usuario.apellido or ''}".replace(" ", "_")
        if not nombre_usuario.strip():
            nombre_usuario = usuario.correo.split('@')[0]
        
        fecha_actual = datetime.now().strftime('%d%m%Y_%H%M')
        nombre_archivo = f"analisis_pendientes_{nombre_usuario}_{user_id}_{fecha_actual}.xlsx"
        
        # Crear respuesta de streaming
        def iter_excel():
            yield excel_bytes
        
        headers = {
            'Content-Disposition': f'attachment; filename="{nombre_archivo}"',
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        
        return StreamingResponse(
            io.BytesIO(excel_bytes), 
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers=headers
        )
        
    except ValueError as ve:
        if "no tiene análisis pendientes" in str(ve):
            raise HTTPException(status_code=400, detail=str(ve))
        else:
            raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando archivo Excel: {str(e)}")


@router.delete("/eliminar-pendientes/{correo_usuario}", response_model=EliminarPendientesResponse)
def eliminar_analisis_pendientes_por_usuario(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Elimina TODOS los análisis de suelos pendientes de un usuario específico.
    
    **ADVERTENCIA IMPORTANTE:**
    - Este endpoint elimina PERMANENTEMENTE todos los registros pendientes del usuario
    - La acción NO se puede deshacer
    - Solo elimina registros con estatus 'pendiente'
    
    **Parámetros:**
    - correo_usuario: Correo electrónico del usuario cuyos pendientes se eliminarán
    
    **Casos de uso:**
    - Limpiar registros pendientes de un usuario específico
    - Eliminar datos antes de resubir información corregida
    - Mantenimiento de base de datos
    
    **Retorna:**
    - Confirmación de eliminación
    - Número de registros eliminados
    - Información del usuario afectado
    - Fecha y hora de la eliminación
    
    **Códigos de respuesta:**
    - 200: Eliminación exitosa (incluso si no había registros)
    - 404: Usuario no encontrado
    - 500: Error interno del servidor
    """
    try:
        resultado = EliminarPendientesService.eliminar_pendientes_por_usuario(
            db=db,
            correo_usuario=correo_usuario
        )
        
        return EliminarPendientesResponse(**resultado)
        
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
    
@router.get("/usuarios-con-validados", response_model=ResumenUsuariosValidadosResponse)
def obtener_usuarios_con_validados(
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los usuarios que tienen análisis de suelos validados.
    
    **Retorna:**
    - Lista completa de usuarios con análisis validados
    - Total de registros validados por usuario
    - Municipios involucrados por usuario
    - Fecha del último análisis validado de cada usuario
    
    **Ordenado por:** Usuarios con más registros validados primero
    
    **Diferencias con pendientes:**
    - Solo incluye análisis con estatus 'validado'
    - Muestra usuarios que ya completaron el proceso de validación
    - Útil para reportes y seguimiento de análisis completados
    """
    try:
        resultado = UsuariosValidadosService.get_usuarios_con_validados(db)
        return ResumenUsuariosValidadosResponse(**resultado)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo usuarios con validados: {str(e)}")


@router.get("/validados-por-correo/{correo_usuario}", response_model=AnalisisValidadosPorCorreoResponse)
def obtener_validados_por_correo(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los análisis validados de un usuario específico usando su correo electrónico.
    
    **Parámetros:**
    - correo_usuario: Correo electrónico del usuario a consultar
    
    **Retorna:**
    - Información completa del usuario
    - Lista detallada de todos sus análisis validados
    - Municipios donde tiene análisis validados
    - Fecha del análisis validado más reciente
    - Detalles de cada análisis (ID, fecha, municipio, cultivo, técnico, etc.)
    
    **Casos de uso:**
    - Consultar historial de validaciones de un usuario
    - Verificar análisis completados por usuario
    - Generar reportes específicos por usuario
    - Seguimiento de trabajo completado
    
    **Respuesta cuando no hay validados:**
    - Retorna información del usuario con listas vacías
    - Message explicativo de que no tiene validados
    - total_validados = 0
    """
    try:
        resultado = UsuariosValidadosService.get_analisis_validados_por_correo(db, correo_usuario)
        return AnalisisValidadosPorCorreoResponse(**resultado)
        
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo análisis validados: {str(e)}")


