# src/AnalisisSuelosValidados/application/analisis_suelos_validados_service.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
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

    def obtener_todos_validados(self) -> List[AnalisisSuelosValidados]:
        """Obtiene todos los análisis de suelos validados"""
        return self.db.query(AnalisisSuelosValidados).all()

    def obtener_validados_por_correo(self, correo_usuario: str) -> List[AnalisisSuelosValidados]:
        """Obtiene análisis validados por correo de usuario"""
        # Buscar usuario por correo
        usuario = self.db.query(Users).filter(Users.correo == correo_usuario).first()
        if not usuario:
            return []
        
        return (
            self.db.query(AnalisisSuelosValidados)
            .filter(AnalisisSuelosValidados.user_id_FK == usuario.ID_user)
            .all()
        )

    def obtener_estadisticas_validados(self) -> dict:
        """Obtiene estadísticas de los análisis validados"""
        total = self.db.query(AnalisisSuelosValidados).count()
        
        # Análisis por municipio
        por_municipio = (
            self.db.query(
                AnalisisSuelosValidados.municipio_cuadernillo,
                func.count(AnalisisSuelosValidados.id).label('total')
            )
            .group_by(AnalisisSuelosValidados.municipio_cuadernillo)
            .all()
        )
        
        return {
            "total_validados": total,
            "por_municipio": [{"municipio": m[0], "total": m[1]} for m in por_municipio]
        }

    # NUEVOS MÉTODOS PARA ANÁLISIS PENDIENTES
    
    def obtener_todos_pendientes(self) -> List[dict]:
        """Obtiene todos los análisis pendientes de todos los usuarios"""
        try:
            # Hacer join entre análisis pendientes y usuarios
            resultados = (
                self.db.query(AnalisisSuelosPendientes, Users)
                .join(Users, AnalisisSuelosPendientes.user_id_FK == Users.ID_user)
                .all()
            )
            
            return [
                {
                    "analisis": analisis,
                    "usuario": usuario
                }
                for analisis, usuario in resultados
            ]
        except Exception as e:
            print(f"Error al obtener análisis pendientes: {str(e)}")
            return []

    def obtener_pendientes_por_correo(self, correo_usuario: str) -> List[dict]:
        """Obtiene análisis pendientes de un usuario específico por correo"""
        try:
            # Buscar usuario por correo
            usuario = self.db.query(Users).filter(Users.correo == correo_usuario).first()
            if not usuario:
                return []
            
            # Obtener análisis pendientes del usuario
            analisis_pendientes = (
                self.db.query(AnalisisSuelosPendientes)
                .filter(AnalisisSuelosPendientes.user_id_FK == usuario.ID_user)
                .all()
            )
            
            return [
                {
                    "analisis": analisis,
                    "usuario": usuario
                }
                for analisis in analisis_pendientes
            ]
        except Exception as e:
            print(f"Error al obtener análisis pendientes por correo: {str(e)}")
            return []

    def contar_pendientes_por_usuario(self) -> List[dict]:
        """Obtiene el conteo de análisis pendientes agrupados por usuario"""
        try:
            resultados = (
                self.db.query(
                    Users.correo,
                    Users.nombre,
                    Users.apellido,
                    func.count(AnalisisSuelosPendientes.id).label('total_pendientes')
                )
                .join(AnalisisSuelosPendientes, Users.ID_user == AnalisisSuelosPendientes.user_id_FK)
                .group_by(Users.correo, Users.nombre, Users.apellido)
                .having(func.count(AnalisisSuelosPendientes.id) > 0)
                .all()
            )
            
            return [
                {
                    "correo": resultado.correo,
                    "nombre": resultado.nombre,
                    "apellido": resultado.apellido,
                    "total_pendientes": resultado.total_pendientes
                }
                for resultado in resultados
            ]
        except Exception as e:
            print(f"Error al contar pendientes por usuario: {str(e)}")
            return []

    def obtener_estadisticas_pendientes(self) -> dict:
        """Obtiene estadísticas generales de análisis pendientes"""
        try:
            total_pendientes = self.db.query(AnalisisSuelosPendientes).count()
            
            # Pendientes por municipio
            por_municipio = (
                self.db.query(
                    AnalisisSuelosPendientes.municipio_cuadernillo,
                    func.count(AnalisisSuelosPendientes.id).label('total')
                )
                .group_by(AnalisisSuelosPendientes.municipio_cuadernillo)
                .all()
            )
            
            # Usuarios con pendientes
            usuarios_con_pendientes = (
                self.db.query(func.count(func.distinct(AnalisisSuelosPendientes.user_id_FK)))
                .scalar()
            )
            
            return {
                "total_pendientes": total_pendientes,
                "usuarios_con_pendientes": usuarios_con_pendientes,
                "por_municipio": [{"municipio": m[0], "total": m[1]} for m in por_municipio]
            }
        except Exception as e:
            print(f"Error al obtener estadísticas de pendientes: {str(e)}")
            return {
                "total_pendientes": 0,
                "usuarios_con_pendientes": 0,
                "por_municipio": []
            }