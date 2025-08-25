# src/AnalisisSuelosPendientes/application/usuarios_pendientes_service.py

import pandas as pd
import io
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from src.AnalisisSuelosValidados.infrastructure.analisis_suelos_validados_model import AnalisisSuelosValidados
from src.AnalisisSuelosPendientes.infrastructure.analisis_suelos_model import AnalisisSuelosPendientes
from src.Users.infrastructure.users_model import Users

class UsuariosPendientesService:
    

    @staticmethod
    def generar_excel_por_usuario(db: Session, user_id: int) -> bytes:
        """
        Genera un archivo Excel con todos los análisis pendientes de un usuario específico
        """
        try:
            print(f"Generando Excel para usuario ID: {user_id}")
            
            # 1. Verificar que el usuario existe
            usuario = db.query(Users).filter(Users.ID_user == user_id).first()
            if not usuario:
                raise ValueError(f"No se encontró el usuario con ID: {user_id}")
            
            # 2. Obtener todos los análisis pendientes del usuario
            analisis_pendientes = (
                db.query(AnalisisSuelosPendientes)
                .filter(
                    AnalisisSuelosPendientes.user_id_FK == user_id,
                    AnalisisSuelosPendientes.estatus == 'pendiente'
                )
                .order_by(AnalisisSuelosPendientes.fecha_creacion.desc())
            ).all()
            
            if not analisis_pendientes:
                raise ValueError(f"El usuario {usuario.correo} no tiene análisis pendientes")
            
            print(f"Se encontraron {len(analisis_pendientes)} análisis pendientes para {usuario.correo}")
            
            # 3. Preparar datos para Excel con orden lógico de columnas
            data_rows = []
            
            for analisis in analisis_pendientes:
                row_data = {
                    # Información básica
                    'ID': analisis.id,
                    'Número': analisis.numero,
                    'Estatus': analisis.estatus,
                    'Fecha Creación': analisis.fecha_creacion.strftime('%d/%m/%Y %H:%M') if analisis.fecha_creacion else '',
                    
                    # Información geográfica
                    'Clave Estatal': analisis.clave_estatal,
                    'Estado Cuadernillo': analisis.estado_cuadernillo,
                    'Clave Municipio': analisis.clave_municipio,
                    'Clave Munip': analisis.clave_munip,
                    'Municipio Cuadernillo': analisis.municipio_cuadernillo,
                    'Clave Localidad': analisis.clave_localidad,
                    'Localidad Cuadernillo': analisis.localidad_cuadernillo,
                    
                    # Información técnica
                    'Recuento CURP Renapo': analisis.recuento_curp_renapo,
                    'Extracción Edo': analisis.extraccion_edo,
                    'Clave': analisis.clave,
                    'DDR': analisis.ddr,
                    'CADER': analisis.cader,
                    
                    # Coordenadas y ubicación
                    'Coordenada X': analisis.coordenada_x,
                    'Coordenada Y': analisis.coordenada_y,
                    'Elevación MSNM': analisis.elevacion_msnm,
                    
                    # Información de muestreo
                    'Profundidad Muestreo': analisis.profundidad_muestreo,
                    'Fecha Muestreo': analisis.fecha_muestreo.strftime('%d/%m/%Y') if analisis.fecha_muestreo else '',
                    'Parcela': analisis.parcela,
                    'Cultivo Anterior': analisis.cultivo_anterior,
                    'Cultivo a Establecer': analisis.cultivo_establecer,
                    'Manejo': analisis.manejo,
                    'Tipo Vegetación': analisis.tipo_vegetacion,
                    
                    # Información del técnico
                    'Nombre Técnico': analisis.nombre_tecnico,
                    'Tel Técnico': analisis.tel_tecnico,
                    'Correo Técnico': analisis.correo_tecnico,
                    
                    # Información del productor
                    'Nombre Productor': analisis.nombre_productor,
                    'Tel Productor': analisis.tel_productor,
                    'Correo Productor': analisis.correo_productor,
                    
                    # Información final
                    'Muestra': analisis.muestra,
                    'Reemplazo': analisis.reemplazo,
                    'Nombre Revisor': analisis.nombre_revisor,
                    
                    # Comentarios (si existen)
                    'Comentario Inválido': analisis.comentario_invalido,
                    
                    # FK de referencia
                    'Municipio ID FK': analisis.municipio_id_FK,
                    'User ID FK': analisis.user_id_FK
                }
                
                data_rows.append(row_data)
            
            # 4. Crear DataFrame
            df = pd.DataFrame(data_rows)
            
            # 5. Información del usuario para el nombre del archivo y hoja
            nombre_completo = f"{usuario.nombre or ''} {usuario.apellido or ''}".strip()
            if not nombre_completo:
                nombre_completo = usuario.correo.split('@')[0]  # Usar parte del correo si no hay nombre
            
            fecha_generacion = datetime.now().strftime('%d%m%Y_%H%M')
            
            # 6. Crear archivo Excel en memoria
            excel_buffer = io.BytesIO()
            
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # Crear hoja principal con datos
                sheet_name = f"Pendientes_{user_id}"
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Obtener la hoja para darle formato
                workbook = writer.book
                worksheet = workbook[sheet_name]
                
                # Ajustar ancho de columnas automáticamente
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)  # Máximo 50 caracteres
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Crear hoja de resumen
                resumen_data = {
                    'Información del Reporte': [
                        'Usuario ID', 'Nombre Usuario', 'Correo Usuario', 
                        'Total Registros', 'Fecha Generación', 'Estado de Registros'
                    ],
                    'Valores': [
                        user_id, nombre_completo, usuario.correo,
                        len(analisis_pendientes), datetime.now().strftime('%d/%m/%Y %H:%M'), 'Pendientes'
                    ]
                }
                
                resumen_df = pd.DataFrame(resumen_data)
                resumen_df.to_excel(writer, sheet_name='Resumen', index=False)
            
            excel_buffer.seek(0)
            excel_bytes = excel_buffer.getvalue()
            excel_buffer.close()
            
            print(f"Excel generado exitosamente: {len(excel_bytes)} bytes")
            print(f"Archivo incluye {len(analisis_pendientes)} registros de {usuario.correo}")
            
            return excel_bytes
            
        except ValueError as ve:
            raise ve
        except Exception as e:
            error_msg = f"Error generando Excel para usuario {user_id}: {str(e)}"
            print(f"Error: {error_msg}")
            raise Exception(error_msg)
        
        
    @staticmethod
    def get_usuarios_con_pendientes(db: Session) -> Dict[str, Any]:
       """
       Obtiene todos los usuarios que tienen análisis de suelos PENDIENTES con estadísticas
       """
       try:
           print("Obteniendo usuarios con análisis pendientes...")
           usuarios_query = (
               db.query(
                   Users.ID_user.label('user_id'),
                   Users.nombre.label('nombre_usuario'),
                   Users.apellido.label('apellido_usuario'),
                   Users.correo.label('correo_usuario'),
                   func.count(AnalisisSuelosPendientes.id).label('total_pendientes'),
                   func.max(AnalisisSuelosPendientes.fecha_creacion).label('ultimo_analisis_fecha'),
                   func.max(AnalisisSuelosPendientes.nombre_archivo).label('nombre_archivo')
                   )
               .join(AnalisisSuelosPendientes, Users.ID_user == AnalisisSuelosPendientes.user_id_FK)
               .filter(AnalisisSuelosPendientes.estatus == 'pendiente')  # Solo pendientes
               .group_by(
                   Users.ID_user, 
                   Users.nombre, 
                   Users.apellido, 
                   Users.correo
                   )
               .order_by(func.count(AnalisisSuelosPendientes.id).desc())
               ).all()
           usuarios_con_pendientes = []
           total_usuarios = len(usuarios_query)
           print(f"Se encontraron {total_usuarios} usuarios con análisis pendientes")
        
           for usuario in usuarios_query:
            usuario_data = {
                'user_id': usuario.user_id,
                'nombre_usuario': usuario.nombre_usuario,
                'correo_usuario': usuario.correo_usuario,
                'estatus': 'pendiente',
                'nombre_archivo': usuario.nombre_archivo,
                'total_pendientes': usuario.total_pendientes,
                'ultimo_analisis_fecha': usuario.ultimo_analisis_fecha,
                'fecha_validacion': None  # Los pendientes no tienen fecha de validación
            }
            
            usuarios_con_pendientes.append(usuario_data)
            
            print(f"Usuario {usuario.correo_usuario}: {usuario.total_pendientes} registros pendientes")
        
           return {
            'total_usuarios_con_pendientes': total_usuarios,
            'usuarios': usuarios_con_pendientes
        }
        
       except Exception as e:
        error_msg = f"Error obteniendo usuarios con pendientes: {str(e)}"
        print(f"Error: {error_msg}")
        raise Exception(error_msg)
    
    @staticmethod
    def generar_excel_por_usuario(db: Session, user_id: int) -> bytes:
        """
        Genera un archivo Excel con todos los análisis pendientes de un usuario específico
        """
        try:
            print(f"Generando Excel para usuario ID: {user_id}")
            
            # 1. Verificar que el usuario existe
            usuario = db.query(Users).filter(Users.ID_user == user_id).first()
            if not usuario:
                raise ValueError(f"No se encontró el usuario con ID: {user_id}")
            
            # 2. Obtener todos los análisis pendientes del usuario
            analisis_pendientes = (
                db.query(AnalisisSuelosPendientes)
                .filter(
                    AnalisisSuelosPendientes.user_id_FK == user_id,
                    AnalisisSuelosPendientes.estatus == 'pendiente'
                )
                .order_by(AnalisisSuelosPendientes.fecha_creacion.desc())
            ).all()
            
            if not analisis_pendientes:
                raise ValueError(f"El usuario {usuario.correo} no tiene análisis pendientes")
            
            print(f"Se encontraron {len(analisis_pendientes)} análisis pendientes para {usuario.correo}")
            
            # 3. Preparar datos para Excel con orden lógico de columnas
            data_rows = []
            
            for analisis in analisis_pendientes:
                row_data = {
                    # Información básica
                    'ID': analisis.id,
                    'Número': analisis.numero,
                    'Estatus': analisis.estatus,
                    'Fecha Creación': analisis.fecha_creacion.strftime('%d/%m/%Y %H:%M') if analisis.fecha_creacion else '',
                    
                    # Información geográfica
                    'Clave Estatal': analisis.clave_estatal,
                    'Estado Cuadernillo': analisis.estado_cuadernillo,
                    'Clave Municipio': analisis.clave_municipio,
                    'Clave Munip': analisis.clave_munip,
                    'Municipio Cuadernillo': analisis.municipio_cuadernillo,
                    'Clave Localidad': analisis.clave_localidad,
                    'Localidad Cuadernillo': analisis.localidad_cuadernillo,
                    
                    # Información técnica
                    'Recuento CURP Renapo': analisis.recuento_curp_renapo,
                    'Extracción Edo': analisis.extraccion_edo,
                    'Clave': analisis.clave,
                    'DDR': analisis.ddr,
                    'CADER': analisis.cader,
                    
                    # Coordenadas y ubicación
                    'Coordenada X': analisis.coordenada_x,
                    'Coordenada Y': analisis.coordenada_y,
                    'Elevación MSNM': analisis.elevacion_msnm,
                    
                    # Información de muestreo
                    'Profundidad Muestreo': analisis.profundidad_muestreo,
                    'Fecha Muestreo': analisis.fecha_muestreo.strftime('%d/%m/%Y') if analisis.fecha_muestreo else '',
                    'Parcela': analisis.parcela,
                    'Cultivo Anterior': analisis.cultivo_anterior,
                    'Cultivo a Establecer': analisis.cultivo_establecer,
                    'Manejo': analisis.manejo,
                    'Tipo Vegetación': analisis.tipo_vegetacion,
                    
                    # Información del técnico
                    'Nombre Técnico': analisis.nombre_tecnico,
                    'Tel Técnico': analisis.tel_tecnico,
                    'Correo Técnico': analisis.correo_tecnico,
                    
                    # Información del productor
                    'Nombre Productor': analisis.nombre_productor,
                    'Tel Productor': analisis.tel_productor,
                    'Correo Productor': analisis.correo_productor,
                    
                    # Información final
                    'Muestra': analisis.muestra,
                    'Reemplazo': analisis.reemplazo,
                    'Nombre Revisor': analisis.nombre_revisor,
                    
                    # Comentarios (si existen)
                    'Comentario Inválido': analisis.comentario_invalido,
                    
                    # FK de referencia
                    'Municipio ID FK': analisis.municipio_id_FK,
                    'User ID FK': analisis.user_id_FK
                }
                
                data_rows.append(row_data)
            
            # 4. Crear DataFrame
            df = pd.DataFrame(data_rows)
            
            # 5. Información del usuario para el nombre del archivo y hoja
            nombre_completo = f"{usuario.nombre or ''} {usuario.apellido or ''}".strip()
            if not nombre_completo:
                nombre_completo = usuario.correo.split('@')[0]  # Usar parte del correo si no hay nombre
            
            fecha_generacion = datetime.now().strftime('%d%m%Y_%H%M')
            
            # 6. Crear archivo Excel en memoria
            excel_buffer = io.BytesIO()
            
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # Crear hoja principal con datos
                sheet_name = f"Pendientes_{user_id}"
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Obtener la hoja para darle formato
                workbook = writer.book
                worksheet = workbook[sheet_name]
                
                # Ajustar ancho de columnas automáticamente
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)  # Máximo 50 caracteres
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
                # Crear hoja de resumen
                resumen_data = {
                    'Información del Reporte': [
                        'Usuario ID', 'Nombre Usuario', 'Correo Usuario', 
                        'Total Registros', 'Fecha Generación', 'Estado de Registros'
                    ],
                    'Valores': [
                        user_id, nombre_completo, usuario.correo,
                        len(analisis_pendientes), datetime.now().strftime('%d/%m/%Y %H:%M'), 'Pendientes'
                    ]
                }
                
                resumen_df = pd.DataFrame(resumen_data)
                resumen_df.to_excel(writer, sheet_name='Resumen', index=False)
            
            excel_buffer.seek(0)
            excel_bytes = excel_buffer.getvalue()
            excel_buffer.close()
            
            print(f"Excel generado exitosamente: {len(excel_bytes)} bytes")
            print(f"Archivo incluye {len(analisis_pendientes)} registros de {usuario.correo}")
            
            return excel_bytes
            
        except ValueError as ve:
            raise ve
        except Exception as e:
            error_msg = f"Error generando Excel para usuario {user_id}: {str(e)}"
            print(f"Error: {error_msg}")
            raise Exception(error_msg)
    
    @staticmethod
    def get_estadisticas_generales_pendientes(db: Session) -> Dict[str, Any]:
        """
        Obtiene estadísticas generales de análisis pendientes en el sistema
        """
        try:
            # Total de análisis pendientes
            total_pendientes = db.query(AnalisisSuelosPendientes).filter(
                AnalisisSuelosPendientes.estatus == 'pendiente'
            ).count()
            
            # Total de usuarios con pendientes
            total_usuarios_pendientes = db.query(
                func.count(distinct(AnalisisSuelosPendientes.user_id_FK))
            ).filter(
                AnalisisSuelosPendientes.estatus == 'pendiente'
            ).scalar()
            
            # Municipios más frecuentes
            municipios_frecuentes = (
                db.query(
                    AnalisisSuelosPendientes.municipio_cuadernillo,
                    func.count(AnalisisSuelosPendientes.id).label('total')
                )
                .filter(
                    AnalisisSuelosPendientes.estatus == 'pendiente',
                    AnalisisSuelosPendientes.municipio_cuadernillo.isnot(None),
                    AnalisisSuelosPendientes.municipio_cuadernillo != ''
                )
                .group_by(AnalisisSuelosPendientes.municipio_cuadernillo)
                .order_by(func.count(AnalisisSuelosPendientes.id).desc())
                .limit(10)
            ).all()
            
            # Usuarios con más pendientes
            usuarios_top = (
                db.query(
                    Users.correo,
                    func.count(AnalisisSuelosPendientes.id).label('total_pendientes')
                )
                .join(AnalisisSuelosPendientes, Users.ID_user == AnalisisSuelosPendientes.user_id_FK)
                .filter(AnalisisSuelosPendientes.estatus == 'pendiente')
                .group_by(Users.ID_user, Users.correo)
                .order_by(func.count(AnalisisSuelosPendientes.id).desc())
                .limit(10)
            ).all()
            
            return {
                'total_analisis_pendientes': total_pendientes,
                'total_usuarios_con_pendientes': total_usuarios_pendientes,
                'municipios_mas_frecuentes': [
                    {'municipio': mun[0], 'total': mun[1]} 
                    for mun in municipios_frecuentes if mun[0]
                ],
                'usuarios_con_mas_pendientes': [
                    {'correo': user[0], 'total_pendientes': user[1]} 
                    for user in usuarios_top
                ],
                'fecha_consulta': datetime.now()
            }
            
        except Exception as e:
            error_msg = f"Error obteniendo estadísticas generales: {str(e)}"
            print(f"Error: {error_msg}")
            raise Exception(error_msg)