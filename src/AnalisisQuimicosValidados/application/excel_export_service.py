# src/AnalisisQuimicosValidados/application/excel_export_service.py
import pandas as pd
from io import BytesIO
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
import traceback

from src.Users.infrastructure.users_model import Users
from src.AnalisisQuimicosPendientes.infrastructure.analisis_quimicos_model import (
    AnalisisQuimicosPendientes,
)


def generar_excel_pendientes_por_usuario(
    correo_usuario: str, db: Session
) -> Optional[BytesIO]:
    """
    Genera un archivo Excel con todos los análisis químicos pendientes de un usuario.
    
    Args:
        correo_usuario (str): Correo electrónico del usuario
        db (Session): Sesión de base de datos
        
    Returns:
        Optional[BytesIO]: Archivo Excel en memoria o None si hay error
    """
    try:
        print(f"=== GENERANDO EXCEL PARA: {correo_usuario} ===")
        
        # Buscar usuario por correo
        usuario = db.query(Users).filter(
            Users.correo == correo_usuario.strip().lower()
        ).first()
        
        if not usuario:
            print(f"Usuario no encontrado: {correo_usuario}")
            return None
        
        print(f"Usuario encontrado: {usuario.ID_user} - {usuario.correo}")
        
        # Obtener análisis pendientes del usuario
        analisis_pendientes = (
            db.query(AnalisisQuimicosPendientes)
            .filter(
                AnalisisQuimicosPendientes.user_id_FK == usuario.ID_user,
                AnalisisQuimicosPendientes.estatus == "pendiente"
            )
            .order_by(AnalisisQuimicosPendientes.fecha_creacion.desc())
            .all()
        )
        
        if not analisis_pendientes:
            print(f"No se encontraron análisis pendientes para el usuario: {correo_usuario}")
            return None
        
        print(f"Análisis pendientes encontrados: {len(analisis_pendientes)}")
        
        # Convertir los datos a una lista de diccionarios
        datos_excel = []
        for analisis in analisis_pendientes:
            try:
                fila = {
                    "ID": analisis.id,
                    "Municipio": analisis.municipio,
                    "Localidad": analisis.localidad,
                    "Nombre Productor": analisis.nombre_productor,
                    "Cultivo Anterior": analisis.cultivo_anterior,
                    "Arcilla (%)": float(analisis.arcilla) if analisis.arcilla else None,
                    "Limo (%)": float(analisis.limo) if analisis.limo else None,
                    "Arena (%)": float(analisis.arena) if analisis.arena else None,
                    "Textura": analisis.textura,
                    "Densidad Aparente": float(analisis.da) if analisis.da else None,
                    "pH": float(analisis.ph) if analisis.ph else None,
                    "Materia Orgánica (%)": float(analisis.mo) if analisis.mo else None,
                    "Fósforo (ppm)": float(analisis.fosforo) if analisis.fosforo else None,
                    "N Inorgánico (ppm)": float(analisis.n_inorganico) if analisis.n_inorganico else None,
                    "Potasio (ppm)": float(analisis.k) if analisis.k else None,
                    "Magnesio (ppm)": float(analisis.mg) if analisis.mg else None,
                    "Calcio (ppm)": float(analisis.ca) if analisis.ca else None,
                    "Sodio (ppm)": float(analisis.na) if analisis.na else None,
                    "Aluminio (ppm)": float(analisis.al) if analisis.al else None,
                    "CIC (meq/100g)": float(analisis.cic) if analisis.cic else None,
                    "CIC Calculada": float(analisis.cic_calculada) if analisis.cic_calculada else None,
                    "Hidrógeno (ppm)": float(analisis.h) if analisis.h else None,
                    "Azufre (ppm)": float(analisis.azufre) if analisis.azufre else None,
                    "Hierro (ppm)": float(analisis.hierro) if analisis.hierro else None,
                    "Cobre (ppm)": float(analisis.cobre) if analisis.cobre else None,
                    "Zinc (ppm)": float(analisis.zinc) if analisis.zinc else None,
                    "Manganeso (ppm)": float(analisis.manganeso) if analisis.manganeso else None,
                    "Boro (ppm)": float(analisis.boro) if analisis.boro else None,
                    "Ca/Mg": float(analisis.ca_mg) if analisis.ca_mg else None,
                    "Mg/K": float(analisis.mg_k) if analisis.mg_k else None,
                    "Ca/K": float(analisis.ca_k) if analisis.ca_k else None,
                    "Ca+Mg/K": float(analisis.ca_mg_k) if analisis.ca_mg_k else None,
                    "K/Mg": float(analisis.k_mg) if analisis.k_mg else None,
                    "Estatus": analisis.estatus,
                    "Comentario": analisis.comentario_invalido,
                    "Fecha Creación": analisis.fecha_creacion.strftime("%Y-%m-%d %H:%M:%S") if analisis.fecha_creacion else None,
                }
                datos_excel.append(fila)
                
            except Exception as e:
                print(f"Error procesando análisis {analisis.id}: {e}")
                continue
        
        # Crear DataFrame
        df = pd.DataFrame(datos_excel)
        
        if df.empty:
            print("No se pudieron procesar los datos para Excel")
            return None
        
        # Crear archivo Excel en memoria
        buffer = BytesIO()
        
        # Usar ExcelWriter para mejor control del formato
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            # Escribir datos principales
            df.to_excel(
                writer, 
                sheet_name='Análisis Pendientes', 
                index=False,
                startrow=4  # Dejar espacio para el encabezado
            )
            
            # Obtener la hoja de trabajo para agregar información adicional
            worksheet = writer.sheets['Análisis Pendientes']
            
            # Agregar información del usuario en las primeras filas
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            nombre_completo = f"{usuario.nombre or ''} {usuario.apellido or ''}".strip()
            
            worksheet['A1'] = f"ANÁLISIS QUÍMICOS PENDIENTES"
            worksheet['A2'] = f"Usuario: {correo_usuario}"
            worksheet['A3'] = f"Nombre: {nombre_completo}"
            worksheet['A4'] = f"Fecha de exportación: {fecha_actual}"
            worksheet['A5'] = f"Total de análisis: {len(datos_excel)}"
            
            # Aplicar formato a los encabezados
            from openpyxl.styles import Font, PatternFill, Alignment
            
            # Estilo para el título principal
            title_font = Font(bold=True, size=14)
            worksheet['A1'].font = title_font
            
            # Estilo para la información del usuario
            info_font = Font(bold=True, size=10)
            for row in range(2, 6):
                worksheet[f'A{row}'].font = info_font
            
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
                adjusted_width = min(max_length + 2, 30)  # Máximo 30 caracteres
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        buffer.seek(0)
        print(f"✅ Excel generado exitosamente con {len(datos_excel)} registros")
        
        return buffer
        
    except Exception as e:
        print(f"❌ Error generando Excel: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return None


def obtener_nombre_archivo_excel(correo_usuario: str) -> str:
    """
    Genera un nombre de archivo Excel basado en el correo del usuario y la fecha actual.
    
    Args:
        correo_usuario (str): Correo del usuario
        
    Returns:
        str: Nombre del archivo
    """
    fecha_actual = datetime.now().strftime("%Y%m%d_%H%M%S")
    usuario_limpio = correo_usuario.split('@')[0]  # Tomar solo la parte antes del @
    return f"analisis_pendientes_{usuario_limpio}_{fecha_actual}.xlsx"


def validar_usuario_existe(correo_usuario: str, db: Session) -> bool:
    """
    Valida si un usuario existe en la base de datos.
    
    Args:
        correo_usuario (str): Correo del usuario
        db (Session): Sesión de base de datos
        
    Returns:
        bool: True si existe, False si no existe
    """
    try:
        usuario = db.query(Users).filter(
            Users.correo == correo_usuario.strip().lower()
        ).first()
        return usuario is not None
    except Exception as e:
        print(f"Error validando usuario: {e}")
        return False


def contar_pendientes_usuario(correo_usuario: str, db: Session) -> int:
    """
    Cuenta el número de análisis pendientes de un usuario.
    
    Args:
        correo_usuario (str): Correo del usuario
        db (Session): Sesión de base de datos
        
    Returns:
        int: Número de análisis pendientes
    """
    try:
        usuario = db.query(Users).filter(
            Users.correo == correo_usuario.strip().lower()
        ).first()
        
        if not usuario:
            return 0
        
        count = (
            db.query(AnalisisQuimicosPendientes)
            .filter(
                AnalisisQuimicosPendientes.user_id_FK == usuario.ID_user,
                AnalisisQuimicosPendientes.estatus == "pendiente"
            )
            .count()
        )
        
        return count
        
    except Exception as e:
        print(f"Error contando pendientes: {e}")
        return 0