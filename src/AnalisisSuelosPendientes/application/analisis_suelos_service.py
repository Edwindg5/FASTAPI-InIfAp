# src/AnalisisSuelosPendientes/application/analisis_suelos_service.py
import pandas as pd
import io
from datetime import datetime
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, create_engine
from src.AnalisisSuelosPendientes.infrastructure.analisis_suelos_model import AnalisisSuelosPendientes
from src.AnalisisSuelosPendientes.application.analisis_suelos_schemas import AnalisisSuelosCreate, AnalisisSuelosResponse
from src.municipios.infrastructure.municipios_model import Municipios

class AnalisisSuelosService:
    
    # Mapeo correcto de columnas de Excel a campos de BD
    COLUMN_MAPPING = {
        'N°': 'numero',
        'Clave estatal': 'clave_estatal', 
        'estado_cuadernillo': 'estado_cuadernillo',
        'Clave municipio': 'clave_municipio',
        'clave munip': 'clave_munip',
        'municipio_cuadernillo': 'municipio_cuadernillo',
        'Clave localidad': 'clave_localidad',
        'localidad_cuadernillo': 'localidad_cuadernillo',
        'Recuento de CURP_Renapo': 'recuento_curp_renapo',
        ' Recuento de CURP_Renapo ': 'recuento_curp_renapo',  # Con espacios
        'extraccion edo': 'extraccion_edo',
        'CLAVE': 'clave',
        'DDR': 'ddr',
        'CADER': 'cader',
        'X': 'coordenada_x',
        'Y': 'coordenada_y',
        'Elevacion msnm': 'elevacion_msnm',
        'Profundidad de muestreo': 'profundidad_muestreo',
        'Fecha de muestreo': 'fecha_muestreo',
        'Parcela': 'parcela',
        'Cultivo anterior': 'cultivo_anterior',
        'Cultivo a establecer': 'cultivo_establecer',
        'Manejo': 'manejo',
        'Tipo vegetación': 'tipo_vegetacion',
        # Datos del técnico (primeras columnas)
        'Nombre': 'nombre_tecnico',
        'Tel': 'tel_tecnico',
        'Correo': 'correo_tecnico',
        # Datos del productor (columnas renombradas por pandas)
        'Nombre.1': 'nombre_productor',
        'Tel.1': 'tel_productor',
        'Correo.1': 'correo_productor',
        # Posibles variaciones de nombres que pandas podría crear
        'Nombre ': 'nombre_tecnico',        # Con espacio al final
        'Tel ': 'tel_tecnico',              # Con espacio al final
        'Correo ': 'correo_tecnico',        # Con espacio al final
        'Nombre .1': 'nombre_productor',    # Con espacio antes del .1
        'Tel .1': 'tel_productor',          # Con espacio antes del .1
        'Correo .1': 'correo_productor',    # Con espacio antes del .1
        # Campos finales
        'Muestra': 'muestra',
        'Reemplazo': 'reemplazo',
        'NOMBRE REVISOR': 'nombre_revisor'
    }
    
    @staticmethod
    def cache_municipios(db: Session) -> Dict[str, int]:
        """Cache todos los municipios en memoria para búsqueda rápida"""
        print("Cargando cache de municipios...")
        municipios_cache = {}
        
        municipios = db.query(Municipios).all()
        
        for municipio in municipios:
            nombre = municipio.nombre
            if nombre:
                # Múltiples variaciones para búsqueda rápida
                municipios_cache[nombre] = municipio.id_municipio
                municipios_cache[nombre.upper()] = municipio.id_municipio
                municipios_cache[nombre.lower()] = municipio.id_municipio
                municipios_cache[nombre.strip()] = municipio.id_municipio
                
                # Versión sin acentos
                nombre_sin_acentos = (nombre.replace('á', 'a').replace('é', 'e')
                                    .replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
                                    .replace('ñ', 'n').replace('Á', 'A').replace('É', 'E')
                                    .replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')
                                    .replace('Ñ', 'N'))
                municipios_cache[nombre_sin_acentos.upper()] = municipio.id_municipio
        
        print(f"Cache cargado: {len(municipios)} municipios únicos")
        return municipios_cache
    
    @staticmethod
    def find_municipio_id_fast(municipio_nombre: str, municipios_cache: Dict[str, int]) -> int:
        """Búsqueda ultra rápida usando cache en memoria"""
        if not municipio_nombre or pd.isna(municipio_nombre):
            return None
            
        municipio_clean = str(municipio_nombre).strip()
        
        if not municipio_clean or municipio_clean.lower() == 'nan':
            return None
        
        # Búsquedas progresivas en cache
        search_variants = [
            municipio_clean,
            municipio_clean.upper(),
            municipio_clean.lower(),
            municipio_clean.strip(),
        ]
        
        # Búsqueda directa en cache
        for variant in search_variants:
            if variant in municipios_cache:
                return municipios_cache[variant]
        
        # Búsqueda parcial en cache
        municipio_upper = municipio_clean.upper()
        for cached_name, municipio_id in municipios_cache.items():
            if municipio_upper in cached_name.upper() or cached_name.upper() in municipio_upper:
                return municipio_id
        
        return None
    
    @staticmethod
    def process_date_fast(value) -> datetime.date:
        """Procesamiento robusto de fechas"""
        if pd.isna(value) or value == '' or str(value).strip() == '':
            return None
        
        try:
            # Si ya es datetime
            if hasattr(value, 'date'):
                return value.date()
            
            # Si es string
            if isinstance(value, str):
                value_clean = value.strip()
                
                # Caso especial "07/052024" -> "07/05/2024"
                if '/' in value_clean and len(value_clean) <= 10:
                    parts = value_clean.split('/')
                    if len(parts) == 2 and len(parts[1]) >= 6:
                        day = parts[0]
                        month_year = parts[1]
                        if len(month_year) == 6:  # "052024"
                            month = month_year[:2]   # "05"
                            year = month_year[2:]    # "2024"
                            value_clean = f"{day}/{month}/{year}"
                
                # Intentar formatos más comunes primero
                date_formats = [
                    '%d/%m/%Y',  # 07/05/2024
                    '%d/%m/%y',  # 07/05/24
                    '%Y-%m-%d',  # 2024-05-07
                    '%d-%m-%Y',  # 07-05-2024
                    '%d-%m-%y',  # 07-05-24
                    '%m/%d/%Y',  # 05/07/2024
                    '%m-%d-%Y'   # 05-07-2024
                ]
                
                for fmt in date_formats:
                    try:
                        return datetime.strptime(value_clean, fmt).date()
                    except ValueError:
                        continue
            
            return None
        except Exception as e:
            print(f"Error procesando fecha '{value}': {str(e)}")
            return None
    
    @staticmethod
    def process_int_fast(value) -> int:
        """Conversión robusta a entero"""
        if pd.isna(value) or value == '' or str(value).strip() == '':
            return None
        
        try:
            # Limpiar y convertir
            clean_value = str(value).replace(',', '').replace(' ', '').strip()
            if clean_value and clean_value.lower() != 'nan':
                # Manejar números decimales convertidos a enteros
                return int(float(clean_value))
            return None
        except Exception as e:
            print(f"Error procesando número '{value}': {str(e)}")
            return None
    
    @staticmethod
    def process_text_fast(value, max_length: int = None) -> str:
        """Procesamiento robusto de texto con límite de longitud"""
        if pd.isna(value) or value == '':
            return None
        
        clean_text = str(value).strip()
        if not clean_text or clean_text.lower() in ['nan', 'none', '']:
            return None
        
        # Aplicar límite de longitud si se especifica
        if max_length and len(clean_text) > max_length:
            clean_text = clean_text[:max_length]
            print(f"Texto truncado a {max_length} caracteres: {clean_text}")
        
        return clean_text
    
    @staticmethod
    def safe_get_column_value(row, column_name: str, df_columns: list):
        """Obtiene valor de columna de manera segura"""
        try:
            if column_name in df_columns:
                idx = df_columns.index(column_name)
                if idx < len(row):
                    return row.iloc[idx]
            return None
        except Exception as e:
            print(f"Error obteniendo valor de columna '{column_name}': {str(e)}")
            return None
    
    @staticmethod
    def check_row_has_any_data(row) -> bool:
        """Verifica si una fila tiene algún dato válido en cualquier columna"""
        for value in row:
            if pd.notna(value) and str(value).strip() not in ['', 'nan', 'None', 'null']:
                return True
        return False
    
    @staticmethod
    def dynamic_column_mapping(df_columns: list) -> Dict[str, str]:
        """Crea mapeo dinámico basado en las columnas reales del Excel"""
        dynamic_mapping = {}
        
        # Identificar columnas Nombre, Tel, Correo automáticamente
        nombre_cols = [col for col in df_columns if 'nombre' in col.lower() or col.strip() == 'Nombre']
        tel_cols = [col for col in df_columns if 'tel' in col.lower() or col.strip() == 'Tel']
        correo_cols = [col for col in df_columns if 'correo' in col.lower() or col.strip() == 'Correo']
        
        # Mapear primera aparición a técnico
        if len(nombre_cols) >= 1:
            dynamic_mapping[nombre_cols[0]] = 'nombre_tecnico'
        if len(tel_cols) >= 1:
            dynamic_mapping[tel_cols[0]] = 'tel_tecnico'
        if len(correo_cols) >= 1:
            dynamic_mapping[correo_cols[0]] = 'correo_tecnico'
            
        # Mapear segunda aparición a productor
        if len(nombre_cols) >= 2:
            dynamic_mapping[nombre_cols[1]] = 'nombre_productor'
        if len(tel_cols) >= 2:
            dynamic_mapping[tel_cols[1]] = 'tel_productor'
        if len(correo_cols) >= 2:
            dynamic_mapping[correo_cols[1]] = 'correo_productor'
        
        return dynamic_mapping
    
    @staticmethod
    def bulk_insert_optimized(records: List[Dict], db: Session) -> Tuple[int, int, List[str]]:
        """Inserción masiva ultra rápida usando SQL crudo - SIN LÍMITES DE 1000"""
        if not records:
            return 0, 0, []
        
        success_count = 0
        error_count = 0
        errors = []
        
        try:
            # Preparar SQL para inserción masiva
            fields = [
                'municipio_id_FK', 'numero', 'clave_estatal', 'estado_cuadernillo', 'clave_municipio',
                'clave_munip', 'municipio_cuadernillo', 'clave_localidad', 'localidad_cuadernillo',
                'recuento_curp_renapo', 'extraccion_edo', 'clave', 'ddr', 'cader',
                'coordenada_x', 'coordenada_y', 'elevacion_msnm', 'profundidad_muestreo',
                'fecha_muestreo', 'parcela', 'cultivo_anterior', 'cultivo_establecer',
                'manejo', 'tipo_vegetacion', 'nombre_tecnico', 'tel_tecnico', 'correo_tecnico',
                'nombre_productor', 'tel_productor', 'correo_productor', 'muestra',
                'reemplazo', 'nombre_revisor', 'estatus', 'user_id_FK'
            ]
            
            # Crear placeholders para valores
            placeholders = ', '.join([f':{field}' for field in fields])
            fields_str = ', '.join(fields)
            
            insert_sql = text(f"""
                INSERT INTO analisis_suelos_pendientes ({fields_str})
                VALUES ({placeholders})
            """)
            
            # CAMBIO CRÍTICO: Aumentar tamaño del lote para manejar más registros
            BATCH_SIZE = 500  # Incrementado de 200 a 500 para mejor rendimiento
            total_batches = (len(records) + BATCH_SIZE - 1) // BATCH_SIZE
            
            print(f"INSERTANDO {len(records)} REGISTROS TOTAL en {total_batches} lotes de {BATCH_SIZE}...")
            
            for i in range(0, len(records), BATCH_SIZE):
                batch = records[i:i + BATCH_SIZE]
                batch_num = (i // BATCH_SIZE) + 1
                
                try:
                    # Ejecutar lote
                    db.execute(insert_sql, batch)
                    success_count += len(batch)
                    print(f"  ✅ Lote {batch_num}/{total_batches}: {len(batch)} registros insertados (Total: {success_count}/{len(records)})")
                    
                    # COMMITEAR cada lote para evitar problemas de memoria
                    db.commit()
                    
                except Exception as e:
                    error_count += len(batch)
                    error_msg = f"Error en lote {batch_num}: {str(e)}"
                    errors.append(error_msg)
                    print(f"  ❌ Error: {error_msg}")
                    db.rollback()  # Rollback solo del lote fallido
                    continue
            
            print(f"🎉 INSERCIÓN COMPLETADA: {success_count} registros insertados exitosamente de {len(records)} totales")
            
        except Exception as e:
            error_msg = f"Error crítico en inserción masiva: {str(e)}"
            errors.append(error_msg)
            print(f"💥 Error general: {error_msg}")
            db.rollback()
        
        return success_count, error_count, errors
    
    @staticmethod
    def process_excel_file(file_content: bytes, user_id: int, db: Session) -> Dict[str, Any]:
        """Procesamiento mejorado de archivo Excel - PROCESANDO TODAS LAS FILAS"""
        try:
            print("🚀 INICIANDO PROCESAMIENTO DE ARCHIVO EXCEL...")
            start_time = datetime.now()
            
            # 1. Cargar cache de municipios
            municipios_cache = AnalisisSuelosService.cache_municipios(db)
            
            # 2. Leer Excel - SIN LÍMITES
            print("📖 Leyendo archivo Excel...")
            df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl', header=1)
            print(f"📋 Archivo cargado: {len(df)} filas, {len(df.columns)} columnas")
            
            # 3. Limpiar nombres de columnas y mostrarlas para debug
            df.columns = [str(col).strip() for col in df.columns]
            print("🏷️  Columnas encontradas:")
            for i, col in enumerate(df.columns[:10]):  # Mostrar solo las primeras 10
                print(f"  {i}: '{col}'")
            if len(df.columns) > 10:
                print(f"  ... y {len(df.columns) - 10} columnas más")
            
            # 4. Crear mapeo combinado (estático + dinámico)
            combined_mapping = AnalisisSuelosService.COLUMN_MAPPING.copy()
            dynamic_mapping = AnalisisSuelosService.dynamic_column_mapping(df.columns.tolist())
            combined_mapping.update(dynamic_mapping)
            
            print("🔗 Mapeo de columnas aplicado:")
            mapped_count = 0
            for excel_col, db_field in combined_mapping.items():
                if excel_col in df.columns:
                    mapped_count += 1
                    if mapped_count <= 10:  # Mostrar solo los primeros 10
                        print(f"  '{excel_col}' -> {db_field}")
            if mapped_count > 10:
                print(f"  ... y {mapped_count - 10} mapeos más")
            
            # 5. Campos que necesitan conversión especial y límites de longitud
            int_fields = {'numero', 'clave_estatal', 'clave_municipio', 'elevacion_msnm', 'recuento_curp_renapo'}
            date_fields = {'fecha_muestreo'}
            
            # Definir límites de longitud para campos de texto críticos
            text_field_limits = {
                'tel_tecnico': 20,
                'tel_productor': 20,
                'correo_tecnico': 150,
                'correo_productor': 150,
                'nombre_tecnico': 150,
                'nombre_productor': 150,
                'estado_cuadernillo': 100,
                'municipio_cuadernillo': 100,
                'clave_munip': 10,
                'clave_localidad': 10,
                'localidad_cuadernillo': 100,
                'extraccion_edo': 10,
                'clave': 50,
                'ddr': 100,
                'cader': 100,
                'coordenada_x': 50,
                'coordenada_y': 50,
                'profundidad_muestreo': 50,
                'parcela': 100,
                'cultivo_anterior': 100,
                'cultivo_establecer': 100,
                'manejo': 100,
                'tipo_vegetacion': 100,
                'muestra': 50,
                'reemplazo': 50,
                'nombre_revisor': 150,
                'estatus': 20
            }
            
            records_to_insert = []
            municipios_not_found = set()
            processing_errors = []
            
            print(f"⚡ Procesando TODAS las {len(df)} filas del Excel...")
            
            # 6. Procesar TODAS las filas - SIN LÍMITES
            skipped_rows = []
            empty_rows = 0
            progress_step = max(1, len(df) // 10)  # Mostrar progreso cada 10%
            
            for index, row in df.iterrows():
                try:
                    # Mostrar progreso cada cierto porcentaje
                    if (index + 1) % progress_step == 0:
                        progress_percent = ((index + 1) / len(df)) * 100
                        print(f"  📊 Progreso: {index + 1}/{len(df)} filas ({progress_percent:.1f}%)")
                    
                    data = {}
                    row_has_data = False
                    
                    # Verificar si la fila tiene ALGÚN dato
                    row_completely_empty = not AnalisisSuelosService.check_row_has_any_data(row)
                    
                    if row_completely_empty:
                        empty_rows += 1
                        # Aún así, procesar la fila con datos mínimos
                    
                    # Mapear valores usando el diccionario de mapeo combinado
                    for excel_col, db_field in combined_mapping.items():
                        value = AnalisisSuelosService.safe_get_column_value(row, excel_col, df.columns.tolist())
                        
                        # Solo procesar si encontramos el valor y el campo no está ya asignado
                        if value is not None and (db_field not in data or data[db_field] is None):
                            # Aplicar conversión según tipo de campo
                            if db_field in int_fields:
                                processed_value = AnalisisSuelosService.process_int_fast(value)
                            elif db_field in date_fields:
                                processed_value = AnalisisSuelosService.process_date_fast(value)
                            else:
                                # Aplicar límite de longitud si existe
                                max_length = text_field_limits.get(db_field)
                                processed_value = AnalisisSuelosService.process_text_fast(value, max_length)
                            
                            data[db_field] = processed_value
                            
                            # Marcar que la fila tiene datos si encontramos algo válido
                            if processed_value is not None:
                                row_has_data = True
                    
                    # Validación de municipio - PERMITIR MUNICIPIOS NO ENCONTRADOS
                    municipio_nombre = data.get('municipio_cuadernillo')
                    if municipio_nombre:
                        municipio_id = AnalisisSuelosService.find_municipio_id_fast(municipio_nombre, municipios_cache)
                        data['municipio_id_FK'] = municipio_id
                        if not municipio_id:
                            municipios_not_found.add(str(municipio_nombre))
                    else:
                        data['municipio_id_FK'] = None
                    
                    # Campos obligatorios
                    data['user_id_FK'] = user_id
                    data['estatus'] = 'pendiente'
                    
                    # Validar número - SIEMPRE asigna
                    if data.get('numero') is None:
                        data['numero'] = index + 1
                    
                    # SIEMPRE agregar la fila al resultado
                    records_to_insert.append(data)
                    
                except Exception as e:
                    error_msg = f"Error procesando fila {index + 1}: {str(e)}"
                    processing_errors.append(error_msg)
                    
                    # AÚN ASÍ, intentar crear un registro mínimo
                    try:
                        minimal_data = {
                            'numero': index + 1,
                            'user_id_FK': user_id,
                            'estatus': 'pendiente',
                            'municipio_id_FK': None
                        }
                        records_to_insert.append(minimal_data)
                    except:
                        skipped_rows.append(index + 1)
                        continue
            
            print(f"📊 ESTADÍSTICAS DE PROCESAMIENTO:")
            print(f"  📋 Total de filas en Excel: {len(df)}")
            print(f"  💾 Registros preparados para insertar: {len(records_to_insert)}")
            print(f"  🗂️ Filas aparentemente vacías: {empty_rows}")
            print(f"  ⚠️ Errores de procesamiento: {len(processing_errors)}")
            print(f"  ❌ Filas completamente saltadas: {len(skipped_rows)}")
            print(f"  🏘️ Municipios no encontrados: {len(municipios_not_found)}")
            
            # 7. Inserción masiva - PROCESANDO TODOS LOS REGISTROS
            print(f"💾 Iniciando inserción de {len(records_to_insert)} registros en base de datos...")
            success_count, error_count, errors = AnalisisSuelosService.bulk_insert_optimized(records_to_insert, db)
            
            # 8. Estadísticas finales
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            print(f"🎉 PROCESAMIENTO COMPLETADO en {processing_time:.2f} segundos")
            print(f"📈 Estadísticas finales: {success_count} exitosos, {error_count} errores")
            
            # Mensaje final mejorado
            message_parts = []
            if success_count > 0:
                message_parts.append(f"✅ Archivo procesado exitosamente en {processing_time:.2f}s.")
                message_parts.append(f"💾 {success_count} de {len(records_to_insert)} registros insertados.")
                
                if success_count < len(records_to_insert):
                    message_parts.append(f"⚠️ {len(records_to_insert) - success_count} registros tuvieron errores.")
            else:
                message_parts.append("❌ No se pudo insertar ningún registro.")
            
            if municipios_not_found:
                message_parts.append(f"🏘️ {len(municipios_not_found)} municipios no encontrados (registrados con municipio_id_FK=NULL).")
            
            final_message = " ".join(message_parts)
            
            return {
                "message": final_message,
                "records_processed": len(df),  # Total de filas en el Excel
                "success_count": success_count,  # Registros insertados exitosamente
                "error_count": error_count + len(processing_errors),
                "processing_time_seconds": round(processing_time, 2),
                "errors": errors + processing_errors[:5],  # Solo los primeros 5 errores
                "municipios_not_found": list(municipios_not_found) if municipios_not_found else []
            }
            
        except Exception as e:
            db.rollback()
            error_msg = f"💥 Error crítico procesando archivo: {str(e)}"
            print(error_msg)
            raise Exception(error_msg)
    
  
    @staticmethod
    def get_analisis_suelos_by_id(db: Session, analisis_id: int) -> AnalisisSuelosPendientes:
        """Obtiene un análisis de suelos por ID"""
        return db.query(AnalisisSuelosPendientes).filter(AnalisisSuelosPendientes.id == analisis_id).first()
    
    @staticmethod
    def create_analisis_suelos(db: Session, analisis_data: AnalisisSuelosCreate) -> AnalisisSuelosPendientes:
        """Crea un nuevo análisis de suelos"""
        db_analisis = AnalisisSuelosPendientes(**analisis_data.dict())
        db.add(db_analisis)
        db.commit()
        db.refresh(db_analisis)
        return db_analisis
    
    @staticmethod
    def delete_analisis_suelos(db: Session, analisis_id: int) -> bool:
        """Elimina un análisis de suelos por ID"""
        analisis = db.query(AnalisisSuelosPendientes).filter(AnalisisSuelosPendientes.id == analisis_id).first()
        if analisis:
            db.delete(analisis)
            db.commit()
            return True
        return False

