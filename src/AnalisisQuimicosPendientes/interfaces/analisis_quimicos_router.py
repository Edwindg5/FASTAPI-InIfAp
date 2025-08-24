# src/AnalisisQuimicosPendientes/interfaces/analisis_quimicos_router.py
from fastapi import APIRouter, UploadFile, Depends, Form, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.AnalisisQuimicosPendientes.application.analisis_quimicos_service import procesar_excel_y_guardar
from src.AnalisisQuimicosPendientes.application.usuario_service import (
    obtener_usuarios_con_datos_pendientes,
    generar_excel_usuario,
    obtener_info_usuario_para_descarga
)
from src.AnalisisQuimicosPendientes.infrastructure.analisis_quimicos_model import AnalisisQuimicosPendientes
from src.Users.infrastructure.users_model import Users
from src.rol.infrastructure.rol_model import Rol  # Ajusta la ruta según tu estructura
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import io

router = APIRouter(prefix="/analisis-quimicos", tags=["Análisis Químicos"])

# ======================= MODELOS PYDANTIC =======================

class AgregarComentarioInvalidoRequest(BaseModel):
    correo_usuario: EmailStr  # Correo del usuario que recibirá el comentario
    comentario_invalido: str

class ComentarioInvalidoResponse(BaseModel):
    tiene_comentario: bool
    comentario_invalido: Optional[str] = None
    mensaje: str

class UsuarioConDatosResponse(BaseModel):
    user_id: int
    nombre_usuario: str
    correo: str
    fecha_creacion: Optional[str]
    ultima_actualizacion: Optional[str]
    estatus: str
    total_registros: int
    registros_pendientes: int
    registros_invalidados: int
    nombres_archivos: List[str] = []  # ¡NUEVO CAMPO!

class ListaUsuariosResponse(BaseModel):
    usuarios: List[UsuarioConDatosResponse]
    total_usuarios: int
    mensaje: str

# ======================= HELPER FUNCTIONS =======================

def _verificar_es_administrador(user_id_admin: int, db: Session) -> bool:
    """
    Verifica si el usuario es administrador (id_rol = 1)
    """
    usuario = db.query(Users).filter(Users.ID_user == user_id_admin).first()
    if not usuario:
        return False
    return usuario.rol_id_FK == 1

def _obtener_usuario_por_correo(correo: str, db: Session) -> Optional[Users]:
    """
    Obtiene un usuario por su correo electrónico
    """
    return db.query(Users).filter(Users.correo == correo.lower().strip()).first()

# ======================= ENDPOINTS =======================

@router.post("/upload-excel/")
async def upload_excel(
    file: UploadFile, 
    correo_usuario: str = Form(..., description="Correo electrónico del usuario que sube el archivo"),
    nombre_archivo: str = Form(..., description="Nombre descriptivo para el archivo (se guardará en la BD)"),
    db: Session = Depends(get_db)
):
    """
    Procesa y almacena un archivo Excel con datos de análisis químicos.
    
    Args:
        file: Archivo Excel a procesar
        correo_usuario: Correo electrónico del usuario (debe existir en la tabla users)
        nombre_archivo: Nombre descriptivo del archivo (se registra en la BD para referencia)
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
    
    # Validar que el nombre del archivo no esté vacío
    if not nombre_archivo or not nombre_archivo.strip():
        raise HTTPException(
            status_code=400, 
            detail="El nombre del archivo es obligatorio"
        )
    
    try:
        file_bytes = await file.read()
        
        # ¡NUEVO PARÁMETRO! - Pasar nombre_archivo al servicio
        resumen = procesar_excel_y_guardar(
            file_bytes, 
            correo_usuario.strip(), 
            nombre_archivo.strip(),  # ¡NUEVO!
            db
        )
        
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

@router.post("/agregar-comentario-invalido/")
async def agregar_comentario_invalido(
    user_id_administrador: int = Form(..., description="ID del administrador"),
    correo_usuario: str = Form(..., description="Correo del usuario que recibirá el comentario"),
    comentario_invalido: str = Form(..., description="Comentario inválido a agregar"),
    db: Session = Depends(get_db)
):
    """
    Permite al administrador agregar un comentario inválido a un usuario específico.
    Solo usuarios con rol de Administrador (id_rol = 1) pueden usar este endpoint.
    
    Args:
        user_id_administrador: ID del administrador que agrega el comentario
        correo_usuario: Correo del usuario que recibirá el comentario
        comentario_invalido: El comentario inválido a agregar
        db: Sesión de base de datos
    
    Returns:
        Confirmación de que el comentario fue agregado
    """
    try:
        # 1. Verificar que quien hace la petición es administrador
        if not _verificar_es_administrador(user_id_administrador, db):
            raise HTTPException(
                status_code=403,
                detail="Solo los administradores pueden agregar comentarios inválidos"
            )
        
        # 2. Verificar que el usuario objetivo existe
        usuario_objetivo = _obtener_usuario_por_correo(correo_usuario, db)
        if not usuario_objetivo:
            raise HTTPException(
                status_code=404,
                detail=f"Usuario con correo '{correo_usuario}' no encontrado"
            )
        
        # 3. Validar que el comentario no esté vacío
        comentario = comentario_invalido.strip()
        if not comentario:
            raise HTTPException(
                status_code=400,
                detail="El comentario no puede estar vacío"
            )
        
        # 4. Buscar registros del usuario para agregar el comentario
        # Primero intentar registros pendientes
        registros_pendientes = db.query(AnalisisQuimicosPendientes).filter(
            AnalisisQuimicosPendientes.user_id_FK == usuario_objetivo.ID_user,
            AnalisisQuimicosPendientes.estatus == "pendiente"
        ).all()
        
        # Si no hay pendientes, buscar cualquier registro del usuario
        if not registros_pendientes:
            registros_usuario = db.query(AnalisisQuimicosPendientes).filter(
                AnalisisQuimicosPendientes.user_id_FK == usuario_objetivo.ID_user
            ).all()
            
            # Si no hay ningún registro, crear uno nuevo solo para el comentario
            if not registros_usuario:
                nuevo_registro = AnalisisQuimicosPendientes(
                    user_id_FK=usuario_objetivo.ID_user,
                    municipio=None,  # Se puede agregar info básica si se requiere
                    localidad=None,
                    nombre_productor=None,
                    comentario_invalido=comentario,
                    nombre_archivo="comentario_admin.xlsx",  # ¡NUEVO! - Nombre por defecto para comentarios
                    estatus="invalidado"
                )
                db.add(nuevo_registro)
                registros_actualizados = 1
            else:
                # Actualizar todos los registros existentes del usuario
                registros_actualizados = 0
                for registro in registros_usuario:
                    registro.comentario_invalido = comentario
                    registro.estatus = "invalidado"
                    registros_actualizados += 1
        else:
            # 5. Actualizar todos los registros pendientes con el comentario
            registros_actualizados = 0
            for registro in registros_pendientes:
                registro.comentario_invalido = comentario
                registro.estatus = "invalidado"  # Cambiar estatus para indicar que hay un comentario
                registros_actualizados += 1
        
        # 6. Guardar cambios
        db.commit()
        
        # 7. Obtener información del administrador para la respuesta
        admin_info = db.query(Users).filter(Users.ID_user == user_id_administrador).first()
        admin_nombre = f"{admin_info.nombre} {admin_info.apellido}" if admin_info and admin_info.nombre else f"Admin ID: {user_id_administrador}"
        
        # Determinar el tipo de acción realizada
        if not any([
            db.query(AnalisisQuimicosPendientes).filter(
                AnalisisQuimicosPendientes.user_id_FK == usuario_objetivo.ID_user,
                AnalisisQuimicosPendientes.estatus == "pendiente"
            ).first(),
            db.query(AnalisisQuimicosPendientes).filter(
                AnalisisQuimicosPendientes.user_id_FK == usuario_objetivo.ID_user
            ).count() > 1
        ]):
            accion_realizada = "Se creó un nuevo registro para el comentario"
        else:
            accion_realizada = "Se actualizaron registros existentes"
        
        return {
            "success": True,
            "accion_realizada": accion_realizada,
            "usuario_objetivo": correo_usuario,
            "comentario": comentario,
            "registros_actualizados": registros_actualizados,
            "administrador": admin_nombre,
            "admin_id": user_id_administrador
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.post("/verificar-comentario-invalido/")
async def verificar_y_limpiar_comentario_invalido(
    correo_usuario: str = Form(..., description="Correo del usuario"),
    accion: str = Form(..., description="Acción a realizar: 'verificar' o 'recibido'"),
    db: Session = Depends(get_db)
) -> ComentarioInvalidoResponse:
    """
    Verifica si un usuario tiene comentarios inválidos y permite marcarlos como recibidos.
    
    Acciones disponibles:
    - 'verificar': Solo verifica si hay comentarios inválidos
    - 'recibido': Marca los comentarios como recibidos y los elimina
    
    Args:
        correo_usuario: Correo del usuario a verificar
        accion: Acción a realizar ('verificar' o 'recibido')
        db: Sesión de base de datos
    
    Returns:
        Estado de los comentarios inválidos del usuario
    """
    try:
        # 1. Validar acción
        if accion not in ["verificar", "recibido"]:
            raise HTTPException(
                status_code=400,
                detail="Acción debe ser 'verificar' o 'recibido'"
            )
        
        # 2. Verificar que el usuario existe
        usuario = _obtener_usuario_por_correo(correo_usuario, db)
        if not usuario:
            raise HTTPException(
                status_code=404,
                detail=f"Usuario con correo '{correo_usuario}' no encontrado"
            )
        
        # 3. Buscar registros con comentarios inválidos
        registros_con_comentarios = db.query(AnalisisQuimicosPendientes).filter(
            AnalisisQuimicosPendientes.user_id_FK == usuario.ID_user,
            AnalisisQuimicosPendientes.comentario_invalido.isnot(None),
            AnalisisQuimicosPendientes.comentario_invalido != ""
        ).all()
        
        # 4. Si no hay comentarios inválidos
        if not registros_con_comentarios:
            return ComentarioInvalidoResponse(
                tiene_comentario=False,
                comentario_invalido=None,
                mensaje="No tienes comentarios inválidos pendientes"
            )
        
        # 5. Obtener el primer comentario (asumiendo que todos son iguales)
        primer_comentario = registros_con_comentarios[0].comentario_invalido
        
        # 6. Si solo es verificación, devolver el estado actual
        if accion == "verificar":
            return ComentarioInvalidoResponse(
                tiene_comentario=True,
                comentario_invalido=primer_comentario,
                mensaje=f"Tienes {len(registros_con_comentarios)} registro(s) con comentarios inválidos pendientes"
            )
        
        # 7. Si es acción 'recibido', limpiar los comentarios
        elif accion == "recibido":
            registros_limpiados = 0
            registros_eliminados = 0
            
            for registro in registros_con_comentarios:
                # Si el registro solo tiene comentario y no tiene datos de análisis, eliminarlo
                tiene_datos_analisis = any([
                    registro.municipio, registro.localidad, registro.nombre_productor,
                    registro.arcilla, registro.limo, registro.arena, registro.ph, 
                    registro.mo, registro.fosforo, registro.k, registro.mg, registro.ca
                ])
                
                if not tiene_datos_analisis:
                    # Eliminar el registro completo si solo se creó para el comentario
                    db.delete(registro)
                    registros_eliminados += 1
                else:
                    # Solo limpiar el comentario si tiene datos de análisis
                    registro.comentario_invalido = None
                    registro.estatus = "pendiente"  # Regresar a estado pendiente
                    registros_limpiados += 1
            
            # Guardar cambios
            db.commit()
            
            if registros_eliminados > 0 and registros_limpiados > 0:
                mensaje = f"Se eliminaron {registros_eliminados} registro(s) vacío(s) y se limpiaron {registros_limpiados} registro(s) con datos"
            elif registros_eliminados > 0:
                mensaje = f"Se eliminaron {registros_eliminados} registro(s) que solo contenían comentarios"
            else:
                mensaje = f"Comentarios eliminados de {registros_limpiados} registro(s) con datos de análisis"
            
            return ComentarioInvalidoResponse(
                tiene_comentario=False,
                comentario_invalido=None,
                mensaje=mensaje
            )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

# ======================= ENDPOINT PARA USUARIOS CON DATOS PENDIENTES =======================

@router.get("/usuarios-con-datos-pendientes/", response_model=ListaUsuariosResponse)
async def obtener_usuarios_con_datos_pendientes_endpoint(
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los usuarios que tienen registros de análisis químicos pendientes.
    
    Muestra información básica del usuario, fechas de creación, estatus, estadísticas
    de sus registros y nombres de archivos que ha subido. Incluye opción para descargar 
    Excel con todos los datos del usuario.
    
    Args:
        db: Sesión de base de datos
    
    Returns:
        Lista de usuarios con datos pendientes, estadísticas y nombres de archivos
    """
    try:
        usuarios = obtener_usuarios_con_datos_pendientes(db)
        
        # Convertir a formato de respuesta
        usuarios_response = [
            UsuarioConDatosResponse(
                user_id=usuario["user_id"],
                nombre_usuario=usuario["nombre_usuario"],
                correo=usuario["correo"],
                fecha_creacion=usuario["fecha_creacion"],
                ultima_actualizacion=usuario["ultima_actualizacion"],
                estatus=usuario["estatus"],
                total_registros=usuario["total_registros"],
                registros_pendientes=usuario["registros_pendientes"],
                registros_invalidados=usuario["registros_invalidados"],
                nombres_archivos=usuario["nombres_archivos"]  # ¡NUEVO CAMPO!
            )
            for usuario in usuarios
        ]
        
        return ListaUsuariosResponse(
            usuarios=usuarios_response,
            total_usuarios=len(usuarios_response),
            mensaje=f"Se encontraron {len(usuarios_response)} usuario(s) con registros pendientes"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener usuarios con datos pendientes: {str(e)}"
        )

@router.get("/descargar-datos-usuario/{user_id}")
async def descargar_datos_usuario_excel(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Descarga un archivo Excel con todos los datos de análisis químicos de un usuario específico.
    
    Args:
        user_id: ID del usuario del cual descargar los datos
        db: Sesión de base de datos
    
    Returns:
        Archivo Excel con todos los registros del usuario
    """
    try:
        # 1. Verificar que el usuario existe
        info_usuario = obtener_info_usuario_para_descarga(user_id, db)
        if not info_usuario:
            raise HTTPException(
                status_code=404,
                detail=f"Usuario con ID {user_id} no encontrado"
            )
        
        # 2. Verificar que el usuario tiene registros
        if info_usuario["total_registros"] == 0:
            raise HTTPException(
                status_code=404,
                detail=f"El usuario '{info_usuario['nombre_completo']}' no tiene registros de análisis químicos"
            )
        
        # 3. Generar el archivo Excel
        excel_bytes = generar_excel_usuario(user_id, db)
        if not excel_bytes:
            raise HTTPException(
                status_code=500,
                detail="Error al generar el archivo Excel"
            )
        
        # 4. Crear respuesta de descarga
        excel_stream = io.BytesIO(excel_bytes)
        
        headers = {
            'Content-Disposition': f'attachment; filename="{info_usuario["nombre_archivo"]}"',
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al generar descarga: {str(e)}"
        )