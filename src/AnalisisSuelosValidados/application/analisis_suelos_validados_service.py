# src/AnalisisSuelosValidados/application/analisis_suelos_validados_service.py
from typing import List, Optional, Generator, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from src.AnalisisSuelosValidados.infrastructure.analisis_suelos_validados_model import AnalisisSuelosValidados
from src.AnalisisSuelosPendientes.infrastructure.analisis_suelos_model import AnalisisSuelosPendientes
from src.Users.infrastructure.users_model import Users

class AnalisisSuelosValidadosService:
    def __init__(self, db: Session):
        self.db = db

    def validar_analisis_por_correo(self, correo_usuario: str) -> dict:
        """Valida análisis de un usuario específico por su correo"""
        try:
            # Buscar al usuario por correo
            usuario = self.db.query(Users).filter(Users.correo == correo_usuario).first()
            if not usuario:
                return {"success": False, "message": "Usuario no encontrado"}
            
            # Buscar análisis pendientes del usuario
            analisis_pendientes = (
                self.db.query(AnalisisSuelosPendientes)
                .filter(AnalisisSuelosPendientes.user_id_FK == usuario.ID_user)
                .all()
            )
            
            if not analisis_pendientes:
                return {"success": False, "message": "No hay análisis pendientes para este usuario"}
            
            # Buscar al administrador (rol_id_FK = 1)
            admin = self.db.query(Users).filter(Users.rol_id_FK == 1).first()
            if not admin:
                return {"success": False, "message": "No se encontró un administrador en el sistema"}
            
            validados_count = 0
            
            for analisis in analisis_pendientes:
                # Crear nuevo registro en analisis_suelos_validados
                analisis_validado = AnalisisSuelosValidados(
                    municipio_id_FK=analisis.municipio_id_FK,
                    numero=analisis.numero,
                    clave_estatal=analisis.clave_estatal,
                    estado_cuadernillo=analisis.estado_cuadernillo,
                    clave_municipio=analisis.clave_municipio,
                    clave_munip=analisis.clave_munip,
                    municipio_cuadernillo=analisis.municipio_cuadernillo,
                    clave_localidad=analisis.clave_localidad,
                    localidad_cuadernillo=analisis.localidad_cuadernillo,
                    recuento_curp_renapo=analisis.recuento_curp_renapo,
                    extraccion_edo=analisis.extraccion_edo,
                    clave=analisis.clave,
                    ddr=analisis.ddr,
                    cader=analisis.cader,
                    coordenada_x=analisis.coordenada_x,
                    coordenada_y=analisis.coordenada_y,
                    elevacion_msnm=analisis.elevacion_msnm,
                    profundidad_muestreo=analisis.profundidad_muestreo,
                    fecha_muestreo=analisis.fecha_muestreo,
                    parcela=analisis.parcela,
                    cultivo_anterior=analisis.cultivo_anterior,
                    cultivo_establecer=analisis.cultivo_establecer,
                    manejo=analisis.manejo,
                    tipo_vegetacion=analisis.tipo_vegetacion,
                    nombre_tecnico=analisis.nombre_tecnico,
                    tel_tecnico=analisis.tel_tecnico,
                    correo_tecnico=analisis.correo_tecnico,
                    nombre_productor=analisis.nombre_productor,
                    tel_productor=analisis.tel_productor,
                    correo_productor=analisis.correo_productor,
                    muestra=analisis.muestra,
                    reemplazo=analisis.reemplazo,
                    nombre_revisor=analisis.nombre_revisor,
                    user_id_FK=admin.ID_user,  # Cambiar al ID del administrador
                    fecha_validacion=func.now(),
                    fecha_creacion=analisis.fecha_creacion
                )
                
                self.db.add(analisis_validado)
                validados_count += 1
            
            # Eliminar todos los análisis pendientes del usuario
            self.db.query(AnalisisSuelosPendientes).filter(
                AnalisisSuelosPendientes.user_id_FK == usuario.ID_user
            ).delete()
            
            self.db.commit()
            
            return {
                "success": True,
                "message": f"Se validaron {validados_count} análisis correctamente",
                "validados": validados_count,
                "usuario": {
                    "correo": correo_usuario,
                    "nombre": usuario.nombre,
                    "apellido": usuario.apellido
                }
            }
            
        except Exception as e:
            self.db.rollback()
            return {"success": False, "message": f"Error al validar análisis: {str(e)}"}

    def obtener_pendientes_detallados_por_correo(self, correo_usuario: str) -> dict:
        """
        Obtiene todos los análisis pendientes de un usuario específico con información detallada.
        Optimizado para exportación y visualización completa.
        """
        try:
            # Buscar usuario por correo
            usuario = self.db.query(Users).filter(Users.correo == correo_usuario).first()
            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado",
                    "total_registros": 0,
                    "datos": []
                }
            
            # Obtener TODOS los análisis pendientes del usuario
            analisis_pendientes = (
                self.db.query(AnalisisSuelosPendientes)
                .filter(AnalisisSuelosPendientes.user_id_FK == usuario.ID_user)
                .order_by(AnalisisSuelosPendientes.fecha_creacion.desc())
                .all()
            )
            
            if not analisis_pendientes:
                return {
                    "success": False,
                    "message": "No hay análisis pendientes para este usuario",
                    "total_registros": 0,
                    "usuario_info": {
                        "id": usuario.ID_user,
                        "correo": usuario.correo,
                        "nombre": usuario.nombre,
                        "apellido": usuario.apellido
                    },
                    "datos": []
                }
            
            # Procesar todos los datos con manejo seguro de valores None
            datos_procesados = []
            for i, analisis in enumerate(analisis_pendientes, 1):
                dato = {
                    # Información básica
                    "numero_registro": i,
                    "id": getattr(analisis, 'id', None),
                    "user_id": usuario.ID_user,
                    
                    # Información geográfica
                    "municipio_id_FK": getattr(analisis, 'municipio_id_FK', None),
                    "municipio_cuadernillo": getattr(analisis, 'municipio_cuadernillo', ''),
                    "localidad_cuadernillo": getattr(analisis, 'localidad_cuadernillo', ''),
                    "clave_municipio": getattr(analisis, 'clave_municipio', None),
                    "clave_munip": getattr(analisis, 'clave_munip', ''),
                    "clave_localidad": getattr(analisis, 'clave_localidad', ''),
                    "estado_cuadernillo": getattr(analisis, 'estado_cuadernillo', ''),
                    
                    # Coordenadas y ubicación
                    "coordenada_x": getattr(analisis, 'coordenada_x', ''),
                    "coordenada_y": getattr(analisis, 'coordenada_y', ''),
                    "elevacion_msnm": getattr(analisis, 'elevacion_msnm', None),
                    
                    # Información del productor
                    "nombre_productor": getattr(analisis, 'nombre_productor', ''),
                    "tel_productor": getattr(analisis, 'tel_productor', ''),
                    "correo_productor": getattr(analisis, 'correo_productor', ''),
                    
                    # Información del técnico
                    "nombre_tecnico": getattr(analisis, 'nombre_tecnico', ''),
                    "tel_tecnico": getattr(analisis, 'tel_tecnico', ''),
                    "correo_tecnico": getattr(analisis, 'correo_tecnico', ''),
                    
                    # Información agrícola
                    "cultivo_anterior": getattr(analisis, 'cultivo_anterior', ''),
                    "cultivo_establecer": getattr(analisis, 'cultivo_establecer', ''),
                    "manejo": getattr(analisis, 'manejo', ''),
                    "tipo_vegetacion": getattr(analisis, 'tipo_vegetacion', ''),
                    "parcela": getattr(analisis, 'parcela', ''),
                    
                    # Información de muestreo
                    "profundidad_muestreo": getattr(analisis, 'profundidad_muestreo', ''),
                    "fecha_muestreo": str(analisis.fecha_muestreo) if getattr(analisis, 'fecha_muestreo', None) else '',
                    "muestra": getattr(analisis, 'muestra', ''),
                    "reemplazo": getattr(analisis, 'reemplazo', ''),
                    
                    # Información administrativa
                    "numero": getattr(analisis, 'numero', None),
                    "clave_estatal": getattr(analisis, 'clave_estatal', None),
                    "recuento_curp_renapo": getattr(analisis, 'recuento_curp_renapo', None),
                    "extraccion_edo": getattr(analisis, 'extraccion_edo', ''),
                    "clave": getattr(analisis, 'clave', ''),
                    "ddr": getattr(analisis, 'ddr', ''),
                    "cader": getattr(analisis, 'cader', ''),
                    "nombre_revisor": getattr(analisis, 'nombre_revisor', ''),
                    
                    # Fechas
                    "fecha_creacion": str(analisis.fecha_creacion) if getattr(analisis, 'fecha_creacion', None) else '',
                }
                
                datos_procesados.append(dato)
            
            return {
                "success": True,
                "message": f"Se encontraron {len(analisis_pendientes)} análisis pendientes",
                "total_registros": len(analisis_pendientes),
                "usuario_info": {
                    "id": usuario.ID_user,
                    "correo": usuario.correo,
                    "nombre": usuario.nombre or '',
                    "apellido": usuario.apellido or ''
                },
                "datos": datos_procesados
            }
            
        except Exception as e:
            print(f"Error al obtener análisis pendientes detallados: {str(e)}")
            return {
                "success": False,
                "message": f"Error al obtener datos: {str(e)}",
                "total_registros": 0,
                "datos": []
            }

    def obtener_todos_los_pendientes_detallados(self) -> dict:
        """
        Obtiene TODOS los análisis pendientes de TODOS los usuarios con información detallada.
        Incluye información del usuario propietario de cada registro.
        Optimizado para exportación y visualización completa.
        """
        try:
            # Obtener TODOS los análisis pendientes con información del usuario
            analisis_pendientes = (
                self.db.query(AnalisisSuelosPendientes, Users)
                .join(Users, AnalisisSuelosPendientes.user_id_FK == Users.ID_user)
                .order_by(
                    Users.correo.asc(),  # Ordenar por usuario primero
                    AnalisisSuelosPendientes.fecha_creacion.desc()  # Luego por fecha
                )
                .all()
            )
            
            if not analisis_pendientes:
                return {
                    "success": False,
                    "message": "No hay análisis pendientes en el sistema",
                    "total_registros": 0,
                    "total_usuarios": 0,
                    "datos": []
                }
            
            # Procesar todos los datos con manejo seguro de valores None
            datos_procesados = []
            usuarios_unicos = set()
            
            for i, (analisis, usuario) in enumerate(analisis_pendientes, 1):
                usuarios_unicos.add(usuario.correo)
                
                dato = {
                    # Información básica del registro
                    "numero_registro": i,
                    "id": getattr(analisis, 'id', None),
                    
                    # Información del usuario propietario
                    "user_id": usuario.ID_user,
                    "usuario_correo": usuario.correo,
                    "usuario_nombre": getattr(usuario, 'nombre', '') or '',
                    "usuario_apellido": getattr(usuario, 'apellido', '') or '',
                    "usuario_nombre_completo": f"{getattr(usuario, 'nombre', '') or ''} {getattr(usuario, 'apellido', '') or ''}".strip(),
                    "usuario_rol": getattr(usuario, 'rol_id_FK', None),
                    
                    # Información geográfica
                    "municipio_id_FK": getattr(analisis, 'municipio_id_FK', None),
                    "municipio_cuadernillo": getattr(analisis, 'municipio_cuadernillo', ''),
                    "localidad_cuadernillo": getattr(analisis, 'localidad_cuadernillo', ''),
                    "clave_municipio": getattr(analisis, 'clave_municipio', None),
                    "clave_munip": getattr(analisis, 'clave_munip', ''),
                    "clave_localidad": getattr(analisis, 'clave_localidad', ''),
                    "estado_cuadernillo": getattr(analisis, 'estado_cuadernillo', ''),
                    
                    # Coordenadas y ubicación
                    "coordenada_x": getattr(analisis, 'coordenada_x', ''),
                    "coordenada_y": getattr(analisis, 'coordenada_y', ''),
                    "elevacion_msnm": getattr(analisis, 'elevacion_msnm', None),
                    
                    # Información del productor
                    "nombre_productor": getattr(analisis, 'nombre_productor', ''),
                    "tel_productor": getattr(analisis, 'tel_productor', ''),
                    "correo_productor": getattr(analisis, 'correo_productor', ''),
                    
                    # Información del técnico
                    "nombre_tecnico": getattr(analisis, 'nombre_tecnico', ''),
                    "tel_tecnico": getattr(analisis, 'tel_tecnico', ''),
                    "correo_tecnico": getattr(analisis, 'correo_tecnico', ''),
                    
                    # Información agrícola
                    "cultivo_anterior": getattr(analisis, 'cultivo_anterior', ''),
                    "cultivo_establecer": getattr(analisis, 'cultivo_establecer', ''),
                    "manejo": getattr(analisis, 'manejo', ''),
                    "tipo_vegetacion": getattr(analisis, 'tipo_vegetacion', ''),
                    "parcela": getattr(analisis, 'parcela', ''),
                    
                    # Información de muestreo
                    "profundidad_muestreo": getattr(analisis, 'profundidad_muestreo', ''),
                    "fecha_muestreo": str(analisis.fecha_muestreo) if getattr(analisis, 'fecha_muestreo', None) else '',
                    "muestra": getattr(analisis, 'muestra', ''),
                    "reemplazo": getattr(analisis, 'reemplazo', ''),
                    
                    # Información administrativa
                    "numero": getattr(analisis, 'numero', None),
                    "clave_estatal": getattr(analisis, 'clave_estatal', None),
                    "recuento_curp_renapo": getattr(analisis, 'recuento_curp_renapo', None),
                    "extraccion_edo": getattr(analisis, 'extraccion_edo', ''),
                    "clave": getattr(analisis, 'clave', ''),
                    "ddr": getattr(analisis, 'ddr', ''),
                    "cader": getattr(analisis, 'cader', ''),
                    "nombre_revisor": getattr(analisis, 'nombre_revisor', ''),
                    
                    # Fechas
                    "fecha_creacion": str(analisis.fecha_creacion) if getattr(analisis, 'fecha_creacion', None) else '',
                }
                
                datos_procesados.append(dato)
            
            return {
                "success": True,
                "message": f"Se encontraron {len(analisis_pendientes)} análisis pendientes de {len(usuarios_unicos)} usuarios",
                "total_registros": len(analisis_pendientes),
                "total_usuarios": len(usuarios_unicos),
                "usuarios_con_pendientes": list(usuarios_unicos),
                "datos": datos_procesados
            }
            
        except Exception as e:
            print(f"Error al obtener todos los análisis pendientes detallados: {str(e)}")
            return {
                "success": False,
                "message": f"Error al obtener datos: {str(e)}",
                "total_registros": 0,
                "total_usuarios": 0,
                "datos": []
            }
            
            
    def obtener_validados_detallados_por_correo(self, correo_usuario: str) -> dict:
        """
        Obtiene todos los análisis validados de un usuario específico con información detallada.
        Optimizado para exportación y visualización completa.
        """
        try:
            usuario = self.db.query(Users).filter(Users.correo == correo_usuario).first()
            if not usuario:
                return {
                    "success": False,
                    "message": "Usuario no encontrado",
                    "total_registros": 0,
                    "datos": []
                }
            
            # Obtener TODOS los análisis validados del usuario
            analisis_validados = (
                self.db.query(AnalisisSuelosValidados)
                .filter(AnalisisSuelosValidados.user_id_FK == usuario.ID_user)
                .order_by(AnalisisSuelosValidados.fecha_validacion.desc())
                .all()
            )
            
            if not analisis_validados:
                return {
                    "success": False,
                    "message": "No hay análisis validados para este usuario",
                    "total_registros": 0,
                    "usuario_info": {
                        "id": usuario.ID_user,
                        "correo": usuario.correo,
                        "nombre": usuario.nombre,
                        "apellido": usuario.apellido
                    },
                    "datos": []
                }
            
            # Procesar todos los datos con manejo seguro de valores None
            datos_procesados = []
            for i, analisis in enumerate(analisis_validados, 1):
                dato = {
                    # Información básica
                    "numero_registro": i,
                    "id": getattr(analisis, 'id', None),
                    "user_id": usuario.ID_user,
                    
                    # Información geográfica
                    "municipio_id_FK": getattr(analisis, 'municipio_id_FK', None),
                    "municipio_cuadernillo": getattr(analisis, 'municipio_cuadernillo', ''),
                    "localidad_cuadernillo": getattr(analisis, 'localidad_cuadernillo', ''),
                    "clave_municipio": getattr(analisis, 'clave_municipio', None),
                    "clave_munip": getattr(analisis, 'clave_munip', ''),
                    "clave_localidad": getattr(analisis, 'clave_localidad', ''),
                    "estado_cuadernillo": getattr(analisis, 'estado_cuadernillo', ''),
                    
                    # Coordenadas y ubicación
                    "coordenada_x": getattr(analisis, 'coordenada_x', ''),
                    "coordenada_y": getattr(analisis, 'coordenada_y', ''),
                    "elevacion_msnm": getattr(analisis, 'elevacion_msnm', None),
                    
                    # Información del productor
                    "nombre_productor": getattr(analisis, 'nombre_productor', ''),
                    "tel_productor": getattr(analisis, 'tel_productor', ''),
                    "correo_productor": getattr(analisis, 'correo_productor', ''),
                    
                    # Información del técnico
                    "nombre_tecnico": getattr(analisis, 'nombre_tecnico', ''),
                    "tel_tecnico": getattr(analisis, 'tel_tecnico', ''),
                    "correo_tecnico": getattr(analisis, 'correo_tecnico', ''),
                    
                    # Información agrícola
                    "cultivo_anterior": getattr(analisis, 'cultivo_anterior', ''),
                    "cultivo_establecer": getattr(analisis, 'cultivo_establecer', ''),
                    "manejo": getattr(analisis, 'manejo', ''),
                    "tipo_vegetacion": getattr(analisis, 'tipo_vegetacion', ''),
                    "parcela": getattr(analisis, 'parcela', ''),
                    
                    # Información de muestreo
                    "profundidad_muestreo": getattr(analisis, 'profundidad_muestreo', ''),
                    "fecha_muestreo": str(analisis.fecha_muestreo) if getattr(analisis, 'fecha_muestreo', None) else '',
                    "muestra": getattr(analisis, 'muestra', ''),
                    "reemplazo": getattr(analisis, 'reemplazo', ''),
                    
                    # Información administrativa
                    "numero": getattr(analisis, 'numero', None),
                    "clave_estatal": getattr(analisis, 'clave_estatal', None),
                    "recuento_curp_renapo": getattr(analisis, 'recuento_curp_renapo', None),
                    "extraccion_edo": getattr(analisis, 'extraccion_edo', ''),
                    "clave": getattr(analisis, 'clave', ''),
                    "ddr": getattr(analisis, 'ddr', ''),
                    "cader": getattr(analisis, 'cader', ''),
                    "nombre_revisor": getattr(analisis, 'nombre_revisor', ''),
                    
                    # Fechas específicas de validados
                    "fecha_validacion": str(analisis.fecha_validacion) if getattr(analisis, 'fecha_validacion', None) else '',
                    "fecha_creacion": str(analisis.fecha_creacion) if getattr(analisis, 'fecha_creacion', None) else '',
                }
                
                datos_procesados.append(dato)
            
            return {
                "success": True,
                "message": f"Se encontraron {len(analisis_validados)} análisis validados",
                "total_registros": len(analisis_validados),
                "usuario_info": {
                    "id": usuario.ID_user,
                    "correo": usuario.correo,
                    "nombre": usuario.nombre or '',
                    "apellido": usuario.apellido or ''
                },
                "datos": datos_procesados
            }
            
        except Exception as e:
            print(f"Error al obtener análisis validados detallados: {str(e)}")
            return {
                "success": False,
                "message": f"Error al obtener datos: {str(e)}",
                "total_registros": 0,
                "datos": []
            }

    def obtener_todos_los_validados_detallados(self) -> dict:
        """
        Obtiene TODOS los análisis validados de TODOS los usuarios con información detallada.
        Incluye información del usuario propietario de cada registro.
        Optimizado para exportación y visualización completa.
        """
        try:
            # Obtener TODOS los análisis validados con información del usuario
            analisis_validados = (
                self.db.query(AnalisisSuelosValidados, Users)
                .join(Users, AnalisisSuelosValidados.user_id_FK == Users.ID_user)
                .order_by(
                    Users.correo.asc(),  # Ordenar por usuario primero
                    AnalisisSuelosValidados.fecha_validacion.desc()  # Luego por fecha de validación
                )
                .all()
            )
            
            if not analisis_validados:
                return {
                    "success": False,
                    "message": "No hay análisis validados en el sistema",
                    "total_registros": 0,
                    "total_usuarios": 0,
                    "datos": []
                }
            
            # Procesar todos los datos con manejo seguro de valores None
            datos_procesados = []
            usuarios_unicos = set()
            
            for i, (analisis, usuario) in enumerate(analisis_validados, 1):
                usuarios_unicos.add(usuario.correo)
                
                dato = {
                    # Información básica del registro
                    "numero_registro": i,
                    "id": getattr(analisis, 'id', None),
                    
                    # Información del usuario propietario
                    "user_id": usuario.ID_user,
                    "usuario_correo": usuario.correo,
                    "usuario_nombre": getattr(usuario, 'nombre', '') or '',
                    "usuario_apellido": getattr(usuario, 'apellido', '') or '',
                    "usuario_nombre_completo": f"{getattr(usuario, 'nombre', '') or ''} {getattr(usuario, 'apellido', '') or ''}".strip(),
                    "usuario_rol": getattr(usuario, 'rol_id_FK', None),
                    
                    # Información geográfica
                    "municipio_id_FK": getattr(analisis, 'municipio_id_FK', None),
                    "municipio_cuadernillo": getattr(analisis, 'municipio_cuadernillo', ''),
                    "localidad_cuadernillo": getattr(analisis, 'localidad_cuadernillo', ''),
                    "clave_municipio": getattr(analisis, 'clave_municipio', None),
                    "clave_munip": getattr(analisis, 'clave_munip', ''),
                    "clave_localidad": getattr(analisis, 'clave_localidad', ''),
                    "estado_cuadernillo": getattr(analisis, 'estado_cuadernillo', ''),
                    
                    # Coordenadas y ubicación
                    "coordenada_x": getattr(analisis, 'coordenada_x', ''),
                    "coordenada_y": getattr(analisis, 'coordenada_y', ''),
                    "elevacion_msnm": getattr(analisis, 'elevacion_msnm', None),
                    
                    # Información del productor
                    "nombre_productor": getattr(analisis, 'nombre_productor', ''),
                    "tel_productor": getattr(analisis, 'tel_productor', ''),
                    "correo_productor": getattr(analisis, 'correo_productor', ''),
                    
                    # Información del técnico
                    "nombre_tecnico": getattr(analisis, 'nombre_tecnico', ''),
                    "tel_tecnico": getattr(analisis, 'tel_tecnico', ''),
                    "correo_tecnico": getattr(analisis, 'correo_tecnico', ''),
                    
                    # Información agrícola
                    "cultivo_anterior": getattr(analisis, 'cultivo_anterior', ''),
                    "cultivo_establecer": getattr(analisis, 'cultivo_establecer', ''),
                    "manejo": getattr(analisis, 'manejo', ''),
                    "tipo_vegetacion": getattr(analisis, 'tipo_vegetacion', ''),
                    "parcela": getattr(analisis, 'parcela', ''),
                    
                    # Información de muestreo
                    "profundidad_muestreo": getattr(analisis, 'profundidad_muestreo', ''),
                    "fecha_muestreo": str(analisis.fecha_muestreo) if getattr(analisis, 'fecha_muestreo', None) else '',
                    "muestra": getattr(analisis, 'muestra', ''),
                    "reemplazo": getattr(analisis, 'reemplazo', ''),
                    
                    # Información administrativa
                    "numero": getattr(analisis, 'numero', None),
                    "clave_estatal": getattr(analisis, 'clave_estatal', None),
                    "recuento_curp_renapo": getattr(analisis, 'recuento_curp_renapo', None),
                    "extraccion_edo": getattr(analisis, 'extraccion_edo', ''),
                    "clave": getattr(analisis, 'clave', ''),
                    "ddr": getattr(analisis, 'ddr', ''),
                    "cader": getattr(analisis, 'cader', ''),
                    "nombre_revisor": getattr(analisis, 'nombre_revisor', ''),
                    
                    # Fechas específicas de validados
                    "fecha_validacion": str(analisis.fecha_validacion) if getattr(analisis, 'fecha_validacion', None) else '',
                    "fecha_creacion": str(analisis.fecha_creacion) if getattr(analisis, 'fecha_creacion', None) else '',
                }
                
                datos_procesados.append(dato)
            
            return {
                "success": True,
                "message": f"Se encontraron {len(analisis_validados)} análisis validados de {len(usuarios_unicos)} usuarios",
                "total_registros": len(analisis_validados),
                "total_usuarios": len(usuarios_unicos),
                "usuarios_con_validados": list(usuarios_unicos),
                "datos": datos_procesados
            }
            
        except Exception as e:
            print(f"Error al obtener todos los análisis validados detallados: {str(e)}")
            return {
                "success": False,
                "message": f"Error al obtener datos: {str(e)}",
                "total_registros": 0,
                "total_usuarios": 0,
                "datos": []
            }

    def eliminar_analisis_validados_por_correo(self, correo_usuario: str) -> dict:
        """
        Elimina TODOS los análisis de suelos validados asociados a un usuario por su correo.
        Busca todos los registros en analisis_suelos_validados que tengan user_id_FK = usuario.ID_user
        y los elimina permanentemente.
        
        Args:
            correo_usuario (str): Correo electrónico del usuario
            
        Returns:
            dict: Resultado de la operación de eliminación
        """
        try:
            print(f"=== ELIMINANDO ANÁLISIS DE SUELOS VALIDADOS PARA: {correo_usuario} ===")
            
            # Buscar usuario por correo
            usuario = self.db.query(Users).filter(
                Users.correo == correo_usuario.strip().lower()
            ).first()
            
            if not usuario:
                print(f"Usuario no encontrado: {correo_usuario}")
                return {
                    "success": False,
                    "message": f"Usuario con correo '{correo_usuario}' no encontrado",
                    "eliminados": 0
                }
            
            print(f"Usuario encontrado: ID={usuario.ID_user}, correo={usuario.correo}")
            
            # Contar cuántos análisis validados tiene el usuario
            total_validados = (
                self.db.query(AnalisisSuelosValidados)
                .filter(AnalisisSuelosValidados.user_id_FK == usuario.ID_user)
                .count()
            )
            
            print(f"Análisis de suelos validados encontrados para eliminar: {total_validados}")
            
            if total_validados == 0:
                return {
                    "success": True,
                    "message": "El usuario no tiene análisis de suelos validados para eliminar",
                    "usuario": correo_usuario,
                    "usuario_id": usuario.ID_user,
                    "eliminados": 0
                }
            
            # ELIMINAR todos los análisi validados del usuario
            registros_eliminados = (
                self.db.query(AnalisisSuelosValidados)
                .filter(AnalisisSuelosValidados.user_id_FK == usuario.ID_user)
                .delete(synchronize_session=False)
            )
            
            # Hacer commit de la eliminación
            self.db.commit()
            
            print(f"✅ ELIMINACIÓN DE SUELOS VALIDADOS COMPLETADA:")
            print(f"   - Usuario: {correo_usuario} (ID: {usuario.ID_user})")
            print(f"   - Registros eliminados: {registros_eliminados}")
            
            return {
                "success": True,
                "message": f"Se eliminaron {registros_eliminados} análisis de suelos validados exitosamente",
                "usuario": correo_usuario,
                "usuario_id": usuario.ID_user,
                "eliminados": registros_eliminados
            }
            
        except Exception as e:
            print(f"❌ Error en eliminación de suelos validados: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            
            # Rollback en caso de error
            self.db.rollback()
            return {
                "success": False,
                "message": f"Error al eliminar análisis de suelos validados: {str(e)}",
                "usuario": correo_usuario,
                "eliminados": 0,
                "error": str(e)
            }