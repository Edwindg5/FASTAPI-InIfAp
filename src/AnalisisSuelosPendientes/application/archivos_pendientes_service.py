from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from src.AnalisisSuelosPendientes.infrastructure.analisis_suelos_model import AnalisisSuelosPendientes
from src.Users.infrastructure.users_model import Users

class ArchivosPendientesService:
    
    @staticmethod
    def get_archivos_con_pendientes(db: Session) -> Dict[str, Any]:
        """
        Obtiene todos los archivos únicos que tienen análisis pendientes
        """
        try:
            print("Obteniendo archivos únicos con análisis pendientes...")
            
            archivos_query = (
                db.query(
                    Users.ID_user.label('user_id'),  # AGREGADO: ID del usuario
                    Users.nombre.label('nombre_usuario'),
                    Users.apellido.label('apellido_usuario'),
                    func.max(AnalisisSuelosPendientes.fecha_creacion).label('fecha'),
                    AnalisisSuelosPendientes.nombre_archivo
                )
                .join(AnalisisSuelosPendientes, Users.ID_user == AnalisisSuelosPendientes.user_id_FK)
                .filter(
                    AnalisisSuelosPendientes.estatus == 'pendiente',
                    AnalisisSuelosPendientes.nombre_archivo.isnot(None)
                )
                .group_by(
                    Users.ID_user,  # AGREGADO: Incluir en GROUP BY
                    Users.nombre, 
                    Users.apellido,
                    AnalisisSuelosPendientes.nombre_archivo
                )
                .order_by(Users.nombre, AnalisisSuelosPendientes.nombre_archivo)
            ).all()
            
            archivos_con_pendientes = []
            
            for archivo in archivos_query:
                nombre_completo = f"{archivo.nombre_usuario or ''} {archivo.apellido_usuario or ''}".strip()
                
                archivo_data = {
                    'user_id': archivo.user_id,  # AGREGADO: ID del usuario
                    'nombre_usuario': nombre_completo,
                    'estatus': 'pendiente',
                    'fecha': archivo.fecha,
                    'nombre_archivo': archivo.nombre_archivo
                }
                
                archivos_con_pendientes.append(archivo_data)
            
            print(f"Se encontraron {len(archivos_con_pendientes)} archivos únicos con pendientes")
            
            return {
                'total_archivos_con_pendientes': len(archivos_con_pendientes),
                'archivos': archivos_con_pendientes
            }
            
        except Exception as e:
            error_msg = f"Error obteniendo archivos con pendientes: {str(e)}"
            print(f"Error: {error_msg}")
            raise Exception(error_msg)
    
    @staticmethod
    def get_pendientes_por_usuario_archivo(db: Session, correo_usuario: str, nombre_archivo: str) -> Dict[str, Any]:
        """
        Obtiene los pendientes específicos por correo de usuario y nombre de archivo
        """
        try:
            print(f"Obteniendo pendientes para {correo_usuario} - archivo: {nombre_archivo}")
            
            # Verificar que el usuario existe
            usuario = db.query(Users).filter(Users.correo == correo_usuario).first()
            if not usuario:
                raise ValueError(f"Usuario con correo {correo_usuario} no encontrado")
            
            # Obtener cantidad de registros pendientes para este usuario y archivo
            cantidad_datos = (
                db.query(AnalisisSuelosPendientes)
                .filter(
                    AnalisisSuelosPendientes.user_id_FK == usuario.ID_user,
                    AnalisisSuelosPendientes.estatus == 'pendiente',
                    AnalisisSuelosPendientes.nombre_archivo == nombre_archivo
                )
            ).count()
            
            if cantidad_datos == 0:
                raise ValueError(f"No se encontraron registros pendientes para {correo_usuario} con el archivo {nombre_archivo}")
            
            # Obtener fecha más reciente de este archivo
            fecha_reciente = (
                db.query(func.max(AnalisisSuelosPendientes.fecha_creacion))
                .filter(
                    AnalisisSuelosPendientes.user_id_FK == usuario.ID_user,
                    AnalisisSuelosPendientes.estatus == 'pendiente',
                    AnalisisSuelosPendientes.nombre_archivo == nombre_archivo
                )
            ).scalar()
            
            # Construir nombre completo
            nombre_completo = f"{usuario.nombre or ''} {usuario.apellido or ''}".strip()
            if not nombre_completo:
                nombre_completo = usuario.correo.split('@')[0]
            
            resultado = {
                'nombre_usuario': nombre_completo,
                'fecha': fecha_reciente,
                'estatus': 'pendiente',
                'cantidad_datos': cantidad_datos,
                'nombre_archivo': nombre_archivo
            }
            
            print(f"Resultado: {cantidad_datos} registros pendientes encontrados")
            
            return resultado
            
        except ValueError as ve:
            raise ve
        except Exception as e:
            error_msg = f"Error obteniendo pendientes por usuario y archivo: {str(e)}"
            print(f"Error: {error_msg}")
            raise Exception(error_msg)