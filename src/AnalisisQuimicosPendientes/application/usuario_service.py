# src/AnalisisQuimicosPendientes/application/usuario_service.py
import io
import math
import re
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, distinct

from src.AnalisisQuimicosPendientes.infrastructure.analisis_quimicos_model import (
    AnalisisQuimicosPendientes,
)
from src.Users.infrastructure.users_model import Users


def obtener_usuarios_con_datos_pendientes(db: Session) -> List[Dict[str, any]]:
    """
    Obtiene todos los usuarios que tienen registros de análisis químicos pendientes.
    Incluye los nombres de archivos únicos que ha subido cada usuario.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Lista de usuarios con sus datos básicos y estadísticas
    """
    try:
        # Obtener usuarios únicos que tienen registros pendientes
        usuarios_con_pendientes = (
            db.query(
                AnalisisQuimicosPendientes.user_id_FK,
                func.min(AnalisisQuimicosPendientes.fecha_creacion).label("primera_fecha"),
                func.max(AnalisisQuimicosPendientes.fecha_creacion).label("ultima_fecha")
            )
            .filter(
                AnalisisQuimicosPendientes.user_id_FK.isnot(None),
                AnalisisQuimicosPendientes.estatus == "pendiente"
            )
            .group_by(AnalisisQuimicosPendientes.user_id_FK)
            .all()
        )
        
        if not usuarios_con_pendientes:
            return []
        
        # Para cada usuario, obtener estadísticas detalladas
        resultado = []
        
        for usuario_data in usuarios_con_pendientes:
            user_id = usuario_data.user_id_FK
            
            # Obtener información del usuario
            usuario = db.query(Users).filter(Users.ID_user == user_id).first()
            
            if not usuario:
                continue
                
            # Contar registros por estatus
            total_registros = (
                db.query(func.count(AnalisisQuimicosPendientes.id))
                .filter(AnalisisQuimicosPendientes.user_id_FK == user_id)
                .scalar() or 0
            )
            
            pendientes = (
                db.query(func.count(AnalisisQuimicosPendientes.id))
                .filter(
                    AnalisisQuimicosPendientes.user_id_FK == user_id,
                    AnalisisQuimicosPendientes.estatus == "pendiente"
                )
                .scalar() or 0
            )
            
            invalidados = (
                db.query(func.count(AnalisisQuimicosPendientes.id))
                .filter(
                    AnalisisQuimicosPendientes.user_id_FK == user_id,
                    AnalisisQuimicosPendientes.estatus == "invalidado"
                )
                .scalar() or 0
            )
            
            # CORREGIDO - Obtener nombres de archivos únicos del usuario (todos los registros, no solo pendientes)
            nombres_archivos_query = (
                db.query(distinct(AnalisisQuimicosPendientes.nombre_archivo))
                .filter(
                    AnalisisQuimicosPendientes.user_id_FK == user_id,
                    AnalisisQuimicosPendientes.nombre_archivo.isnot(None),
                    AnalisisQuimicosPendientes.nombre_archivo != ""
                )
                .all()
            )
            
            # Extraer los nombres de archivos únicos y filtrar valores nulos/vacíos
            nombres_archivos = []
            for row in nombres_archivos_query:
                nombre = row[0]  # distinct() retorna tuplas
                if nombre and nombre.strip() and nombre.strip() != "":
                    nombres_archivos.append(nombre.strip())
            
            # Solo incluir si tiene registros pendientes (ya filtrado, pero por seguridad)
            if pendientes == 0:
                continue
                
            # Construir nombre de usuario
            nombre_completo = f"{usuario.nombre or ''} {usuario.apellido or ''}".strip()
            if not nombre_completo:
                nombre_completo = usuario.correo.split('@')[0] if usuario.correo else f"Usuario {user_id}"
            
            resultado.append({
                "user_id": user_id,
                "nombre_usuario": nombre_completo,
                "correo": usuario.correo,
                "fecha_creacion": usuario_data.primera_fecha.strftime("%Y-%m-%d %H:%M:%S") if usuario_data.primera_fecha else None,
                "ultima_actualizacion": usuario_data.ultima_fecha.strftime("%Y-%m-%d %H:%M:%S") if usuario_data.ultima_fecha else None,
                "estatus": "pendiente",  # Como filtras por pendientes, siempre hay pendientes
                "total_registros": int(total_registros),
                "registros_pendientes": int(pendientes),
                "registros_invalidados": int(invalidados),
                "nombres_archivos": nombres_archivos  # Lista de nombres únicos
            })
        
        # Ordenar por fecha de última actualización (más recientes primero)
        resultado.sort(key=lambda x: x.get("ultima_actualizacion", ""), reverse=True)
        
        return resultado
        
    except Exception as e:
        print(f"Error en obtener_usuarios_con_datos_pendientes: {str(e)}")
        import traceback
        print(f"Traceback completo: {traceback.format_exc()}")
        raise


def generar_excel_usuario(user_id: int, db: Session) -> Optional[bytes]:
    """
    Genera un archivo Excel con todos los datos de análisis químicos de un usuario específico.
    
    Args:
        user_id: ID del usuario
        db: Sesión de base de datos
        
    Returns:
        Bytes del archivo Excel generado o None si no hay datos
    """
    try:
        # Obtener todos los registros del usuario
        registros = (
            db.query(AnalisisQuimicosPendientes)
            .filter(AnalisisQuimicosPendientes.user_id_FK == user_id)
            .order_by(AnalisisQuimicosPendientes.fecha_creacion.desc())
            .all()
        )
        
        if not registros:
            return None
        
        # Obtener información del usuario para el nombre del archivo
        usuario = db.query(Users).filter(Users.ID_user == user_id).first()
        nombre_usuario = "usuario_desconocido"
        correo_usuario = "no_disponible"
        
        if usuario:
            nombre_completo = f"{usuario.nombre or ''} {usuario.apellido or ''}".strip()
            if nombre_completo:
                # Limpiar nombre para uso en archivos
                nombre_usuario = re.sub(r'[^\w\s-]', '', nombre_completo.lower().replace(" ", "_"))
            else:
                nombre_usuario = re.sub(r'[^\w\s-]', '', usuario.correo.split('@')[0].lower()) if usuario.correo else f"usuario_{user_id}"
            correo_usuario = usuario.correo or "no_disponible"
        
        # Convertir registros a diccionarios para pandas
        datos = []
        for registro in registros:
            fila = {
                "ID_Registro": registro.id,
                "Municipio": registro.municipio,
                "Localidad": registro.localidad,
                "Nombre_Productor": registro.nombre_productor,
                "Cultivo_Anterior": registro.cultivo_anterior,
                "Arcilla_%": float(registro.arcilla) if registro.arcilla is not None else None,
                "Limo_%": float(registro.limo) if registro.limo is not None else None,
                "Arena_%": float(registro.arena) if registro.arena is not None else None,
                "Textura": registro.textura,
                "Densidad_Aparente": float(registro.da) if registro.da is not None else None,
                "pH": float(registro.ph) if registro.ph is not None else None,
                "Materia_Organica_%": float(registro.mo) if registro.mo is not None else None,
                "Fosforo_ppm": float(registro.fosforo) if registro.fosforo is not None else None,
                "N_Inorganico_ppm": float(registro.n_inorganico) if registro.n_inorganico is not None else None,
                "Potasio_ppm": float(registro.k) if registro.k is not None else None,
                "Magnesio_ppm": float(registro.mg) if registro.mg is not None else None,
                "Calcio_ppm": float(registro.ca) if registro.ca is not None else None,
                "Sodio_ppm": float(registro.na) if registro.na is not None else None,
                "Aluminio_ppm": float(registro.al) if registro.al is not None else None,
                "CIC_meq/100g": float(registro.cic) if registro.cic is not None else None,
                "CIC_Calculada_meq/100g": float(registro.cic_calculada) if registro.cic_calculada is not None else None,
                "Hidrogeno_ppm": float(registro.h) if registro.h is not None else None,
                "Azufre_ppm": float(registro.azufre) if registro.azufre is not None else None,
                "Hierro_ppm": float(registro.hierro) if registro.hierro is not None else None,
                "Cobre_ppm": float(registro.cobre) if registro.cobre is not None else None,
                "Zinc_ppm": float(registro.zinc) if registro.zinc is not None else None,
                "Manganeso_ppm": float(registro.manganeso) if registro.manganeso is not None else None,
                "Boro_ppm": float(registro.boro) if registro.boro is not None else None,
                "Observacion_1": registro.columna1,
                "Observacion_2": registro.columna2,
                "Relacion_Ca/Mg": float(registro.ca_mg) if registro.ca_mg is not None else None,
                "Relacion_Mg/K": float(registro.mg_k) if registro.mg_k is not None else None,
                "Relacion_Ca/K": float(registro.ca_k) if registro.ca_k is not None else None,
                "Relacion_(Ca+Mg)/K": float(registro.ca_mg_k) if registro.ca_mg_k is not None else None,
                "Relacion_K/Mg": float(registro.k_mg) if registro.k_mg is not None else None,
                "Estatus": registro.estatus,
                "Comentario_Invalido": registro.comentario_invalido,
                "Nombre_Archivo_Original": registro.nombre_archivo,
                "Fecha_Creacion": registro.fecha_creacion.strftime("%Y-%m-%d %H:%M:%S") if registro.fecha_creacion else None
            }
            datos.append(fila)
        
        # Crear DataFrame
        df = pd.DataFrame(datos)
        
        # Crear archivo Excel en memoria
        buffer = io.BytesIO()
        
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Hoja principal con todos los datos
            df.to_excel(writer, sheet_name='Análisis_Químicos', index=False)
            
            # Estadísticas para el resumen
            pendientes_count = len([r for r in registros if r.estatus == "pendiente"])
            invalidados_count = len([r for r in registros if r.estatus == "invalidado"])
            procesados_count = len([r for r in registros if r.estatus == "procesado"])
            
            # Obtener archivos únicos
            archivos_unicos = list(set([r.nombre_archivo for r in registros if r.nombre_archivo and r.nombre_archivo.strip()]))
            
            # Hoja resumen
            resumen_data = {
                "Información": [
                    "Usuario ID",
                    "Usuario",
                    "Correo",
                    "Total de registros",
                    "Registros pendientes",
                    "Registros invalidados",
                    "Registros procesados",
                    "Archivos subidos únicos",
                    "Primera subida",
                    "Última subida",
                    "Fecha de extracción"
                ],
                "Valor": [
                    user_id,
                    nombre_usuario,
                    correo_usuario,
                    len(registros),
                    pendientes_count,
                    invalidados_count,
                    procesados_count,
                    len(archivos_unicos),
                    registros[-1].fecha_creacion.strftime("%Y-%m-%d %H:%M:%S") if registros else "No disponible",
                    registros[0].fecha_creacion.strftime("%Y-%m-%d %H:%M:%S") if registros else "No disponible",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]
            }
            
            resumen_df = pd.DataFrame(resumen_data)
            resumen_df.to_excel(writer, sheet_name='Resumen', index=False)
            
            # Hoja con lista de archivos únicos
            if archivos_unicos:
                archivos_data = {
                    "Nombre_Archivo": archivos_unicos,
                    "Registros_por_Archivo": [
                        len([r for r in registros if r.nombre_archivo == archivo])
                        for archivo in archivos_unicos
                    ]
                }
                archivos_df = pd.DataFrame(archivos_data)
                archivos_df.to_excel(writer, sheet_name='Archivos_Subidos', index=False)
            
            # Ajustar anchos de columnas automáticamente
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if cell.value:
                                cell_length = len(str(cell.value))
                                if cell_length > max_length:
                                    max_length = cell_length
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)  # Máximo 50 caracteres
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        buffer.seek(0)
        return buffer.getvalue()
        
    except Exception as e:
        print(f"Error en generar_excel_usuario: {str(e)}")
        return None


def obtener_info_usuario_para_descarga(user_id: int, db: Session) -> Optional[Dict[str, any]]:
    """
    Obtiene información básica del usuario para generar el nombre del archivo de descarga.
    
    Args:
        user_id: ID del usuario
        db: Sesión de base de datos
        
    Returns:
        Diccionario con información del usuario o None si no existe
    """
    try:
        usuario = db.query(Users).filter(Users.ID_user == user_id).first()
        
        if not usuario:
            return None
        
        nombre_completo = f"{usuario.nombre or ''} {usuario.apellido or ''}".strip()
        if not nombre_completo:
            nombre_completo = usuario.correo.split('@')[0] if usuario.correo else f"usuario_{user_id}"
        
        # Contar registros
        total_registros = (
            db.query(func.count(AnalisisQuimicosPendientes.id))
            .filter(AnalisisQuimicosPendientes.user_id_FK == user_id)
            .scalar() or 0
        )
        
        # Limpiar nombre para archivo
        nombre_archivo_limpio = re.sub(r'[^\w\s-]', '', nombre_completo.lower().replace(" ", "_"))
        
        return {
            "user_id": user_id,
            "nombre_completo": nombre_completo,
            "correo": usuario.correo or "no_disponible",
            "total_registros": total_registros,
            "nombre_archivo": f"analisis_quimicos_{nombre_archivo_limpio}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        }
        
    except Exception as e:
        print(f"Error en obtener_info_usuario_para_descarga: {str(e)}")
        return None
    
def generar_excel_usuario_por_archivo(user_id: int, nombre_archivo: str, db: Session) -> Optional[bytes]:
    """
    Genera un archivo Excel con los datos de análisis químicos de un usuario específico
    filtrados por nombre de archivo.
    
    Args:
        user_id: ID del usuario
        nombre_archivo: Nombre del archivo específico a filtrar
        db: Sesión de base de datos
        
    Returns:
        Bytes del archivo Excel generado o None si no hay datos
    """
    try:
        # Obtener registros del usuario filtrados por nombre de archivo
        registros = (
            db.query(AnalisisQuimicosPendientes)
            .filter(
                AnalisisQuimicosPendientes.user_id_FK == user_id,
                AnalisisQuimicosPendientes.nombre_archivo == nombre_archivo
            )
            .order_by(AnalisisQuimicosPendientes.fecha_creacion.desc())
            .all()
        )
        
        if not registros:
            return None
        
        # Obtener información del usuario para el nombre del archivo
        usuario = db.query(Users).filter(Users.ID_user == user_id).first()
        nombre_usuario = "usuario_desconocido"
        correo_usuario = "no_disponible"
        
        if usuario:
            nombre_completo = f"{usuario.nombre or ''} {usuario.apellido or ''}".strip()
            if nombre_completo:
                nombre_usuario = re.sub(r'[^\w\s-]', '', nombre_completo.lower().replace(" ", "_"))
            else:
                nombre_usuario = re.sub(r'[^\w\s-]', '', usuario.correo.split('@')[0].lower()) if usuario.correo else f"usuario_{user_id}"
            correo_usuario = usuario.correo or "no_disponible"
        
        # Convertir registros a diccionarios para pandas
        datos = []
        for registro in registros:
            fila = {
                "ID_Registro": registro.id,
                "Municipio": registro.municipio,
                "Localidad": registro.localidad,
                "Nombre_Productor": registro.nombre_productor,
                "Cultivo_Anterior": registro.cultivo_anterior,
                "Arcilla_%": float(registro.arcilla) if registro.arcilla is not None else None,
                "Limo_%": float(registro.limo) if registro.limo is not None else None,
                "Arena_%": float(registro.arena) if registro.arena is not None else None,
                "Textura": registro.textura,
                "Densidad_Aparente": float(registro.da) if registro.da is not None else None,
                "pH": float(registro.ph) if registro.ph is not None else None,
                "Materia_Organica_%": float(registro.mo) if registro.mo is not None else None,
                "Fosforo_ppm": float(registro.fosforo) if registro.fosforo is not None else None,
                "N_Inorganico_ppm": float(registro.n_inorganico) if registro.n_inorganico is not None else None,
                "Potasio_ppm": float(registro.k) if registro.k is not None else None,
                "Magnesio_ppm": float(registro.mg) if registro.mg is not None else None,
                "Calcio_ppm": float(registro.ca) if registro.ca is not None else None,
                "Sodio_ppm": float(registro.na) if registro.na is not None else None,
                "Aluminio_ppm": float(registro.al) if registro.al is not None else None,
                "CIC_meq/100g": float(registro.cic) if registro.cic is not None else None,
                "CIC_Calculada_meq/100g": float(registro.cic_calculada) if registro.cic_calculada is not None else None,
                "Hidrogeno_ppm": float(registro.h) if registro.h is not None else None,
                "Azufre_ppm": float(registro.azufre) if registro.azufre is not None else None,
                "Hierro_ppm": float(registro.hierro) if registro.hierro is not None else None,
                "Cobre_ppm": float(registro.cobre) if registro.cobre is not None else None,
                "Zinc_ppm": float(registro.zinc) if registro.zinc is not None else None,
                "Manganeso_ppm": float(registro.manganeso) if registro.manganeso is not None else None,
                "Boro_ppm": float(registro.boro) if registro.boro is not None else None,
                "Observacion_1": registro.columna1,
                "Observacion_2": registro.columna2,
                "Relacion_Ca/Mg": float(registro.ca_mg) if registro.ca_mg is not None else None,
                "Relacion_Mg/K": float(registro.mg_k) if registro.mg_k is not None else None,
                "Relacion_Ca/K": float(registro.ca_k) if registro.ca_k is not None else None,
                "Relacion_(Ca+Mg)/K": float(registro.ca_mg_k) if registro.ca_mg_k is not None else None,
                "Relacion_K/Mg": float(registro.k_mg) if registro.k_mg is not None else None,
                "Estatus": registro.estatus,
                "Comentario_Invalido": registro.comentario_invalido,
                "Nombre_Archivo_Original": registro.nombre_archivo,
                "Fecha_Creacion": registro.fecha_creacion.strftime("%Y-%m-%d %H:%M:%S") if registro.fecha_creacion else None
            }
            datos.append(fila)
        
        # Crear DataFrame
        df = pd.DataFrame(datos)
        
        # Crear archivo Excel en memoria
        buffer = io.BytesIO()
        
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Hoja principal con todos los datos del archivo específico
            df.to_excel(writer, sheet_name='Análisis_Químicos', index=False)
            
            # Estadísticas para el resumen
            pendientes_count = len([r for r in registros if r.estatus == "pendiente"])
            invalidados_count = len([r for r in registros if r.estatus == "invalidado"])
            procesados_count = len([r for r in registros if r.estatus == "procesado"])
            
            # Hoja resumen específica del archivo
            resumen_data = {
                "Información": [
                    "Usuario ID",
                    "Usuario",
                    "Correo",
                    "Archivo específico",
                    "Registros en este archivo",
                    "Registros pendientes",
                    "Registros invalidados",
                    "Registros procesados",
                    "Primera subida archivo",
                    "Última subida archivo",
                    "Fecha de extracción"
                ],
                "Valor": [
                    user_id,
                    nombre_usuario,
                    correo_usuario,
                    nombre_archivo,
                    len(registros),
                    pendientes_count,
                    invalidados_count,
                    procesados_count,
                    registros[-1].fecha_creacion.strftime("%Y-%m-%d %H:%M:%S") if registros else "No disponible",
                    registros[0].fecha_creacion.strftime("%Y-%m-%d %H:%M:%S") if registros else "No disponible",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]
            }
            
            resumen_df = pd.DataFrame(resumen_data)
            resumen_df.to_excel(writer, sheet_name='Resumen', index=False)
            
            # Ajustar anchos de columnas automáticamente
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if cell.value:
                                cell_length = len(str(cell.value))
                                if cell_length > max_length:
                                    max_length = cell_length
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        buffer.seek(0)
        return buffer.getvalue()
        
    except Exception as e:
        print(f"Error en generar_excel_usuario_por_archivo: {str(e)}")
        return None
    
def obtener_comentario_invalido_por_correo(correo_usuario: str, db: Session) -> Optional[Dict[str, any]]:
    """
    Obtiene el comentario inválido de un usuario por su correo electrónico.
    Solo obtiene y muestra el contenido, no realiza modificaciones.
    
    Args:
        correo_usuario: Correo del usuario
        db: Sesión de base de datos
        
    Returns:
        Diccionario con información del comentario inválido o None si no existe
    """
    try:
        # 1. Verificar que el usuario existe
        usuario = db.query(Users).filter(Users.correo == correo_usuario.lower().strip()).first()
        if not usuario:
            return None
        
        # 2. Buscar registros con comentarios inválidos
        registros_con_comentarios = db.query(AnalisisQuimicosPendientes).filter(
            AnalisisQuimicosPendientes.user_id_FK == usuario.ID_user,
            AnalisisQuimicosPendientes.comentario_invalido.isnot(None),
            AnalisisQuimicosPendientes.comentario_invalido != ""
        ).order_by(AnalisisQuimicosPendientes.fecha_creacion.desc()).all()
        
        # 3. Si no hay comentarios inválidos
        if not registros_con_comentarios:
            return {
                "tiene_comentario": False,
                "comentario_invalido": None,
                "total_registros_con_comentario": 0,
                "usuario_info": {
                    "user_id": usuario.ID_user,
                    "nombre_completo": f"{usuario.nombre or ''} {usuario.apellido or ''}".strip(),
                    "correo": usuario.correo
                },
                "mensaje": "No hay comentarios inválidos para este usuario"
            }
        
        # 4. Obtener información del comentario
        primer_registro = registros_con_comentarios[0]
        
        # 5. Verificar si todos los comentarios son iguales
        comentarios_unicos = list(set([r.comentario_invalido for r in registros_con_comentarios if r.comentario_invalido]))
        
        return {
            "tiene_comentario": True,
            "comentario_invalido": primer_registro.comentario_invalido,
            "total_registros_con_comentario": len(registros_con_comentarios),
            "comentarios_diferentes": len(comentarios_unicos) > 1,
            "todos_los_comentarios": comentarios_unicos if len(comentarios_unicos) > 1 else None,
            "usuario_info": {
                "user_id": usuario.ID_user,
                "nombre_completo": f"{usuario.nombre or ''} {usuario.apellido or ''}".strip(),
                "correo": usuario.correo
            },
            "fecha_ultimo_comentario": primer_registro.fecha_creacion.strftime("%Y-%m-%d %H:%M:%S") if primer_registro.fecha_creacion else None,
            "registros_detalles": [
                {
                    "id": r.id,
                    "comentario": r.comentario_invalido,
                    "fecha_creacion": r.fecha_creacion.strftime("%Y-%m-%d %H:%M:%S") if r.fecha_creacion else None,
                    "nombre_archivo": r.nombre_archivo,
                    "estatus": r.estatus
                } for r in registros_con_comentarios
            ],
            "mensaje": f"Usuario tiene {len(registros_con_comentarios)} registro(s) con comentarios inválidos"
        }
        
    except Exception as e:
        print(f"Error en obtener_comentario_invalido_por_correo: {str(e)}")
        return None