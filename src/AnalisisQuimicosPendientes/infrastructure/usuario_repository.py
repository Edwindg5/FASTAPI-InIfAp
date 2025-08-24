# src/AnalisisQuimicosPendientes/infrastructure/usuario_repository.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from src.AnalisisQuimicosPendientes.infrastructure.analisis_quimicos_model import (
    AnalisisQuimicosPendientes,
)
from src.Users.infrastructure.users_model import Users


class UsuarioRepository:
    """
    Repositorio para operaciones de consulta relacionadas con usuarios y sus análisis químicos.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def obtener_usuarios_con_registros_pendientes(self) -> List[Dict[str, Any]]:
        """
        Obtiene todos los usuarios que tienen al menos un registro pendiente.
        
        Returns:
            Lista de usuarios con estadísticas de sus registros
        """
        # Subconsulta para estadísticas por usuario
        estadisticas_subq = (
            self.db.query(
                AnalisisQuimicosPendientes.user_id_FK.label('user_id'),
                func.count(AnalisisQuimicosPendientes.id).label("total_registros"),
                func.min(AnalisisQuimicosPendientes.fecha_creacion).label("primera_fecha"),
                func.max(AnalisisQuimicosPendientes.fecha_creacion).label("ultima_fecha"),
                func.sum(
                    func.case(
                        [(AnalisisQuimicosPendientes.estatus == "pendiente", 1)],
                        else_=0
                    )
                ).label("count_pendientes"),
                func.sum(
                    func.case(
                        [(AnalisisQuimicosPendientes.estatus == "invalidado", 1)],
                        else_=0
                    )
                ).label("count_invalidados"),
                func.sum(
                    func.case(
                        [(AnalisisQuimicosPendientes.estatus == "procesado", 1)],
                        else_=0
                    )
                ).label("count_procesados")
            )
            .filter(AnalisisQuimicosPendientes.user_id_FK.isnot(None))
            .group_by(AnalisisQuimicosPendientes.user_id_FK)
            .subquery()
        )
        
        # Consulta principal con JOIN
        resultado = (
            self.db.query(
                Users.ID_user,
                Users.nombre,
                Users.apellido,
                Users.correo,
                estadisticas_subq.c.total_registros,
                estadisticas_subq.c.primera_fecha,
                estadisticas_subq.c.ultima_fecha,
                estadisticas_subq.c.count_pendientes,
                estadisticas_subq.c.count_invalidados,
                estadisticas_subq.c.count_procesados
            )
            .join(estadisticas_subq, Users.ID_user == estadisticas_subq.c.user_id)
            .filter(estadisticas_subq.c.count_pendientes > 0)  # Solo con registros pendientes
            .order_by(estadisticas_subq.c.ultima_fecha.desc())
            .all()
        )
        
        return resultado
    
    def obtener_registros_usuario(self, user_id: int) -> List[AnalisisQuimicosPendientes]:
        """
        Obtiene todos los registros de análisis químicos de un usuario específico.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de registros de análisis químicos
        """
        return (
            self.db.query(AnalisisQuimicosPendientes)
            .filter(AnalisisQuimicosPendientes.user_id_FK == user_id)
            .order_by(AnalisisQuimicosPendientes.fecha_creacion.desc())
            .all()
        )
    
    def obtener_usuario_por_id(self, user_id: int) -> Optional[Users]:
        """
        Obtiene un usuario por su ID.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Usuario o None si no existe
        """
        return self.db.query(Users).filter(Users.ID_user == user_id).first()
    
    def verificar_usuario_tiene_registros(self, user_id: int) -> bool:
        """
        Verifica si un usuario tiene registros de análisis químicos.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            True si tiene registros, False en caso contrario
        """
        count = (
            self.db.query(func.count(AnalisisQuimicosPendientes.id))
            .filter(AnalisisQuimicosPendientes.user_id_FK == user_id)
            .scalar()
        )
        
        return count > 0
    
    def obtener_estadisticas_usuario(self, user_id: int) -> Dict[str, int]:
        """
        Obtiene estadísticas detalladas de los registros de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Diccionario con estadísticas
        """
        estadisticas = (
            self.db.query(
                func.count(AnalisisQuimicosPendientes.id).label("total"),
                func.sum(
                    func.case(
                        [(AnalisisQuimicosPendientes.estatus == "pendiente", 1)],
                        else_=0
                    )
                ).label("pendientes"),
                func.sum(
                    func.case(
                        [(AnalisisQuimicosPendientes.estatus == "invalidado", 1)],
                        else_=0
                    )
                ).label("invalidados"),
                func.sum(
                    func.case(
                        [(AnalisisQuimicosPendientes.estatus == "procesado", 1)],
                        else_=0
                    )
                ).label("procesados")
            )
            .filter(AnalisisQuimicosPendientes.user_id_FK == user_id)
            .first()
        )
        
        return {
            "total": int(estadisticas.total or 0),
            "pendientes": int(estadisticas.pendientes or 0),
            "invalidados": int(estadisticas.invalidados or 0),
            "procesados": int(estadisticas.procesados or 0)
        }
    
    def buscar_usuarios_por_criterio(self, criterio: str) -> List[Users]:
        """
        Busca usuarios por nombre, apellido o correo.
        
        Args:
            criterio: Texto a buscar
            
        Returns:
            Lista de usuarios que coinciden
        """
        criterio_lower = f"%{criterio.lower()}%"
        
        return (
            self.db.query(Users)
            .filter(
                or_(
                    func.lower(Users.nombre).like(criterio_lower),
                    func.lower(Users.apellido).like(criterio_lower),
                    func.lower(Users.correo).like(criterio_lower)
                )
            )
            .all()
        )