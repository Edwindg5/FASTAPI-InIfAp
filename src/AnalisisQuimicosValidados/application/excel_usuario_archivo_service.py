# src/AnalisisQuimicosValidados/application/excel_usuario_archivo_service.py
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, Any, Optional, BinaryIO
import pandas as pd
import io
from datetime import datetime
import traceback

from src.AnalisisQuimicosValidados.infrastructure.analisis_quimicos_validados_model import AnalisisQuimicosValidados
from src.Users.infrastructure.users_model import Users


def verificar_datos_usuario_archivo(
    db: Session, 
    user_id: int, 
    nombre_archivo: str
) -> Dict[str, Any]:
    """
    Verifica si existen análisis validados para un usuario y archivo específico.
    
    Args:
        db (Session): Sesión de base de datos
        user_id (int): ID del usuario
        nombre_archivo (str): Nombre del archivo
        
    Returns:
        Dict: Resultado de la verificación con detalles
    """
    try:
        print(f"=== VERIFICANDO DATOS: USER {user_id} - ARCHIVO {nombre_archivo} ===")
        
        # Verificar que el usuario existe
        usuario = db.query(Users).filter(Users.ID_user == user_id).first()
        if not usuario:
            return {
                "success": False,
                "message": f"Usuario con ID {user_id} no encontrado",
                "total_registros": 0,
                "detalles": {
                    "usuario_existe": False,
                    "archivo_existe": False
                }
            }
        
        # Buscar análisis validados con los criterios especificados
        query = db.query(AnalisisQuimicosValidados).filter(
            and_(
                AnalisisQuimicosValidados.user_id_FK == user_id,
                AnalisisQuimicosValidados.nombre_archivo == nombre_archivo
            )
        )
        
        total_registros = query.count()
        
        if total_registros == 0:
            return {
                "success": False,
                "message": f"No se encontraron análisis validados para el usuario '{usuario.correo}' con el archivo '{nombre_archivo}'",
                "total_registros": 0,
                "detalles": {
                    "usuario_existe": True,
                    "usuario_correo": usuario.correo,
                    "archivo_existe": False,
                    "user_id": user_id,
                    "nombre_archivo": nombre_archivo
                }
            }
        
        # Obtener algunas estadísticas adicionales
        fechas_query = query.with_entities(
            AnalisisQuimicosValidados.fecha_creacion,
            AnalisisQuimicosValidados.fecha_validacion
        ).all()
        
        fechas_creacion = [f.fecha_creacion for f in fechas_query if f.fecha_creacion]
        fechas_validacion = [f.fecha_validacion for f in fechas_query if f.fecha_validacion]
        
        return {
            "success": True,
            "message": f"Se encontraron {total_registros} análisis validados",
            "total_registros": total_registros,
            "usuario_info": {
                "user_id": usuario.ID_user,
                "correo": usuario.correo,
                "nombre": getattr(usuario, 'nombre', None) or usuario.correo.split('@')[0]
            },
            "archivo_info": {
                "nombre_archivo": nombre_archivo,
                "total_analisis": total_registros
            },
            "fechas_info": {
                "fecha_creacion_min": min(fechas_creacion) if fechas_creacion else None,
                "fecha_creacion_max": max(fechas_creacion) if fechas_creacion else None,
                "fecha_validacion_min": min(fechas_validacion) if fechas_validacion else None,
                "fecha_validacion_max": max(fechas_validacion) if fechas_validacion else None
            }
        }
        
    except Exception as e:
        print(f"❌ Error verificando datos: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "message": f"Error al verificar datos: {str(e)}",
            "total_registros": 0,
            "error": str(e)
        }


def generar_excel_por_usuario_archivo(
    db: Session,
    user_id: int,
    nombre_archivo: str
) -> Optional[BinaryIO]:
    """
    Genera un archivo Excel con todos los análisis validados de un usuario y archivo específico.
    
    Args:
        db (Session): Sesión de base de datos
        user_id (int): ID del usuario
        nombre_archivo (str): Nombre del archivo
        
    Returns:
        Optional[BinaryIO]: Buffer del archivo Excel o None si hay error
    """
    try:
        print(f"=== GENERANDO EXCEL: USER {user_id} - ARCHIVO {nombre_archivo} ===")
        
        # Obtener datos con JOIN para incluir información del usuario
        query = db.query(
            AnalisisQuimicosValidados,
            Users.correo.label('usuario_correo'),
            Users.nombre.label('usuario_nombre')
        ).outerjoin(
            Users, AnalisisQuimicosValidados.user_id_FK == Users.ID_user
        ).filter(
            and_(
                AnalisisQuimicosValidados.user_id_FK == user_id,
                AnalisisQuimicosValidados.nombre_archivo == nombre_archivo
            )
        ).order_by(
            AnalisisQuimicosValidados.fecha_validacion.desc(),
            AnalisisQuimicosValidados.id
        )
        
        resultados = query.all()
        
        if not resultados:
            print("❌ No se encontraron datos para generar el Excel")
            return None
        
        print(f"✓ Datos obtenidos: {len(resultados)} registros")
        
        # Convertir a lista de diccionarios para pandas
        datos_excel = []
        
        for analisis, usuario_correo, usuario_nombre in resultados:
            registro = {
                # Información del registro
                'ID': analisis.id,
                'Usuario_Correo': usuario_correo,
                'Usuario_Nombre': usuario_nombre or 'Sin nombre',
                'Nombre_Archivo': analisis.nombre_archivo,
                'Fecha_Validacion': analisis.fecha_validacion.strftime('%Y-%m-%d %H:%M:%S') if analisis.fecha_validacion else '',
                'Fecha_Creacion': analisis.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S') if analisis.fecha_creacion else '',
                
                # Información geográfica
                'Municipio': analisis.municipio,
                'Localidad': analisis.localidad,
                'Nombre_Productor': analisis.nombre_productor,
                'Cultivo_Anterior': analisis.cultivo_anterior,
                
                # Análisis físico
                'Arcilla_%': float(analisis.arcilla) if analisis.arcilla else None,
                'Limo_%': float(analisis.limo) if analisis.limo else None,
                'Arena_%': float(analisis.arena) if analisis.arena else None,
                'Textura': analisis.textura,
                'Densidad_Aparente': float(analisis.da) if analisis.da else None,
                
                # Análisis químico básico
                'pH': float(analisis.ph) if analisis.ph else None,
                'Materia_Organica_%': float(analisis.mo) if analisis.mo else None,
                'Fosforo_ppm': float(analisis.fosforo) if analisis.fosforo else None,
                'N_Inorganico_ppm': float(analisis.n_inorganico) if analisis.n_inorganico else None,
                
                # Bases intercambiables
                'Potasio_cmol/kg': float(analisis.k) if analisis.k else None,
                'Magnesio_cmol/kg': float(analisis.mg) if analisis.mg else None,
                'Calcio_cmol/kg': float(analisis.ca) if analisis.ca else None,
                'Sodio_cmol/kg': float(analisis.na) if analisis.na else None,
                'Aluminio_cmol/kg': float(analisis.al) if analisis.al else None,
                
                # Capacidad de intercambio
                'CIC_cmol/kg': float(analisis.cic) if analisis.cic else None,
                'CIC_Calculada': float(analisis.cic_calculada) if analisis.cic_calculada else None,
                'Hidrogeno_cmol/kg': float(analisis.h) if analisis.h else None,
                
                # Micronutrientes
                'Azufre_ppm': float(analisis.azufre) if analisis.azufre else None,
                'Hierro_ppm': float(analisis.hierro) if analisis.hierro else None,
                'Cobre_ppm': float(analisis.cobre) if analisis.cobre else None,
                'Zinc_ppm': float(analisis.zinc) if analisis.zinc else None,
                'Manganeso_ppm': float(analisis.manganeso) if analisis.manganeso else None,
                'Boro_ppm': float(analisis.boro) if analisis.boro else None,
                
                # Relaciones catiónicas
                'Relacion_Ca/Mg': float(analisis.ca_mg) if analisis.ca_mg else None,
                'Relacion_Mg/K': float(analisis.mg_k) if analisis.mg_k else None,
                'Relacion_Ca/K': float(analisis.ca_k) if analisis.ca_k else None,
                'Relacion_Ca+Mg/K': float(analisis.ca_mg_k) if analisis.ca_mg_k else None,
                'Relacion_K/Mg': float(analisis.k_mg) if analisis.k_mg else None,
                
                # Columnas adicionales
                'Columna1': analisis.columna1,
                'Columna2': analisis.columna2
            }
            
            datos_excel.append(registro)
        
        # Crear DataFrame
        df = pd.DataFrame(datos_excel)
        
        print(f"✓ DataFrame creado con {len(df)} filas y {len(df.columns)} columnas")
        
        # Crear buffer de memoria
        buffer = io.BytesIO()
        
        # Crear archivo Excel con formato
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Escribir datos principales
            df.to_excel(
                writer, 
                sheet_name='Analisis_Validados',
                index=False,
                freeze_panes=(1, 0)  # Congelar primera fila
            )
            
            # Obtener el worksheet para aplicar formato
            worksheet = writer.sheets['Analisis_Validados']
            
            # Aplicar formato a los encabezados
            header_font = openpyxl.styles.Font(bold=True, color='FFFFFF')
            header_fill = openpyxl.styles.PatternFill(start_color='366092', end_color='366092', fill_type='solid')
            
            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = openpyxl.styles.Alignment(horizontal='center')
            
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
                
                # Limitar ancho máximo
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            # Agregar hoja de resumen
            usuario_info = f"Usuario: {resultados[0][1]} (ID: {user_id})"
            archivo_info = f"Archivo: {nombre_archivo}"
            total_info = f"Total de análisis: {len(datos_excel)}"
            fecha_generacion = f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            resumen_df = pd.DataFrame({
                'Información': [usuario_info, archivo_info, total_info, fecha_generacion],
                'Detalle': ['', '', '', '']
            })
            
            resumen_df.to_excel(
                writer,
                sheet_name='Resumen',
                index=False
            )
        
        # Posicionar el buffer al inicio
        buffer.seek(0)
        
        print("✅ Archivo Excel generado exitosamente")
        
        return buffer
        
    except Exception as e:
        print(f"❌ Error generando Excel: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return None


def obtener_nombre_archivo_descarga(usuario_info: Dict, nombre_archivo_original: str) -> str:
    """
    Genera un nombre apropiado para el archivo de descarga.
    
    Args:
        usuario_info (Dict): Información del usuario
        nombre_archivo_original (str): Nombre original del archivo
        
    Returns:
        str: Nombre del archivo para descarga
    """
    try:
        # Obtener nombre del usuario (sin espacios ni caracteres especiales)
        usuario_nombre = usuario_info.get('nombre', 'Usuario')
        usuario_correo = usuario_info.get('correo', 'sin_correo')
        
        # Usar nombre si está disponible, sino usar la parte antes del @ del correo
        if usuario_nombre and usuario_nombre.strip() and usuario_nombre != 'Usuario':
            identificador = usuario_nombre.strip()
        else:
            identificador = usuario_correo.split('@')[0] if '@' in usuario_correo else usuario_correo
        
        # Limpiar identificador
        identificador = "".join(c for c in identificador if c.isalnum() or c in (' ', '_', '-')).strip()
        identificador = identificador.replace(' ', '_')
        
        # Limpiar nombre de archivo original
        nombre_limpio = "".join(c for c in nombre_archivo_original if c.isalnum() or c in (' ', '_', '-', '.')).strip()
        nombre_limpio = nombre_limpio.replace(' ', '_')
        
        # Remover extensión si la tiene
        if '.' in nombre_limpio:
            nombre_sin_ext = '.'.join(nombre_limpio.split('.')[:-1])
        else:
            nombre_sin_ext = nombre_limpio
        
        # Fecha actual
        fecha_actual = datetime.now().strftime('%Y%m%d_%H%M')
        
        # Formar nombre final
        nombre_descarga = f"AnalisisValidados_{identificador}_{nombre_sin_ext}_{fecha_actual}.xlsx"
        
        # Limitar longitud total
        if len(nombre_descarga) > 150:
            nombre_descarga = f"AnalisisValidados_{identificador[:20]}_{fecha_actual}.xlsx"
        
        return nombre_descarga
        
    except Exception as e:
        print(f"⚠️ Error generando nombre de archivo: {e}")
        fecha_actual = datetime.now().strftime('%Y%m%d_%H%M')
        return f"AnalisisValidados_{fecha_actual}.xlsx"


# Importar openpyxl para el formato
try:
    import openpyxl
    import openpyxl.styles
except ImportError:
    print("⚠️ openpyxl no está instalado. El formato avanzado no estará disponible.")
    openpyxl = None