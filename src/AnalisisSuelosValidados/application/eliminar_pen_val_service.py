# src/AnalisisSuelosValidados/application/eliminar_pen_val_service.py

from sqlalchemy.orm import Session
from src.Users.infrastructure.users_model import Users
from src.AnalisisSuelosPendientes.infrastructure.analisis_suelos_model import AnalisisSuelosPendientes
from src.AnalisisSuelosValidados.infrastructure.analisis_suelos_validados_model import AnalisisSuelosValidados
import traceback


class EliminarPenValService:
    """
    Servicio para eliminar análisis de suelos pendientes y validados
    """
    
    def __init__(self, db: Session):
        self.db = db

    def eliminar_analisis_pendientes_por_user_id_y_archivo(self, user_id: int, nombre_archivo: str) -> dict:
        """
        Elimina TODOS los análisis de suelos pendientes asociados a un usuario por su ID
        y filtrados por nombre de archivo.

        Args:
            user_id (int): ID del usuario
            nombre_archivo (str): Nombre del archivo para filtrar

        Returns:
            dict: Resultado de la operación de eliminación
        """
        try:
            print(f"=== ELIMINANDO ANÁLISIS DE SUELOS PENDIENTES PARA USER_ID: {user_id}, ARCHIVO: {nombre_archivo} ===")
            
            # Buscar usuario por ID
            usuario = self.db.query(Users).filter(Users.ID_user == user_id).first()
            if not usuario:
                print(f"Usuario no encontrado: ID {user_id}")
                return {
                    "success": False,
                    "message": f"Usuario con ID '{user_id}' no encontrado",
                    "eliminados": 0
                }

            print(f"Usuario encontrado: ID={usuario.ID_user}, correo={usuario.correo}")

            # Contar cuántos análisis pendientes tiene el usuario con ese archivo
            total_pendientes = (
                self.db.query(AnalisisSuelosPendientes)
                .filter(
                    AnalisisSuelosPendientes.user_id_FK == user_id,
                    AnalisisSuelosPendientes.nombre_archivo == nombre_archivo
                )
                .count()
            )

            print(f"Análisis de suelos pendientes encontrados para eliminar: {total_pendientes}")

            if total_pendientes == 0:
                return {
                    "success": True,
                    "message": f"El usuario no tiene análisis de suelos pendientes con el archivo '{nombre_archivo}' para eliminar",
                    "usuario_correo": usuario.correo,
                    "usuario_id": usuario.ID_user,
                    "eliminados": 0
                }

            # ELIMINAR todos los análisis pendientes del usuario con ese archivo
            registros_eliminados = (
                self.db.query(AnalisisSuelosPendientes)
                .filter(
                    AnalisisSuelosPendientes.user_id_FK == user_id,
                    AnalisisSuelosPendientes.nombre_archivo == nombre_archivo
                )
                .delete(synchronize_session=False)
            )

            # Hacer commit de la eliminación
            self.db.commit()

            print(f"✅ ELIMINACIÓN DE SUELOS PENDIENTES COMPLETADA:")
            print(f"   - Usuario: {usuario.correo} (ID: {usuario.ID_user})")
            print(f"   - Archivo: {nombre_archivo}")
            print(f"   - Registros eliminados: {registros_eliminados}")

            return {
                "success": True,
                "message": f"Se eliminaron {registros_eliminados} análisis de suelos pendientes del archivo '{nombre_archivo}' exitosamente",
                "usuario_correo": usuario.correo,
                "usuario_id": usuario.ID_user,
                "nombre_archivo": nombre_archivo,
                "eliminados": registros_eliminados
            }

        except Exception as e:
            print(f"❌ Error en eliminación de suelos pendientes: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            
            # Rollback en caso de error
            self.db.rollback()
            
            return {
                "success": False,
                "message": f"Error al eliminar análisis de suelos pendientes: {str(e)}",
                "usuario_id": user_id,
                "nombre_archivo": nombre_archivo,
                "eliminados": 0,
                "error": str(e)
            }

    def eliminar_analisis_validados_por_user_id_y_archivo(self, user_id: int, nombre_archivo: str) -> dict:
        """
        Elimina TODOS los análisis de suelos validados asociados a un usuario por su ID
        y filtrados por nombre de archivo.

        Args:
            user_id (int): ID del usuario
            nombre_archivo (str): Nombre del archivo para filtrar

        Returns:
            dict: Resultado de la operación de eliminación
        """
        try:
            print(f"=== ELIMINANDO ANÁLISIS DE SUELOS VALIDADOS PARA USER_ID: {user_id}, ARCHIVO: {nombre_archivo} ===")
            
            # Buscar usuario por ID
            usuario = self.db.query(Users).filter(Users.ID_user == user_id).first()
            if not usuario:
                print(f"Usuario no encontrado: ID {user_id}")
                return {
                    "success": False,
                    "message": f"Usuario con ID '{user_id}' no encontrado",
                    "eliminados": 0
                }

            print(f"Usuario encontrado: ID={usuario.ID_user}, correo={usuario.correo}")

            # Contar cuántos análisis validados tiene el usuario con ese archivo
            total_validados = (
                self.db.query(AnalisisSuelosValidados)
                .filter(
                    AnalisisSuelosValidados.user_id_FK == user_id,
                    AnalisisSuelosValidados.nombre_archivo == nombre_archivo
                )
                .count()
            )

            print(f"Análisis de suelos validados encontrados para eliminar: {total_validados}")

            if total_validados == 0:
                return {
                    "success": True,
                    "message": f"El usuario no tiene análisis de suelos validados con el archivo '{nombre_archivo}' para eliminar",
                    "usuario_correo": usuario.correo,
                    "usuario_id": usuario.ID_user,
                    "eliminados": 0
                }

            # ELIMINAR todos los análisis validados del usuario con ese archivo
            registros_eliminados = (
                self.db.query(AnalisisSuelosValidados)
                .filter(
                    AnalisisSuelosValidados.user_id_FK == user_id,
                    AnalisisSuelosValidados.nombre_archivo == nombre_archivo
                )
                .delete(synchronize_session=False)
            )

            # Hacer commit de la eliminación
            self.db.commit()

            print(f"✅ ELIMINACIÓN DE SUELOS VALIDADOS COMPLETADA:")
            print(f"   - Usuario: {usuario.correo} (ID: {usuario.ID_user})")
            print(f"   - Archivo: {nombre_archivo}")
            print(f"   - Registros eliminados: {registros_eliminados}")

            return {
                "success": True,
                "message": f"Se eliminaron {registros_eliminados} análisis de suelos validados del archivo '{nombre_archivo}' exitosamente",
                "usuario_correo": usuario.correo,
                "usuario_id": usuario.ID_user,
                "nombre_archivo": nombre_archivo,
                "eliminados": registros_eliminados
            }

        except Exception as e:
            print(f"❌ Error en eliminación de suelos validados: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            
            # Rollback en caso de error
            self.db.rollback()
            
            return {
                "success": False,
                "message": f"Error al eliminar análisis de suelos validados: {str(e)}",
                "usuario_id": user_id,
                "nombre_archivo": nombre_archivo,
                "eliminados": 0,
                "error": str(e)
            }