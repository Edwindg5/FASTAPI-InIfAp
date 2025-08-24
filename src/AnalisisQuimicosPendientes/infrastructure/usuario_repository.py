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
            
            # ¡NUEVO! - Obtener nombres de archivos únicos del usuario
            nombres_archivos_query = (
                db.query(AnalisisQuimicosPendientes.nombre_archivo)
                .filter(
                    AnalisisQuimicosPendientes.user_id_FK == user_id,
                    AnalisisQuimicosPendientes.nombre_archivo.isnot(None),
                    AnalisisQuimicosPendientes.nombre_archivo != ""
                )
                .distinct()
                .all()
            )
            
            nombres_archivos = [
                row.nombre_archivo for row in nombres_archivos_query 
                if row.nombre_archivo and row.nombre_archivo.strip()
            ]
            
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
                "nombres_archivos": nombres_archivos  # ¡NUEVO CAMPO!
            })
        
        # Ordenar por fecha de última actualización (más recientes primero)
        resultado.sort(key=lambda x: x.get("ultima_actualizacion", ""), reverse=True)
        
        return resultado
        
    except Exception as e:
        print(f"Error en obtener_usuarios_con_datos_pendientes: {str(e)}")
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
                "Nombre_Archivo_Original": registro.nombre_archivo,  # ¡NUEVO! - Incluir nombre de archivo
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
            
            # ¡NUEVO! - Hoja con lista de archivos únicos
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