# src/AnalisisSuelosPendientes/application/usuarios_validados_service.py

from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from src.AnalisisSuelosPendientes.infrastructure.analisis_suelos_model import AnalisisSuelosPendientes
from src.Users.infrastructure.users_model import Users

class UsuariosValidadosService:
    
    @staticmethod
    def get_usuarios_con_validados(db: Session) -> Dict[str, Any]:
        """
        Obtiene todos los usuarios que tienen análisis de suelos validados con estadísticas completas
        """
        try:
            print("Obteniendo usuarios con análisis validados...")
            
            # Query para obtener usuarios con análisis validados
            usuarios_query = (
                db.query(
                    Users.ID_user.label('user_id'),
                    Users.nombre.label('nombre_usuario'),
                    Users.apellido.label('apellido_usuario'),
                    Users.correo.label('correo_usuario'),
                    func.count(AnalisisSuelosPendientes.id).label('total_validados'),
                    func.max(AnalisisSuelosPendientes.fecha_creacion).label('ultimo_analisis_fecha')
                )
                .join(AnalisisSuelosPendientes, Users.ID_user == AnalisisSuelosPendientes.user_id_FK)
                .filter(AnalisisSuelosPendientes.estatus == 'validado')
                .group_by(
                    Users.ID_user, 
                    Users.nombre, 
                    Users.apellido, 
                    Users.correo
                )
                .order_by(func.count(AnalisisSuelosPendientes.id).desc())
            ).all()
            
            usuarios_con_validados = []
            total_usuarios = len(usuarios_query)
            
            print(f"Se encontraron {total_usuarios} usuarios con análisis validados")
            
            # Para cada usuario, obtener los municipios involucrados
            for usuario in usuarios_query:
                # Obtener municipios únicos para este usuario en registros validados
                municipios_query = (
                    db.query(distinct(AnalisisSuelosPendientes.municipio_cuadernillo))
                    .filter(
                        AnalisisSuelosPendientes.user_id_FK == usuario.user_id,
                        AnalisisSuelosPendientes.estatus == 'validado',
                        AnalisisSuelosPendientes.municipio_cuadernillo.isnot(None),
                        AnalisisSuelosPendientes.municipio_cuadernillo != ''
                    )
                ).all()
                
                municipios_involucrados = [
                    mun[0] for mun in municipios_query 
                    if mun[0] and str(mun[0]).strip() not in ['', 'nan', 'None', 'REGISTRO_TEMPORAL_COMENTARIO']
                ]
                
                usuario_data = {
                    'user_id': usuario.user_id,
                    'nombre_usuario': usuario.nombre_usuario,
                    'apellido_usuario': usuario.apellido_usuario,
                    'correo_usuario': usuario.correo_usuario,
                    'total_validados': usuario.total_validados,
                    'ultimo_analisis_fecha': usuario.ultimo_analisis_fecha,
                    'municipios_involucrados': municipios_involucrados
                }
                
                usuarios_con_validados.append(usuario_data)
                
                print(f"Usuario {usuario.correo_usuario}: {usuario.total_validados} validados en {len(municipios_involucrados)} municipios")
            
            return {
                'total_usuarios_con_validados': total_usuarios,
                'usuarios': usuarios_con_validados
            }
            
        except Exception as e:
            error_msg = f"Error obteniendo usuarios con validados: {str(e)}"
            print(f"Error: {error_msg}")
            raise Exception(error_msg)
    
    @staticmethod
    def get_analisis_validados_por_correo(db: Session, correo_usuario: str) -> Dict[str, Any]:
        """
        Obtiene todos los análisis validados de un usuario específico usando su correo
        """
        try:
            print(f"Obteniendo análisis validados para usuario: {correo_usuario}")
            
            # 1. Verificar que el usuario exista
            usuario = db.query(Users).filter(Users.correo == correo_usuario).first()
            if not usuario:
                raise ValueError(f"No se encontró un usuario con el correo: {correo_usuario}")
            
            # 2. Obtener todos los análisis validados del usuario
            analisis_validados = (
                db.query(AnalisisSuelosPendientes)
                .filter(
                    AnalisisSuelosPendientes.user_id_FK == usuario.ID_user,
                    AnalisisSuelosPendientes.estatus == 'validado'
                )
                .order_by(AnalisisSuelosPendientes.fecha_creacion.desc())
            ).all()
            
            total_validados = len(analisis_validados)
            
            if total_validados == 0:
                return {
                    'usuario_info': {
                        'user_id': usuario.ID_user,
                        'nombre_completo': f"{usuario.nombre or ''} {usuario.apellido or ''}".strip(),
                        'correo': usuario.correo
                    },
                    'total_validados': 0,
                    'analisis_validados': [],
                    'municipios_involucrados': [],
                    'ultimo_analisis_fecha': None,
                    'message': f"El usuario {correo_usuario} no tiene análisis validados"
                }
            
            # 3. Obtener municipios únicos
            municipios_unicos = set()
            for analisis in analisis_validados:
                if analisis.municipio_cuadernillo and str(analisis.municipio_cuadernillo).strip() not in ['', 'nan', 'None']:
                    municipios_unicos.add(analisis.municipio_cuadernillo)
            
            # 4. Preparar datos de respuesta con información completa
            analisis_data = []
            for analisis in analisis_validados:
                analisis_info = {
                    'id': analisis.id,
                    'numero': analisis.numero,
                    'fecha_creacion': analisis.fecha_creacion,
                    'municipio_cuadernillo': analisis.municipio_cuadernillo,
                    'localidad_cuadernillo': analisis.localidad_cuadernillo,
                    'clave_estatal': analisis.clave_estatal,
                    'clave_municipio': analisis.clave_municipio,
                    'cultivo_establecer': analisis.cultivo_establecer,
                    'nombre_tecnico': analisis.nombre_tecnico,
                    'nombre_productor': analisis.nombre_productor,
                    'fecha_muestreo': analisis.fecha_muestreo,
                    'estatus': analisis.estatus,
                    'nombre_revisor': analisis.nombre_revisor
                }
                analisis_data.append(analisis_info)
            
            print(f"Usuario {correo_usuario}: {total_validados} análisis validados encontrados")
            
            return {
                'usuario_info': {
                    'user_id': usuario.ID_user,
                    'nombre_completo': f"{usuario.nombre or ''} {usuario.apellido or ''}".strip(),
                    'correo': usuario.correo
                },
                'total_validados': total_validados,
                'analisis_validados': analisis_data,
                'municipios_involucrados': list(municipios_unicos),
                'ultimo_analisis_fecha': analisis_validados[0].fecha_creacion if analisis_validados else None,
                'message': f"Se encontraron {total_validados} análisis validados para {correo_usuario}"
            }
            
        except ValueError as ve:
            raise ve
        except Exception as e:
            error_msg = f"Error obteniendo análisis validados para {correo_usuario}: {str(e)}"
            print(f"Error: {error_msg}")
            raise Exception(error_msg)
    
    @staticmethod
    def get_estadisticas_validados(db: Session) -> Dict[str, Any]:
        """
        Obtiene estadísticas generales de análisis validados en el sistema
        """
        try:
            # Total de análisis validados
            total_validados = db.query(AnalisisSuelosPendientes).filter(
                AnalisisSuelosPendientes.estatus == 'validado'
            ).count()
            
            # Total de usuarios con validados
            total_usuarios_validados = db.query(
                func.count(distinct(AnalisisSuelosPendientes.user_id_FK))
            ).filter(
                AnalisisSuelosPendientes.estatus == 'validado'
            ).scalar()
            
            # Municipios más frecuentes en validados
            municipios_frecuentes = (
                db.query(
                    AnalisisSuelosPendientes.municipio_cuadernillo,
                    func.count(AnalisisSuelosPendientes.id).label('total')
                )
                .filter(
                    AnalisisSuelosPendientes.estatus == 'validado',
                    AnalisisSuelosPendientes.municipio_cuadernillo.isnot(None),
                    AnalisisSuelosPendientes.municipio_cuadernillo != ''
                )
                .group_by(AnalisisSuelosPendientes.municipio_cuadernillo)
                .order_by(func.count(AnalisisSuelosPendientes.id).desc())
                .limit(10)
            ).all()
            
            # Usuarios con más validados
            usuarios_top = (
                db.query(
                    Users.correo,
                    func.count(AnalisisSuelosPendientes.id).label('total_validados')
                )
                .join(AnalisisSuelosPendientes, Users.ID_user == AnalisisSuelosPendientes.user_id_FK)
                .filter(AnalisisSuelosPendientes.estatus == 'validado')
                .group_by(Users.ID_user, Users.correo)
                .order_by(func.count(AnalisisSuelosPendientes.id).desc())
                .limit(10)
            ).all()
            
            return {
                'total_analisis_validados': total_validados,
                'total_usuarios_con_validados': total_usuarios_validados,
                'municipios_mas_frecuentes': [
                    {'municipio': mun[0], 'total': mun[1]} 
                    for mun in municipios_frecuentes if mun[0]
                ],
                'usuarios_con_mas_validados': [
                    {'correo': user[0], 'total_validados': user[1]} 
                    for user in usuarios_top
                ],
                'fecha_consulta': datetime.now()
            }
            
        except Exception as e:
            error_msg = f"Error obteniendo estadísticas de validados: {str(e)}"
            print(f"Error: {error_msg}")
            raise Exception(error_msg)