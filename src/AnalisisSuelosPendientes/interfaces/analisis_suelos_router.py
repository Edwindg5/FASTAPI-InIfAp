# Actualización del router - src/AnalisisSuelosPendientes/interfaces/analisis_suelos_router.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List
from src.core.database import get_db
from src.AnalisisSuelosPendientes.application.analisis_suelos_service import AnalisisSuelosService
from src.AnalisisSuelosPendientes.application.analisis_suelos_schemas import (
    AnalisisSuelosResponse, 
    AnalisisSuelosCreate, 
    UploadResponse,
    ComentarioInvalidoCreate,
    ComentarioInvalidoResponse,
    VerificarComentariosRequest,
    VerificarComentariosResponse
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