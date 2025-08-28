# src/AnalisisSuelosPendientes/application/comentario_invalido_service.py
from sqlalchemy.orm import Session
from typing import Optional
from src.AnalisisSuelosPendientes.infrastructure.analisis_suelos_model import AnalisisSuelosPendientes
from src.Users.infrastructure.users_model import Users


class ComentarioInvalidoService:
    
    @staticmethod
    def obtener_comentario_por_correo(db: Session, correo_usuario: str) -> dict:
        """
        Obtiene el comentario inválido de un usuario por su correo electrónico.
        
        Args:
            db: Sesión de base de datos
            correo_usuario: Correo electrónico del usuario
            
        Returns:
            dict: Información del comentario inválido del usuario
            
        Raises:
            ValueError: Si el usuario no existe o no tiene comentarios inválidos
        """
        
        # Verificar que el usuario existe
        usuario = db.query(Users).filter(Users.correo == correo_usuario).first()
        
        if not usuario:
            raise ValueError(f"Usuario con correo '{correo_usuario}' no encontrado")
        
        # Buscar el primer registro con comentario inválido del usuario
        # Se asume que todos los registros de un usuario tienen el mismo comentario
        analisis_con_comentario = db.query(AnalisisSuelosPendientes).filter(
            AnalisisSuelosPendientes.user_id_FK == usuario.ID_user,
            AnalisisSuelosPendientes.comentario_invalido.is_not(None),
            AnalisisSuelosPendientes.comentario_invalido != ""
        ).first()
        
        if not analisis_con_comentario:
            raise ValueError(f"El usuario '{correo_usuario}' no tiene comentarios inválidos registrados")
        
        # Contar total de registros con comentario inválido
        total_registros_con_comentario = db.query(AnalisisSuelosPendientes).filter(
            AnalisisSuelosPendientes.user_id_FK == usuario.ID_user,
            AnalisisSuelosPendientes.comentario_invalido.is_not(None),
            AnalisisSuelosPendientes.comentario_invalido != ""
        ).count()
        
        return {
            "user_id": usuario.ID_user,
            "correo_usuario": usuario.correo,
            "nombre_usuario": f"{usuario.nombre or ''} {usuario.apellido or ''}".strip() or usuario.correo,
            "comentario_invalido": analisis_con_comentario.comentario_invalido,
            "fecha_comentario": analisis_con_comentario.fecha_creacion,
            "total_registros_afectados": total_registros_con_comentario
        }