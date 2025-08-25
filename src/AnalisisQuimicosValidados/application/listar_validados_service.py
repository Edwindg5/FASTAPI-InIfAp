"""
Servicio para listar y generar Excel de análisis químicos validados específicos
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, Any, Optional
import traceback
import pandas as pd
from io import BytesIO
from datetime import datetime

def listar_todos_validados_con_usuario(db: Session) -> Dict[str, Any]:
    """
    Lista todos los análisis validados AGRUPADOS por usuario y nombre_archivo.
    Muestra un registro por archivo con la cantidad de análisis que contiene.
    
    Args:
        db: Sesión de base de datos
        
    Returns:
        Dict con los análisis validados agrupados por archivo
    """
    try:
        print("📋 Listando validados AGRUPADOS por archivo")
        
        # Importar modelos
        from src.AnalisisQuimicosValidados.infrastructure.analisis_quimicos_validados_model import (
            AnalisisQuimicosValidados
        )
        from src.Users.infrastructure.users_model import Users
        from sqlalchemy import func, desc
        
        # Consulta agrupada por usuario y nombre_archivo
        query = db.query(
            Users.correo.label('correo_usuario'),
            Users.nombre.label('nombre_usuario'),
            AnalisisQuimicosValidados.nombre_archivo,
            func.count(AnalisisQuimicosValidados.id).label('cantidad_analisis'),
            func.min(AnalisisQuimicosValidados.fecha_validacion).label('primera_validacion'),
            func.max(AnalisisQuimicosValidados.fecha_validacion).label('ultima_validacion'),
            func.min(AnalisisQuimicosValidados.fecha_creacion).label('primera_creacion'),
            func.max(AnalisisQuimicosValidados.fecha_creacion).label('ultima_creacion')
        ).join(
            Users, 
            AnalisisQuimicosValidados.user_id_FK == Users.ID_user
        ).group_by(
            Users.correo,
            Users.nombre,
            AnalisisQuimicosValidados.nombre_archivo
        ).order_by(
            desc('ultima_validacion')
        )
        
        resultados = query.all()
        total = len(resultados)
        
        # Formatear datos agrupados
        data = []
        for resultado in resultados:
            data.append({
                "nombre_usuario": resultado.nombre_usuario or "Sin nombre",
                "correo_usuario": resultado.correo_usuario,
                "nombre_archivo": resultado.nombre_archivo or "Sin archivo",
                "cantidad_analisis": resultado.cantidad_analisis,
                "estatus": "Validado",
                "fecha_validacion": resultado.ultima_validacion.strftime("%Y-%m-%d %H:%M:%S") if resultado.ultima_validacion else None,
                "fecha_creacion": resultado.primera_creacion.strftime("%Y-%m-%d %H:%M:%S") if resultado.primera_creacion else None,
                "rango_fechas": {
                    "primera_validacion": resultado.primera_validacion.strftime("%Y-%m-%d %H:%M:%S") if resultado.primera_validacion else None,
                    "ultima_validacion": resultado.ultima_validacion.strftime("%Y-%m-%d %H:%M:%S") if resultado.ultima_validacion else None
                }
            })
        
        print(f"✅ Encontrados {total} archivos agrupados")
        
        return {
            "success": True,
            "data": data,
            "total": total,
            "message": f"Se obtuvieron {total} archivos validados agrupados"
        }
        
    except Exception as e:
        print(f"❌ Error al listar validados agrupados: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "data": [],
            "total": 0,
            "message": f"Error al obtener análisis validados: {str(e)}"
        }

def generar_excel_por_archivo_usuario(db: Session, correo_usuario: str, nombre_archivo: str) -> Dict[str, Any]:
    """
    Genera Excel con análisis validados específicos por correo de usuario y nombre de archivo.
    
    Args:
        db: Sesión de base de datos
        correo_usuario: Correo del usuario
        nombre_archivo: Nombre del archivo específico
        
    Returns:
        Dict con el buffer del Excel y información del proceso
    """
    try:
        print(f"📊 Generando Excel específico - Usuario: {correo_usuario}, Archivo: {nombre_archivo}")
        
        # Importar modelos
        from src.AnalisisQuimicosValidados.infrastructure.analisis_quimicos_validados_model import (
            AnalisisQuimicosValidados
        )
        from src.Users.infrastructure.users_model import Users
        
        # Buscar análisis específicos
        query = db.query(AnalisisQuimicosValidados).join(
            Users, 
            AnalisisQuimicosValidados.user_id_FK == Users.ID_user
        ).filter(
            and_(
                Users.correo == correo_usuario,  # CORREGIDO: usar 'correo'
                AnalisisQuimicosValidados.nombre_archivo == nombre_archivo
            )
        )
        
        resultados = query.all()
        
        if not resultados:
            return {
                "success": False,
                "message": f"No se encontraron análisis validados para el usuario '{correo_usuario}' con el archivo '{nombre_archivo}'"
            }
        
        print(f"✓ Encontrados {len(resultados)} análisis para exportar")
        
        # Convertir a DataFrame
        datos_excel = []
        for analisis in resultados:
            datos_excel.append({
                "ID": analisis.id,
                "Municipio": analisis.municipio,
                "Localidad": analisis.localidad,
                "Nombre Productor": analisis.nombre_productor,
                "Cultivo Anterior": analisis.cultivo_anterior,
                "Arcilla": float(analisis.arcilla) if analisis.arcilla else None,
                "Limo": float(analisis.limo) if analisis.limo else None,
                "Arena": float(analisis.arena) if analisis.arena else None,
                "Textura": analisis.textura,
                "DA": float(analisis.da) if analisis.da else None,
                "pH": float(analisis.ph) if analisis.ph else None,
                "MO": float(analisis.mo) if analisis.mo else None,
                "Fósforo": float(analisis.fosforo) if analisis.fosforo else None,
                "N Inorgánico": float(analisis.n_inorganico) if analisis.n_inorganico else None,
                "K": float(analisis.k) if analisis.k else None,
                "Mg": float(analisis.mg) if analisis.mg else None,
                "Ca": float(analisis.ca) if analisis.ca else None,
                "Na": float(analisis.na) if analisis.na else None,
                "Al": float(analisis.al) if analisis.al else None,
                "CIC": float(analisis.cic) if analisis.cic else None,
                "CIC Calculada": float(analisis.cic_calculada) if analisis.cic_calculada else None,
                "H": float(analisis.h) if analisis.h else None,
                "Azufre": float(analisis.azufre) if analisis.azufre else None,
                "Hierro": float(analisis.hierro) if analisis.hierro else None,
                "Cobre": float(analisis.cobre) if analisis.cobre else None,
                "Zinc": float(analisis.zinc) if analisis.zinc else None,
                "Manganeso": float(analisis.manganeso) if analisis.manganeso else None,
                "Boro": float(analisis.boro) if analisis.boro else None,
                "Columna1": analisis.columna1,
                "Columna2": analisis.columna2,
                "Ca/Mg": float(analisis.ca_mg) if analisis.ca_mg else None,
                "Mg/K": float(analisis.mg_k) if analisis.mg_k else None,
                "Ca/K": float(analisis.ca_k) if analisis.ca_k else None,
                "Ca+Mg/K": float(analisis.ca_mg_k) if analisis.ca_mg_k else None,
                "K/Mg": float(analisis.k_mg) if analisis.k_mg else None,
                "Nombre Archivo": analisis.nombre_archivo,
                "Fecha Validación": analisis.fecha_validacion.strftime("%Y-%m-%d %H:%M:%S") if analisis.fecha_validacion else None,
                "Fecha Creación": analisis.fecha_creacion.strftime("%Y-%m-%d %H:%M:%S") if analisis.fecha_creacion else None
            })
        
        # Crear DataFrame
        df = pd.DataFrame(datos_excel)
        
        # Generar Excel
        buffer = BytesIO()
        
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Hoja principal con datos
            df.to_excel(
                writer,
                sheet_name='Análisis Validados',
                index=False,
                startrow=0
            )
            
            # Obtener el workbook y worksheet para formateo
            workbook = writer.book
            worksheet = writer.sheets['Análisis Validados']
            
            # Ajustar ancho de columnas
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Agregar hoja de información
            info_data = {
                "Información": [
                    "Usuario",
                    "Archivo",
                    "Total de Análisis",
                    "Fecha de Generación",
                    "Estado"
                ],
                "Valor": [
                    correo_usuario,
                    nombre_archivo,
                    len(resultados),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Validados"
                ]
            }
            
            df_info = pd.DataFrame(info_data)
            df_info.to_excel(
                writer,
                sheet_name='Información',
                index=False
            )
        
        buffer.seek(0)
        
        print(f"✅ Excel generado exitosamente - {len(resultados)} análisis exportados")
        
        return {
            "success": True,
            "buffer": buffer,
            "total_registros": len(resultados),
            "message": f"Excel generado con {len(resultados)} análisis validados"
        }
        
    except Exception as e:
        print(f"❌ Error al generar Excel específico: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "message": f"Error al generar Excel: {str(e)}"
        }