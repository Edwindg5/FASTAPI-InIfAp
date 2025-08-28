# src/AnalisisSuelosPendientes/application/archivos_usuario_service.py
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from src.AnalisisSuelosPendientes.infrastructure.analisis_suelos_model import AnalisisSuelosPendientes
from src.Users.infrastructure.users_model import Users

class ArchivosUsuarioService:
    
    @staticmethod
    def get_archivos_pendientes_por_correo(db: Session, correo_usuario: str) -> Dict[str, Any]:
        """
        Obtiene todos los archivos únicos con estatus pendiente de un usuario específico por correo.
        
        Args:
            db: Sesión de base de datos
            correo_usuario: Correo electrónico del usuario
            
        Returns:
            Dict con información de archivos únicos del usuario
            
        Raises:
            ValueError: Si el usuario no existe
            Exception: Errores de base de datos
        """
        try:
            print(f"Buscando archivos pendientes para usuario: {correo_usuario}")
            
            # 1. Verificar que el usuario existe
            usuario = db.query(Users).filter(Users.correo == correo_usuario).first()
            if not usuario:
                raise ValueError(f"Usuario con correo '{correo_usuario}' no encontrado")
            
            # 2. Obtener archivos únicos con sus estadísticas
            archivos_query = (
                db.query(
                    AnalisisSuelosPendientes.nombre_archivo,
                    func.count(AnalisisSuelosPendientes.id).label('total_registros'),
                    func.min(AnalisisSuelosPendientes.fecha_creacion).label('fecha_subida'),
                    func.max(AnalisisSuelosPendientes.fecha_creacion).label('ultima_modificacion')
                )
                .filter(
                    AnalisisSuelosPendientes.user_id_FK == usuario.ID_user,
                    AnalisisSuelosPendientes.estatus == 'pendiente',
                    AnalisisSuelosPendientes.nombre_archivo.isnot(None)
                )
                .group_by(AnalisisSuelosPendientes.nombre_archivo)
                .order_by(func.max(AnalisisSuelosPendientes.fecha_creacion).desc())
            ).all()
            
            # 3. Construir nombre completo del usuario
            nombre_completo = f"{usuario.nombre or ''} {usuario.apellido or ''}".strip()
            if not nombre_completo:
                nombre_completo = usuario.correo.split('@')[0]
            
            # 4. Procesar resultados
            archivos_pendientes = []
            total_archivos_unicos = len(archivos_query)
            total_registros_pendientes = 0
            
            for archivo in archivos_query:
                archivo_data = {
                    'nombre_archivo': archivo.nombre_archivo,
                    'total_registros': archivo.total_registros,
                    'fecha_subida': archivo.fecha_subida,
                    'ultima_modificacion': archivo.ultima_modificacion,
                    'estatus': 'pendiente'
                }
                
                archivos_pendientes.append(archivo_data)
                total_registros_pendientes += archivo.total_registros
                
                print(f"  Archivo: {archivo.nombre_archivo} - {archivo.total_registros} registros")
            
            # 5. Resultado final
            resultado = {
                'correo_usuario': correo_usuario,
                'nombre_usuario': nombre_completo,
                'user_id': usuario.ID_user,
                'total_archivos_unicos': total_archivos_unicos,
                'total_registros_pendientes': total_registros_pendientes,
                'fecha_consulta': datetime.now(),
                'archivos': archivos_pendientes
            }
            
            print(f"Usuario {correo_usuario}: {total_archivos_unicos} archivos únicos, {total_registros_pendientes} registros totales")
            
            return resultado
            
        except ValueError as ve:
            raise ve
        except Exception as e:
            error_msg = f"Error obteniendo archivos pendientes para {correo_usuario}: {str(e)}"
            print(f"Error: {error_msg}")
            raise Exception(error_msg)