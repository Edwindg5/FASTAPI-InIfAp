# src/AnalisisQuimicosValidados/application/eliminar_validados_service.py
from sqlalchemy.orm import Session
from typing import Optional
import traceback

from src.AnalisisQuimicosValidados.infrastructure.analisis_quimicos_validados_model import (
    AnalisisQuimicosValidados,
)
from src.Users.infrastructure.users_model import Users


def eliminar_todos_validados_por_correo(
    correo_usuario: str,
    db: Session
) -> dict:
    """
    Elimina TODOS los análisis químicos validados de un usuario específico por su correo.
    
    Este servicio:
    1. Busca al usuario por su correo electrónico
    2. Encuentra todos sus análisis en la tabla analisis_quimicos_validados  
    3. Los elimina permanentemente de la base de datos
    4. Retorna un resumen de la operación
    
    Args:
        correo_usuario (str): Correo electrónico del usuario
        db (Session): Sesión de base de datos SQLAlchemy
        
    Returns:
        dict: Resultado de la operación con el siguiente formato:
            {
                "success": bool,
                "message": str,
                "usuario": str,
                "usuario_id": int (opcional),
                "eliminados": int,
                "error": str (opcional)
            }
    """
    try:
        print(f"=== INICIANDO ELIMINACIÓN DE ANÁLISIS VALIDADOS ===")
        print(f"Usuario objetivo: {correo_usuario}")
        
        # 1. Validar entrada
        if not correo_usuario or not correo_usuario.strip():
            return {
                "success": False,
                "message": "El correo del usuario es requerido",
                "usuario": correo_usuario,
                "eliminados": 0,
                "error": "Correo vacío o inválido"
            }
        
        correo_normalizado = correo_usuario.strip().lower()
        print(f"Correo normalizado: {correo_normalizado}")
        
        # 2. Buscar usuario por correo electrónico
        usuario = (
            db.query(Users)
            .filter(Users.correo == correo_normalizado)
            .first()
        )
        
        if not usuario:
            print(f"❌ Usuario no encontrado con correo: {correo_normalizado}")
            return {
                "success": False,
                "message": f"No se encontró ningún usuario con el correo '{correo_usuario}'",
                "usuario": correo_usuario,
                "eliminados": 0,
                "error": "Usuario no encontrado"
            }
        
        print(f"✓ Usuario encontrado:")
        print(f"  - ID: {usuario.ID_user}")
        print(f"  - Correo: {usuario.correo}")
        print(f"  - Nombre: {usuario.nombre} {usuario.apellido}")
        
        # 3. Contar análisis validados del usuario
        total_validados = (
            db.query(AnalisisQuimicosValidados)
            .filter(AnalisisQuimicosValidados.user_id_FK == usuario.ID_user)
            .count()
        )
        
        print(f"📊 Análisis validados encontrados: {total_validados}")
        
        # 4. Si no tiene análisis validados, retornar éxito temprano
        if total_validados == 0:
            return {
                "success": True,
                "message": f"El usuario '{correo_usuario}' no tiene análisis químicos validados para eliminar",
                "usuario": correo_usuario,
                "usuario_id": usuario.ID_user,
                "eliminados": 0
            }
        
        # 5. Eliminar todos los análisis validados del usuario
        print("🗑️  Procediendo con la eliminación...")
        
        registros_eliminados = (
            db.query(AnalisisQuimicosValidados)
            .filter(AnalisisQuimicosValidados.user_id_FK == usuario.ID_user)
            .delete(synchronize_session=False)
        )
        
        # 6. Confirmar transacción
        db.commit()
        
        print(f"✅ ELIMINACIÓN COMPLETADA EXITOSAMENTE")
        print(f"   - Usuario: {correo_usuario} (ID: {usuario.ID_user})")
        print(f"   - Registros eliminados: {registros_eliminados}")
        print(f"   - Tabla afectada: analisis_quimicos_validados")
        
        return {
            "success": True,
            "message": f"Se eliminaron exitosamente {registros_eliminados} análisis químicos validados del usuario '{correo_usuario}'",
            "usuario": correo_usuario,
            "usuario_id": usuario.ID_user,
            "eliminados": registros_eliminados,
            "detalles": {
                "tabla_afectada": "analisis_quimicos_validados",
                "campo_filtro": "user_id_FK",
                "valor_filtro": usuario.ID_user
            }
        }
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO EN ELIMINACIÓN:")
        print(f"   - Error: {str(e)}")
        print(f"   - Tipo: {type(e).__name__}")
        print(f"   - Traceback: {traceback.format_exc()}")
        
        # Rollback para garantizar consistencia
        try:
            db.rollback()
            print("🔄 Rollback ejecutado exitosamente")
        except Exception as rollback_error:
            print(f"⚠️  Error durante rollback: {rollback_error}")
        
        return {
            "success": False,
            "message": f"Error interno al eliminar análisis validados: {str(e)}",
            "usuario": correo_usuario,
            "eliminados": 0,
            "error": str(e),
            "tipo_error": type(e).__name__
        }


def verificar_analisis_validados_usuario(
    correo_usuario: str,
    db: Session
) -> dict:
    """
    Verifica cuántos análisis validados tiene un usuario sin eliminarlos.
    Útil para confirmar antes de una eliminación masiva.
    
    Args:
        correo_usuario (str): Correo electrónico del usuario
        db (Session): Sesión de base de datos
        
    Returns:
        dict: Información sobre los análisis validados del usuario
    """
    try:
        print(f"=== VERIFICANDO ANÁLISIS VALIDADOS ===")
        print(f"Usuario: {correo_usuario}")
        
        if not correo_usuario or not correo_usuario.strip():
            return {
                "success": False,
                "message": "Correo del usuario requerido",
                "tiene_datos": False,
                "total_validados": 0
            }
        
        correo_normalizado = correo_usuario.strip().lower()
        
        # Buscar usuario
        usuario = (
            db.query(Users)
            .filter(Users.correo == correo_normalizado)
            .first()
        )
        
        if not usuario:
            return {
                "success": False,
                "message": f"Usuario '{correo_usuario}' no encontrado",
                "tiene_datos": False,
                "total_validados": 0
            }
        
        # Contar análisis validados
        total_validados = (
            db.query(AnalisisQuimicosValidados)
            .filter(AnalisisQuimicosValidados.user_id_FK == usuario.ID_user)
            .count()
        )
        
        # Obtener algunos ejemplos (primeros 3)
        ejemplos = (
            db.query(AnalisisQuimicosValidados)
            .filter(AnalisisQuimicosValidados.user_id_FK == usuario.ID_user)
            .limit(3)
            .all()
        )
        
        ejemplos_info = []
        for ejemplo in ejemplos:
            ejemplos_info.append({
                "id": ejemplo.id,
                "municipio": ejemplo.municipio,
                "localidad": ejemplo.localidad,
                "nombre_productor": ejemplo.nombre_productor,
                "fecha_validacion": ejemplo.fecha_validacion.isoformat() if ejemplo.fecha_validacion else None
            })
        
        return {
            "success": True,
            "message": f"Verificación completada para usuario '{correo_usuario}'",
            "usuario": correo_usuario,
            "usuario_id": usuario.ID_user,
            "tiene_datos": total_validados > 0,
            "total_validados": total_validados,
            "ejemplos": ejemplos_info[:3],
            "puede_eliminar": total_validados > 0
        }
        
    except Exception as e:
        print(f"❌ Error en verificación: {e}")
        return {
            "success": False,
            "message": f"Error al verificar datos: {str(e)}",
            "tiene_datos": False,
            "total_validados": 0,
            "error": str(e)
        }
        
def eliminar_analisis_validados_con_admin(
    correo_usuario: str,
    nombre_archivo: str,
    admin_id: int,
    db: Session,
    user_id_objetivo: int = None
) -> dict:
    """
    Elimina análisis químicos validados con validación de administrador.
    
    Args:
        correo_usuario (str): Correo del usuario (para referencia)
        nombre_archivo (str): Nombre del archivo a eliminar
        admin_id (int): ID del administrador que autoriza
        db (Session): Sesión de base de datos
        user_id_objetivo (int, optional): ID específico del usuario propietario
        
    Returns:
        dict: Resultado de la operación
    """
    try:
        print(f"=== ELIMINACIÓN CON VALIDACIÓN DE ADMIN ===")
        print(f"Correo usuario: {correo_usuario}")
        print(f"Archivo: {nombre_archivo}")
        print(f"Admin ID: {admin_id}")
        print(f"User ID objetivo: {user_id_objetivo}")
        
        # 1. Validar administrador
        admin = db.query(Users).filter(Users.ID_user == admin_id).first()
        if not admin:
            return {
                "success": False,
                "message": f"Administrador con ID {admin_id} no encontrado",
                "eliminados": 0,
                "error": "Admin no encontrado"
            }
        
        # Verificar si es admin (asumiendo que hay un campo role o similar)
        # Ajusta esta validación según tu modelo de usuarios
        print(f"✓ Admin encontrado: {admin.nombre} {admin.apellido} ({admin.correo})")
        
        # 2. Buscar registros por archivo
        registros_archivo = (
            db.query(AnalisisQuimicosValidados)
            .filter(AnalisisQuimicosValidados.nombre_archivo == nombre_archivo.strip())
            .all()
        )
        
        print(f"📊 Total registros con archivo '{nombre_archivo}': {len(registros_archivo)}")
        
        if not registros_archivo:
            return {
                "success": False,
                "message": f"No se encontraron registros con el archivo '{nombre_archivo}'",
                "usuario": correo_usuario,
                "archivo": nombre_archivo,
                "eliminados": 0
            }
        
        # 3. Filtrar por user_id si se especifica
        registros_a_eliminar = registros_archivo
        
        if user_id_objetivo:
            registros_a_eliminar = [
                reg for reg in registros_archivo 
                if reg.user_id_FK == user_id_objetivo
            ]
            print(f"🎯 Registros filtrados por user_id {user_id_objetivo}: {len(registros_a_eliminar)}")
        else:
            # Mostrar todos los user_ids encontrados
            user_ids_encontrados = list(set([reg.user_id_FK for reg in registros_archivo]))
            print(f"🔍 User IDs encontrados en el archivo: {user_ids_encontrados}")
            
            # Si hay múltiples usuarios, pedir especificar
            if len(user_ids_encontrados) > 1:
                return {
                    "success": False,
                    "message": f"El archivo '{nombre_archivo}' contiene registros de múltiples usuarios: {user_ids_encontrados}. Especifica 'user_id_objetivo' en el request.",
                    "usuario": correo_usuario,
                    "archivo": nombre_archivo,
                    "user_ids_encontrados": user_ids_encontrados,
                    "eliminados": 0
                }
        
        if not registros_a_eliminar:
            return {
                "success": False,
                "message": f"No se encontraron registros del archivo '{nombre_archivo}' para el user_id especificado",
                "usuario": correo_usuario,
                "archivo": nombre_archivo,
                "eliminados": 0
            }
        
        # 4. EXTRAER DATOS ANTES DE ELIMINAR (FIX DEL ERROR)
        ids_a_eliminar = [reg.id for reg in registros_a_eliminar]
        user_id_final = user_id_objetivo or registros_a_eliminar[0].user_id_FK
        
        # Mostrar información detallada antes de eliminar
        print(f"🗑️ Registros a eliminar:")
        for reg in registros_a_eliminar[:5]:  # Mostrar solo los primeros 5
            print(f"   ID: {reg.id}, user_id_FK: {reg.user_id_FK}, municipio: {reg.municipio}")
        
        if len(registros_a_eliminar) > 5:
            print(f"   ... y {len(registros_a_eliminar) - 5} registros más")
        
        # 5. Eliminar registros usando los IDs extraídos
        registros_eliminados = (
            db.query(AnalisisQuimicosValidados)
            .filter(AnalisisQuimicosValidados.id.in_(ids_a_eliminar))
            .delete(synchronize_session=False)
        )
        
        # 6. Confirmar transacción
        db.commit()
        
        print(f"✅ ELIMINACIÓN COMPLETADA")
        print(f"   - Archivo: {nombre_archivo}")
        print(f"   - Registros eliminados: {registros_eliminados}")
        print(f"   - Autorizado por: {admin.nombre} {admin.apellido} (ID: {admin_id})")
        
        return {
            "success": True,
            "message": f"Se eliminaron exitosamente {registros_eliminados} registros del archivo '{nombre_archivo}'",
            "usuario": correo_usuario,
            "archivo": nombre_archivo,
            "eliminados": registros_eliminados,
            "autorizado_por": {
                "admin_id": admin_id,
                "admin_nombre": f"{admin.nombre} {admin.apellido}",
                "admin_correo": admin.correo
            },
            "detalles": {
                "ids_eliminados": ids_a_eliminar[:10],  # Solo los primeros 10 IDs
                "user_id_objetivo": user_id_final  # USADO LA VARIABLE EXTRAÍDA ANTES DEL DELETE
            }
        }
        
    except Exception as e:
        print(f"❌ ERROR CRÍTICO: {str(e)}")
        print(f"   Traceback: {traceback.format_exc()}")
        
        try:
            db.rollback()
            print("🔄 Rollback ejecutado")
        except Exception as rollback_error:
            print(f"⚠️ Error en rollback: {rollback_error}")
        
        return {
            "success": False,
            "message": f"Error interno: {str(e)}",
            "usuario": correo_usuario,
            "archivo": nombre_archivo,
            "eliminados": 0,
            "error": str(e)
        }