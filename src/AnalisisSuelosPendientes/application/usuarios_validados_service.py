import pandas as pd
import io
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from src.AnalisisSuelosValidados.infrastructure.analisis_suelos_validados_model import AnalisisSuelosValidados
from src.Users.infrastructure.users_model import Users

class UsuariosValidadosService:
   
   @staticmethod
   def get_usuarios_con_validados(db: Session) -> Dict[str, Any]:
       """
       Obtiene todos los usuarios que tienen análisis de suelos validados con formato simplificado
       """
       try:
           print("Obteniendo usuarios con análisis validados...")
           
           usuarios_query = (
               db.query(
                   Users.ID_user.label('user_id'),
                   Users.nombre.label('nombre_usuario'),
                   Users.apellido.label('apellido_usuario'),
                   Users.correo.label('correo_usuario'),
                   AnalisisSuelosValidados.nombre_archivo,
                   func.max(AnalisisSuelosValidados.fecha_validacion).label('fecha_validacion'),
                   func.count(AnalisisSuelosValidados.id).label('total_registros')
               )
               .join(AnalisisSuelosValidados, Users.ID_user == AnalisisSuelosValidados.user_id_FK)
               .group_by(
                   Users.ID_user, 
                   Users.nombre, 
                   Users.apellido, 
                   Users.correo,
                   AnalisisSuelosValidados.nombre_archivo
               )
               .order_by(
                   Users.nombre.asc(),
                   AnalisisSuelosValidados.nombre_archivo.asc()
               )
           ).all()
           
           usuarios_validados_simple = []
           
           print(f"Se encontraron {len(usuarios_query)} registros de archivos validados")
           
           for usuario in usuarios_query:
               # Crear nombre completo
               nombre_completo = f"{usuario.nombre_usuario or ''} {usuario.apellido_usuario or ''}".strip()
               if not nombre_completo:
                   nombre_completo = usuario.correo_usuario.split('@')[0]
               
               usuario_data = {
                   'nombre_usuario': nombre_completo,
                   'estatus': 'validado',
                   'fecha': usuario.fecha_validacion,
                   'nombre_archivo': usuario.nombre_archivo
               }
               
               usuarios_validados_simple.append(usuario_data)
               
               print(f"Usuario {nombre_completo}: archivo '{usuario.nombre_archivo}' - {usuario.total_registros} registros")
           
           # Contar usuarios únicos
           usuarios_unicos = len(set(usuario.user_id for usuario in usuarios_query))
           
           return {
               'total_usuarios_con_validados': usuarios_unicos,
               'usuarios': usuarios_validados_simple
           }
           
       except Exception as e:
           error_msg = f"Error obteniendo usuarios con validados: {str(e)}"
           print(f"Error: {error_msg}")
           raise Exception(error_msg)
   
   @staticmethod
   def get_analisis_validados_por_correo(db: Session, correo_usuario: str) -> Dict[str, Any]:
       """
       Obtiene todos los análisis validados de un usuario específico por su correo
       """
       try:
           print(f"Buscando análisis validados para usuario: {correo_usuario}")
           
           # 1. Verificar que el usuario existe
           usuario = db.query(Users).filter(Users.correo == correo_usuario).first()
           if not usuario:
               raise ValueError(f"No se encontró el usuario con correo: {correo_usuario}")
           
           # 2. Obtener todos los análisis validados del usuario
           analisis_validados = (
               db.query(AnalisisSuelosValidados)
               .filter(AnalisisSuelosValidados.user_id_FK == usuario.ID_user)
               .order_by(AnalisisSuelosValidados.fecha_validacion.desc())
           ).all()
           
           # 3. Obtener municipios involucrados
           municipios = (
               db.query(AnalisisSuelosValidados.municipio_cuadernillo)
               .filter(
                   AnalisisSuelosValidados.user_id_FK == usuario.ID_user,
                   AnalisisSuelosValidados.municipio_cuadernillo.isnot(None),
                   AnalisisSuelosValidados.municipio_cuadernillo != ''
               )
               .distinct()
           ).all()
           
           municipios_list = [mun[0] for mun in municipios if mun[0]]
           
           # 4. Preparar información del usuario
           nombre_completo = f"{usuario.nombre or ''} {usuario.apellido or ''}".strip()
           if not nombre_completo:
               nombre_completo = correo_usuario.split('@')[0]
           
           usuario_info = {
               'user_id': usuario.ID_user,
               'nombre_completo': nombre_completo,
               'correo': usuario.correo
           }
           
           # 5. Preparar detalles de análisis
           analisis_detalles = []
           for analisis in analisis_validados:
               detalle = {
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
                   'estatus': 'validado',
                   'nombre_revisor': analisis.nombre_revisor
               }
               analisis_detalles.append(detalle)
           
           # 6. Fecha del último análisis
           ultimo_analisis_fecha = None
           if analisis_validados:
               ultimo_analisis_fecha = max(
                   analisis.fecha_validacion for analisis in analisis_validados 
                   if analisis.fecha_validacion
               )
           
           total_validados = len(analisis_validados)
           message = f"Se encontraron {total_validados} análisis validados para {correo_usuario}"
           
           if total_validados == 0:
               message = f"El usuario {correo_usuario} no tiene análisis validados"
           
           print(message)
           
           return {
               'usuario_info': usuario_info,
               'total_validados': total_validados,
               'analisis_validados': analisis_detalles,
               'municipios_involucrados': municipios_list,
               'ultimo_analisis_fecha': ultimo_analisis_fecha,
               'message': message
           }
           
       except ValueError as ve:
           raise ve
       except Exception as e:
           error_msg = f"Error obteniendo análisis validados para {correo_usuario}: {str(e)}"
           print(f"Error: {error_msg}")
           raise Exception(error_msg)