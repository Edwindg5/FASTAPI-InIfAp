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
    VerificarComentariosRequest,
    VerificarComentariosResponse,
    ResumenUsuariosPendientesResponse,
    EstadisticasGeneralesResponse,
    ResumenUsuariosValidadosResponse,
    AnalisisValidadosPorCorreoResponse,
    EstadisticasValidadosResponse
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


# NUEVO ENDPOINT - Verificar y procesar comentarios inválidos
@router.post("/comentarios/verificar", response_model=VerificarComentariosResponse)
def verificar_comentarios_invalidos(
    request: VerificarComentariosRequest,
    db: Session = Depends(get_db)
):
    """
    Verifica si un usuario tiene comentarios inválidos y permite marcarlos como recibidos.
    
    **Acciones disponibles:**
    - **'verificar'**: Solo verifica si hay comentarios inválidos y los muestra
    - **'recibido'**: Marca los comentarios como recibidos y elimina AUTOMÁTICAMENTE todos los registros con comentarios
    
    **Importante:** 
    - La acción 'recibido' eliminará permanentemente todos los análisis de suelos que tengan comentarios inválidos
    - Esta acción no se puede deshacer
    
    **Parámetros:**
    - correo_usuario: Correo del usuario a verificar
    - accion: 'verificar' o 'recibido'
    """
    try:
        resultado = AnalisisSuelosService.verificar_y_procesar_comentarios(
            db=db,
            correo_usuario=request.correo_usuario,
            accion=request.accion
        )
        
        return VerificarComentariosResponse(**resultado)
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


# ENDPOINT ADICIONAL - Obtener comentarios por correo (solo verificar, más simple)
@router.get("/comentarios/{correo_usuario}", response_model=VerificarComentariosResponse)
def obtener_comentarios_invalidos(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint simplificado para solo verificar comentarios inválidos de un usuario.
    
    **Uso:** GET /analisis-suelos-pendientes/comentarios/usuario@ejemplo.com
    
    **Parámetros:**
    - correo_usuario: Correo del usuario a verificar
    
    **Retorna:**
    - Lista de comentarios inválidos del usuario
    - Total de registros afectados
    - Estado de los comentarios
    """
    try:
        resultado = AnalisisSuelosService.verificar_y_procesar_comentarios(
            db=db,
            correo_usuario=correo_usuario,
            accion="verificar"
        )
        
        return VerificarComentariosResponse(**resultado)
        
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")


# ENDPOINT ADICIONAL - Eliminar comentarios por correo (acción directa)
@router.delete("/comentarios/{correo_usuario}", response_model=VerificarComentariosResponse)
def eliminar_comentarios_invalidos(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint directo para eliminar comentarios inválidos y sus registros asociados.
    
    **Uso:** DELETE /analisis-suelos-pendientes/comentarios/usuario@ejemplo.com
    
    **ADVERTENCIA:** 
    - Este endpoint elimina PERMANENTEMENTE todos los registros con comentarios inválidos
    - La acción no se puede deshacer
    
    **Parámetros:**
    - correo_usuario: Correo del usuario cuyos comentarios se eliminarán
    """
    try:
        resultado = AnalisisSuelosService.verificar_y_procesar_comentarios(
            db=db,
            correo_usuario=correo_usuario,
            accion="recibido"
        )
        
        return VerificarComentariosResponse(**resultado)
        
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
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


@router.get("/estadisticas-validados", response_model=EstadisticasValidadosResponse)
def obtener_estadisticas_validados(
    db: Session = Depends(get_db)
):
    """
    Obtiene estadísticas generales del sistema de análisis de suelos validados.
    
    **Incluye:**
    - Total de análisis validados en el sistema
    - Total de usuarios con análisis validados
    - Top 10 municipios más frecuentes en validados
    - Top 10 usuarios con más análisis validados
    - Fecha de la consulta
    
    **Útil para:**
    - Dashboard de administración
    - Reportes ejecutivos
    - Seguimiento de productividad
    - Análisis de tendencias geográficas
    - Identificar usuarios más activos
    """
    try:
        estadisticas = UsuariosValidadosService.get_estadisticas_validados(db)
        return EstadisticasValidadosResponse(**estadisticas)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas de validados: {str(e)}")


# ENDPOINT ADICIONAL - Verificar si un usuario tiene validados
@router.get("/verificar-validados/{correo_usuario}")
def verificar_usuario_tiene_validados(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint simple para verificar si un usuario tiene análisis validados.
    
    **Uso:** Para validaciones rápidas o componentes frontend
    
    **Parámetros:**
    - correo_usuario: Correo del usuario a verificar
    
    **Retorna:**
    - tiene_validados: boolean
    - total_validados: número de registros
    - user_id: ID del usuario
    - message: mensaje descriptivo
    """
    try:
        # Verificar que el usuario exista
        from src.Users.infrastructure.users_model import Users
        usuario = db.query(Users).filter(Users.correo == correo_usuario).first()
        
        if not usuario:
            raise HTTPException(status_code=404, detail=f"Usuario con correo {correo_usuario} no encontrado")
        
        total_validados = db.query(AnalisisSuelosPendientes).filter(
            AnalisisSuelosPendientes.user_id_FK == usuario.ID_user,
            AnalisisSuelosPendientes.estatus == 'validado'
        ).count()
        
        tiene_validados = total_validados > 0
        
        mensaje = f"Usuario {correo_usuario} {'tiene' if tiene_validados else 'no tiene'} análisis validados"
        if tiene_validados:
            mensaje += f" (Total: {total_validados})"
        
        return {
            "correo_usuario": correo_usuario,
            "user_id": usuario.ID_user,
            "tiene_validados": tiene_validados,
            "total_validados": total_validados,
            "message": mensaje
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verificando validados: {str(e)}")


