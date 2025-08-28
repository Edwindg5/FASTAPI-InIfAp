# Actualización del rout - src/AnalisisSuelosPendientes/interfaces/analisis_suelos_router.py

from datetime import datetime
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List
from src.AnalisisSuelosPendientes.application.archivos_pendientes_service import ArchivosPendientesService
from src.AnalisisSuelosPendientes.infrastructure.analisis_suelos_model import AnalisisSuelosPendientes
from src.core.database import get_db
from src.AnalisisSuelosPendientes.application.analisis_suelos_service import AnalisisSuelosService
from src.AnalisisSuelosPendientes.application.usuarios_pendientes_service import UsuariosPendientesService
from src.AnalisisSuelosPendientes.application.eliminar_pendientes_service import EliminarPendientesService
from src.AnalisisSuelosPendientes.application.comentario_invalido_service import ComentarioInvalidoService
from src.AnalisisSuelosPendientes.application.archivos_usuario_service import ArchivosUsuarioService
from src.AnalisisSuelosPendientes.application.analisis_suelos_schemas import EliminarPendientesResponse
from src.AnalisisSuelosPendientes.application.usuarios_validados_service import UsuariosValidadosService
from src.AnalisisSuelosPendientes.application.analisis_suelos_schemas import (
    AnalisisSuelosResponse, 
    AnalisisSuelosCreate, 
    UploadResponse,
    ComentarioInvalidoCreate,
    ComentarioInvalidoResponse,
    ResumenUsuariosPendientesResponse,
    ResumenUsuariosValidadosSimpleResponse,
    PendientesPorArchivoResponse,
    ResumenArchivosPendientesResponse,
    PendientesPorUsuarioArchivoResponse,
    ObtenerComentarioInvalidoResponse,
    ArchivosUsuarioResponse
    
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
    nombre_archivo: str = Query(..., description="Nombre del archivo para registrar en BD"),  # NUEVA LÍNEA
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

        # Procesar el archivo - AGREGADO nombre_archivo
        result = AnalisisSuelosService.process_excel_file(
            file_content=file_content,
            user_id=user_id,
            nombre_archivo=nombre_archivo,  # NUEVA LÍNEA
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
    nombre_archivo: str = Query(None, description="Nombre del archivo específico a filtrar (opcional)"),
    db: Session = Depends(get_db)
):
    """
    Descarga un archivo Excel con los análisis pendientes de un usuario específico.
    Opcionalmente filtrado por nombre de archivo.
    
    **Funcionalidades:**
    - Exporta registros pendientes del usuario
    - Si se especifica nombre_archivo, solo exporta registros de ese archivo
    - Si no se especifica nombre_archivo, exporta TODOS los registros pendientes del usuario
    - Incluye hoja de resumen con información del usuario
    - Formato Excel (.xlsx) optimizado con columnas auto-ajustadas
    - Ordenado por fecha de creación (más recientes primero)
    
    **Parámetros:**
    - user_id: ID del usuario cuyos datos pendientes se descargarán
    - nombre_archivo: (Opcional) Nombre específico del archivo a filtrar
    
    **Retorna:**
    - Archivo Excel como descarga directa
    - Nombre de archivo incluye ID del usuario y fecha de generación
    
    **Errores posibles:**
    - 404: Usuario no encontrado
    - 400: Usuario no tiene análisis pendientes (o no tiene del archivo especificado)
    - 500: Error generando el archivo
    """
    try:
        # Generar Excel con filtro opcional por archivo
        excel_bytes = UsuariosPendientesService.generar_excel_por_usuario(db, user_id, nombre_archivo)
        
        # Obtener información del usuario para el nombre del archivo
        from src.Users.infrastructure.users_model import Users
        usuario = db.query(Users).filter(Users.ID_user == user_id).first()
        
        if not usuario:
            raise HTTPException(status_code=404, detail=f"Usuario con ID {user_id} no encontrado")
        
        # Crear nombre de archivo
        nombre_usuario = f"{usuario.nombre or ''}{usuario.apellido or ''}".replace(" ", "_")
        if not nombre_usuario.strip():
            nombre_usuario = usuario.correo.split('@')[0]
        
        fecha_actual = datetime.now().strftime('%d%m%Y_%H%M')
        
        # Incluir nombre del archivo en el nombre de descarga si se especificó
        archivo_parte = f"_{nombre_archivo.replace('.xlsx', '').replace('.xls', '')}" if nombre_archivo else "_todos"
        nombre_descarga = f"analisis_pendientes_{nombre_usuario}_{user_id}{archivo_parte}_{fecha_actual}.xlsx"
        
        # Crear respuesta de streaming
        headers = {
            'Content-Disposition': f'attachment; filename="{nombre_descarga}"',
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
    
@router.get("/usuarios-con-validados", response_model=ResumenUsuariosValidadosSimpleResponse)
def obtener_usuarios_con_validados(
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los usuarios que tienen análisis de suelos validados en formato simplificado.
    
    **Retorna:**
    - Lista simplificada con: nombre_usuario, estatus, fecha, nombre_archivo
    - Una entrada por cada archivo validado (no agrupado por usuario)
    - Ordenado por nombre de usuario y nombre de archivo
    
    **Formato de respuesta:**
    - nombre_usuario: Nombre completo del usuario
    - estatus: Siempre 'validado'
    - fecha: Fecha de validación del archivo
    - nombre_archivo: Nombre del archivo Excel procesado
    """
    try:
        resultado = UsuariosValidadosService.get_usuarios_con_validados(db)
        return ResumenUsuariosValidadosSimpleResponse(**resultado)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo usuarios con validados: {str(e)}")

@router.get("/archivos-con-pendientes", response_model=ResumenArchivosPendientesResponse)
def obtener_archivos_con_pendientes(
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los archivos únicos que tienen análisis de suelos pendientes.
    
    **Retorna:**
    - Lista de archivos únicos (no duplicados por usuario)
    - Una entrada por cada archivo que tiene registros pendientes
    - Información del usuario, fecha y nombre del archivo
    
    **Formato de respuesta:**
    - nombre_usuario: Nombre completo del usuario
    - estatus: Siempre 'pendiente'
    - fecha: Fecha más reciente del archivo
    - nombre_archivo: Nombre del archivo Excel procesado
    """
    try:
        resultado = ArchivosPendientesService.get_archivos_con_pendientes(db)
        return ResumenArchivosPendientesResponse(**resultado)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo archivos con pendientes: {str(e)}")

@router.get("/pendientes-por-usuario-archivo", response_model=PendientesPorUsuarioArchivoResponse)
def obtener_pendientes_por_usuario_archivo(
    correo_usuario: str = Query(..., description="Correo electrónico del usuario"),
    nombre_archivo: str = Query(..., description="Nombre del archivo a consultar"),
    db: Session = Depends(get_db)
):
    """
    Obtiene información específica de pendientes para un usuario y archivo determinado.
    
    **Parámetros:**
    - correo_usuario: Correo electrónico del usuario
    - nombre_archivo: Nombre exacto del archivo a consultar
    
    **Retorna:**
    - Información detallada del usuario y archivo
    - Cantidad exacta de registros pendientes
    - Fecha más reciente de los registros
    
    **Formato de respuesta:**
    - nombre_usuario: Nombre completo del usuario
    - fecha: Fecha más reciente de los registros
    - estatus: Siempre 'pendiente'
    - cantidad_datos: Número total de registros pendientes
    - nombre_archivo: Nombre del archivo consultado
    
    **Códigos de respuesta:**
    - 200: Consulta exitosa
    - 404: Usuario no encontrado o no tiene registros con ese archivo
    - 500: Error interno del servidor
    """
    try:
        resultado = ArchivosPendientesService.get_pendientes_por_usuario_archivo(
            db=db,
            correo_usuario=correo_usuario,
            nombre_archivo=nombre_archivo
        )
        return PendientesPorUsuarioArchivoResponse(**resultado)
        
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
    
    
@router.get("/comentario-invalido/{correo_usuario}", response_model=ObtenerComentarioInvalidoResponse)
def obtener_comentario_invalido(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene el comentario inválido de un usuario específico por su correo electrónico.
    
    **Funcionalidades:**
    - Busca y retorna el comentario inválido asociado al usuario
    - Incluye información del usuario y fecha del comentario
    - Muestra el total de registros afectados por el comentario
    
    **Parámetros:**
    - correo_usuario: Correo electrónico del usuario a consultar
    
    **Retorna:**
    - user_id: ID del usuario
    - correo_usuario: Correo electrónico del usuario
    - nombre_usuario: Nombre completo del usuario
    - comentario_invalido: Contenido del comentario inválido
    - fecha_comentario: Fecha cuando se creó el comentario
    - total_registros_afectados: Número total de registros con este comentario
    
    **Códigos de respuesta:**
    - 200: Comentario encontrado exitosamente
    - 404: Usuario no encontrado o no tiene comentarios inválidos
    - 500: Error interno del servidor
    """
    try:
        resultado = ComentarioInvalidoService.obtener_comentario_por_correo(
            db=db,
            correo_usuario=correo_usuario
        )
        
        return ObtenerComentarioInvalidoResponse(**resultado)
        
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")
    
@router.get("/mis-archivos-pendientes", response_model=ArchivosUsuarioResponse)
def obtener_archivos_pendientes_usuario(
    correo_usuario: str = Query(..., description="Correo electrónico del usuario"),
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los archivos únicos con estatus pendiente de un usuario específico.
    
    **Funcionalidades:**
    - Busca archivos únicos por correo de usuario (sin duplicados)
    - Solo muestra archivos con estatus 'pendiente'
    - Agrupa registros por nombre_archivo único
    - Incluye estadísticas de cada archivo
    - Ordenado por fecha de última modificación (más recientes primero)
    
    **Parámetros:**
    - correo_usuario: Correo electrónico del usuario a consultar
    
    **Información retornada para cada archivo:**
    - nombre_archivo: Nombre único del archivo Excel subido
    - total_registros: Cantidad total de registros pendientes en ese archivo
    - fecha_subida: Primera vez que se subieron datos de este archivo
    - ultima_modificacion: Última vez que se modificaron datos de este archivo
    - estatus: Siempre 'pendiente'
    
    **Información general del usuario:**
    - correo_usuario: Correo consultado
    - nombre_usuario: Nombre completo del usuario
    - user_id: ID interno del usuario
    - total_archivos_unicos: Cantidad de archivos únicos con pendientes
    - total_registros_pendientes: Suma total de todos los registros pendientes
    - fecha_consulta: Momento de la consulta
    
    **Casos de uso:**
    - Usuario revisa qué archivos tiene pendientes
    - Administración verifica archivos pendientes de un usuario específico
    - Seguimiento de archivos antes de validación
    
    **Códigos de respuesta:**
    - 200: Consulta exitosa (puede retornar lista vacía si no hay archivos pendientes)
    - 404: Usuario no encontrado
    - 500: Error interno del servidor
    """
    try:
        resultado = ArchivosUsuarioService.get_archivos_pendientes_por_correo(
            db=db,
            correo_usuario=correo_usuario
        )
        
        return ArchivosUsuarioResponse(**resultado)
        
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")