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