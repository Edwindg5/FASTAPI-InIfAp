# src/AnalisisSuelosPendientes/application/eliminar_pendientes_service.py

from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session
from src.AnalisisSuelosPendientes.infrastructure.analisis_suelos_model import AnalisisSuelosPendientes
from src.Users.infrastructure.users_model import Users

class EliminarPendientesService:
    
    @staticmethod
    def eliminar_pendientes_por_usuario(db: Session, correo_usuario: str) -> Dict[str, Any]:
        """
        Elimina TODOS los análisis de suelos pendientes de un usuario específico usando su correo.
        
        Args:
            db: Sesión de base de datos
            correo_usuario: Correo del usuario cuyos pendientes se eliminarán
            
        Returns:
            Dict con información del resultado de la operación
        """
        try:
            print(f"Iniciando eliminación de pendientes para usuario: {correo_usuario}")
            
            # 1. Verificar que el usuario exista
            usuario = db.query(Users).filter(Users.correo == correo_usuario).first()
            if not usuario:
                raise ValueError(f"No se encontró un usuario con el correo: {correo_usuario}")
            
            print(f"Usuario encontrado: {usuario.nombre} {usuario.apellido} (ID: {usuario.ID_user})")
            
            # 2. Contar análisis pendientes antes de eliminar
            total_pendientes_antes = db.query(AnalisisSuelosPendientes).filter(
                AnalisisSuelosPendientes.user_id_FK == usuario.ID_user,
                AnalisisSuelosPendientes.estatus == 'pendiente'
            ).count()
            
            if total_pendientes_antes == 0:
                return {
                    "message": f"El usuario {correo_usuario} no tiene análisis pendientes para eliminar",
                    "correo_usuario": correo_usuario,
                    "user_id": usuario.ID_user,
                    "registros_eliminados": 0,
                    "total_antes": 0,
                    "fecha_eliminacion": datetime.now()
                }
            
            print(f"Se encontraron {total_pendientes_antes} análisis pendientes para eliminar")
            
            # 3. Obtener todos los registros pendientes para eliminar
            registros_pendientes = db.query(AnalisisSuelosPendientes).filter(
                AnalisisSuelosPendientes.user_id_FK == usuario.ID_user,
                AnalisisSuelosPendientes.estatus == 'pendiente'
            ).all()
            
            # 4. Eliminar todos los registros pendientes
            registros_eliminados = 0
            for registro in registros_pendientes:
                db.delete(registro)
                registros_eliminados += 1
            
            # 5. Commit de los cambios
            db.commit()
            
            print(f"Eliminación completada exitosamente:")
            print(f"  Usuario: {correo_usuario}")
            print(f"  Registros eliminados: {registros_eliminados}")
            print(f"  Fecha: {datetime.now()}")
            
            return {
                "message": f"Se eliminaron exitosamente {registros_eliminados} análisis pendientes del usuario {correo_usuario}",
                "correo_usuario": correo_usuario,
                "user_id": usuario.ID_user,
                "registros_eliminados": registros_eliminados,
                "total_antes": total_pendientes_antes,
                "fecha_eliminacion": datetime.now()
            }
            
        except ValueError as ve:
            db.rollback()
            raise ve
        except Exception as e:
            db.rollback()
            error_msg = f"Error eliminando pendientes para {correo_usuario}: {str(e)}"
            print(f"Error: {error_msg}")
            raise Exception(error_msg)