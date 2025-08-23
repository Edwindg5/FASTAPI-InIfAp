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
    def get_all_analisis_suelos(db: Session, skip: int = 0, limit: int = 100) -> List[AnalisisSuelosPendientes]:
        """Obtiene todos los análisis de suelos pendientes"""
        return db.query(AnalisisSuelosPendientes).offset(skip).limit(limit).all()
    
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
    @staticmethod
    def get_analisis_suelos_pendientes_by_user(
        db: Session, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[AnalisisSuelosPendientes]:
        """
        Obtiene solo los análisis de suelos PENDIENTES de un usuario específico
        """
        return db.query(AnalisisSuelosPendientes).filter(
            AnalisisSuelosPendientes.user_id_FK == user_id,
            AnalisisSuelosPendientes.estatus == 'pendiente'
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def count_analisis_suelos_pendientes_by_user(db: Session, user_id: int) -> int:
        """
        Cuenta el número total de análisis de suelos pendientes de un usuario específico
        """
        return db.query(AnalisisSuelosPendientes).filter(
            AnalisisSuelosPendientes.user_id_FK == user_id,
            AnalisisSuelosPendientes.estatus == 'pendiente'
        ).count()
    
    @staticmethod
    def get_all_analisis_by_user(
        db: Session, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[AnalisisSuelosPendientes]:
        """
        Obtiene TODOS los análisis de suelos de un usuario específico (cualquier estatus)
        """
        return db.query(AnalisisSuelosPendientes).filter(
            AnalisisSuelosPendientes.user_id_FK == user_id
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_analisis_by_user_and_status(
        db: Session, 
        user_id: int, 
        estatus: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[AnalisisSuelosPendientes]:
        """
        Obtiene análisis de suelos de un usuario específico filtrados por estatus
        """
        return db.query(AnalisisSuelosPendientes).filter(
            AnalisisSuelosPendientes.user_id_FK == user_id,
            AnalisisSuelosPendientes.estatus == estatus
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_estatus_analisis(db: Session, analisis_id: int, nuevo_estatus: str) -> AnalisisSuelosPendientes:
        """
        Actualiza el estatus de un análisis de suelos específico
        """
        analisis = db.query(AnalisisSuelosPendientes).filter(
            AnalisisSuelosPendientes.id == analisis_id
        ).first()
        
        if analisis:
            analisis.estatus = nuevo_estatus
            db.commit()
            db.refresh(analisis)
        
        return analisis
    
    @staticmethod
    def get_usuarios_con_analisis_pendientes(
        db: Session, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene todos los usuarios que tienen análisis de suelos pendientes
        con información resumida de cada usuario
        """
        from src.Users.infrastructure.users_model import Users
        from src.municipios.infrastructure.municipios_model import Municipios
        from sqlalchemy import func, distinct
        
        # Consulta para obtener usuarios con análisis pendientes y su información
        query = db.query(
            AnalisisSuelosPendientes.user_id_FK.label('user_id'),
            Users.nombre.label('nombre_usuario'),
            Users.apellido.label('apellido_usuario'), 
            Users.correo.label('correo_usuario'),
            func.count(AnalisisSuelosPendientes.id).label('total_pendientes'),
            func.max(AnalisisSuelosPendientes.fecha_creacion).label('ultimo_analisis_fecha')
        ).join(
            Users, AnalisisSuelosPendientes.user_id_FK == Users.ID_user, isouter=True
        ).filter(
            AnalisisSuelosPendientes.estatus == 'pendiente'
        ).group_by(
            AnalisisSuelosPendientes.user_id_FK,
            Users.nombre,
            Users.apellido,
            Users.correo
        ).offset(skip).limit(limit)
        
        resultados = query.all()
        
        usuarios_con_pendientes = []
        
        for resultado in resultados:
            # Obtener municipios involucrados para este usuario
            municipios_query = db.query(distinct(Municipios.nombre)).join(
                AnalisisSuelosPendientes, 
                Municipios.id_municipio == AnalisisSuelosPendientes.municipio_id_FK
            ).filter(
                AnalisisSuelosPendientes.user_id_FK == resultado.user_id,
                AnalisisSuelosPendientes.estatus == 'pendiente',
                Municipios.nombre.isnot(None)
            ).all()
            
            municipios_nombres = [m[0] for m in municipios_query if m[0]]
            
            usuario_data = {
                'user_id': resultado.user_id,
                'nombre_usuario': resultado.nombre_usuario,
                'apellido_usuario': resultado.apellido_usuario,
                'correo_usuario': resultado.correo_usuario,
                'total_pendientes': resultado.total_pendientes,
                'ultimo_analisis_fecha': resultado.ultimo_analisis_fecha,
                'municipios_involucrados': municipios_nombres
            }
            
            usuarios_con_pendientes.append(usuario_data)
        
        return usuarios_con_pendientes
    
    @staticmethod
    def crear_comentario_invalido(
        db: Session, 
        admin_id: int, 
        correo_usuario: str, 
        comentario_invalido: str
    ) -> Dict[str, Any]:
        """
        Crea comentarios inválidos para un usuario. Si no tiene análisis pendientes,
        crea un registro temporal que será eliminado cuando el usuario confirme "recibido".
        Solo puede ser ejecutado por administradores (rol_id = 1).
        
        Args:
            db: Sesión de base de datos
            admin_id: ID del administrador que crea el comentario
            correo_usuario: Correo del usuario al que se le asignará el comentario
            comentario_invalido: Texto del comentario inválido
            
        Returns:
            Dict con información del resultado de la operación
        """
        try:
            # 1. Verificar que el admin_id sea un administrador (rol_id = 1)
            from src.Users.infrastructure.users_model import Users
            from src.rol.infrastructure.rol_model import Rol
            
            admin = db.query(Users).filter(Users.ID_user == admin_id).first()
            if not admin:
                raise ValueError("El usuario administrador no existe")
            
            if admin.rol_id_FK != 1:
                raise ValueError("Solo los administradores pueden crear comentarios inválidos")
            
            # 2. Verificar que el correo del usuario exista
            usuario = db.query(Users).filter(Users.correo == correo_usuario).first()
            if not usuario:
                raise ValueError(f"No se encontró un usuario con el correo: {correo_usuario}")
            
            # 3. Buscar todos los análisis pendientes del usuario
            analisis_pendientes = db.query(AnalisisSuelosPendientes).filter(
                AnalisisSuelosPendientes.user_id_FK == usuario.ID_user,
                AnalisisSuelosPendientes.estatus == 'pendiente'
            ).all()
            
            registros_actualizados = 0
            registro_temporal_creado = False
            
            # 4. Si tiene análisis pendientes, actualizar todos
            if analisis_pendientes:
                for analisis in analisis_pendientes:
                    analisis.comentario_invalido = comentario_invalido
                    registros_actualizados += 1
                    
                print(f"Actualizando {len(analisis_pendientes)} registros existentes con comentario")
            
            # 5. Si NO tiene análisis pendientes, crear un registro temporal
            else:
                print(f"Usuario {correo_usuario} no tiene análisis pendientes. Creando registro temporal...")
                
                # Crear registro temporal para almacenar el comentario
                registro_temporal = AnalisisSuelosPendientes(
                    user_id_FK=usuario.ID_user,
                    municipio_id_FK=None,
                    numero=0,  # Número especial para identificar como temporal
                    estatus='comentario_temporal',  # Estatus especial
                    comentario_invalido=comentario_invalido,
                    estado_cuadernillo='TEMPORAL',
                    municipio_cuadernillo='REGISTRO_TEMPORAL_COMENTARIO',
                    nombre_revisor=f"Admin_{admin_id}",
                    # Campos mínimos requeridos como None o valores por defecto
                    clave_estatal=None,
                    clave_municipio=None,
                    clave_munip=None,
                    clave_localidad=None,
                    localidad_cuadernillo=None,
                    recuento_curp_renapo=None,
                    extraccion_edo=None,
                    clave=None,
                    ddr=None,
                    cader=None,
                    coordenada_x=None,
                    coordenada_y=None,
                    elevacion_msnm=None,
                    profundidad_muestreo=None,
                    fecha_muestreo=None,
                    parcela=None,
                    cultivo_anterior=None,
                    cultivo_establecer=None,
                    manejo=None,
                    tipo_vegetacion=None,
                    nombre_tecnico=None,
                    tel_tecnico=None,
                    correo_tecnico=None,
                    nombre_productor=None,
                    tel_productor=None,
                    correo_productor=None,
                    muestra=None,
                    reemplazo=None
                )
                
                db.add(registro_temporal)
                registros_actualizados = 1
                registro_temporal_creado = True
            
            # 6. Commit de los cambios
            db.commit()
            
            # 7. Obtener ID del registro para respuesta
            if registro_temporal_creado:
                # Buscar el registro temporal recién creado
                registro_ref = db.query(AnalisisSuelosPendientes).filter(
                    AnalisisSuelosPendientes.user_id_FK == usuario.ID_user,
                    AnalisisSuelosPendientes.estatus == 'comentario_temporal'
                ).first()
                registro_id = registro_ref.id if registro_ref else 0
            else:
                registro_id = analisis_pendientes[0].id if analisis_pendientes else 0
            
            mensaje_tipo = "registro temporal creado" if registro_temporal_creado else "registros existentes actualizados"
            
            print(f"Comentario inválido almacenado exitosamente")
            print(f"   Admin ID: {admin_id}")
            print(f"   Usuario: {correo_usuario}")
            print(f"   Tipo: {mensaje_tipo}")
            print(f"   Registros afectados: {registros_actualizados}")
            
            return {
                "message": f"Comentario inválido registrado exitosamente para {correo_usuario} ({mensaje_tipo})",
                "comentario_id": registro_id,
                "correo_usuario": correo_usuario,
                "comentario_invalido": comentario_invalido,
                "registros_afectados": registros_actualizados,
                "fecha_comentario": datetime.now()
            }
            
        except ValueError as ve:
            db.rollback()
            raise ve
        except Exception as e:
            db.rollback()
            error_msg = f"Error creando comentario inválido: {str(e)}"
            print(f"Error: {error_msg}")
            raise Exception(error_msg)
    
    @staticmethod
    def verificar_y_procesar_comentarios(
        db: Session, 
        correo_usuario: str, 
        accion: str
    ) -> Dict[str, Any]:
        """
        Verifica si un usuario tiene comentarios inválidos y permite marcarlos como recibidos.
        
        Acciones disponibles:
        * 'verificar': Solo verifica si hay comentarios inválidos
        * 'recibido': Marca los comentarios como recibidos y los elimina
        
        Args:
            correo_usuario: Correo del usuario a verificar
            accion: Acción a realizar ('verificar' o 'recibido')
            db: Sesión de base de datos
            
        Returns:
            Dict con información sobre los comentarios encontrados y acciones realizadas
        """
        try:
            # 1. Verificar que el usuario exista
            from src.Users.infrastructure.users_model import Users
            
            usuario = db.query(Users).filter(Users.correo == correo_usuario).first()
            if not usuario:
                raise ValueError(f"No se encontró un usuario con el correo: {correo_usuario}")
            
            # 2. Buscar análisis con comentarios inválidos (incluyendo registros temporales)
            analisis_con_comentarios = db.query(AnalisisSuelosPendientes).filter(
                AnalisisSuelosPendientes.user_id_FK == usuario.ID_user,
                AnalisisSuelosPendientes.comentario_invalido.isnot(None),
                AnalisisSuelosPendientes.comentario_invalido != ''
            ).all()
            
            # 3. Extraer comentarios únicos
            comentarios_unicos = []
            if analisis_con_comentarios:
                comentarios_set = set()
                for analisis in analisis_con_comentarios:
                    if analisis.comentario_invalido:
                        comentarios_set.add(analisis.comentario_invalido)
                comentarios_unicos = list(comentarios_set)
            
            tiene_comentarios = len(analisis_con_comentarios) > 0
            
            # 4. Procesar según la acción solicitada
            if accion == "verificar":
                return {
                    "correo_usuario": correo_usuario,
                    "tiene_comentarios": tiene_comentarios,
                    "total_comentarios": len(analisis_con_comentarios),
                    "comentarios": comentarios_unicos,
                    "message": f"Verificación completada. {len(analisis_con_comentarios)} registros con comentarios encontrados."
                }
                
            elif accion == "recibido":
                if not tiene_comentarios:
                    return {
                        "correo_usuario": correo_usuario,
                        "tiene_comentarios": False,
                        "total_comentarios": 0,
                        "comentarios": [],
                        "message": f"El usuario {correo_usuario} no tiene comentarios inválidos pendientes.",
                        "registros_eliminados": 0
                    }
                
                # 5. Eliminar todos los registros con comentarios inválidos
                registros_eliminados = 0
                for analisis in analisis_con_comentarios:
                    db.delete(analisis)
                    registros_eliminados += 1
                
                # 6. Commit de los cambios
                db.commit()
                
                print(f"🗑️  Comentarios procesados como recibidos:")
                print(f"   Usuario: {correo_usuario}")
                print(f"   Registros eliminados: {registros_eliminados}")
                
                return {
                    "correo_usuario": correo_usuario,
                    "tiene_comentarios": False,  # Ya no tiene comentarios después de eliminarlos
                    "total_comentarios": 0,
                    "comentarios": [],
                    "message": f"Comentarios marcados como recibidos. {registros_eliminados} registros eliminados exitosamente.",
                    "registros_eliminados": registros_eliminados
                }
            
            else:
                raise ValueError(f"Acción no válida: {accion}. Use 'verificar' o 'recibido'")
                
        except ValueError as ve:
            db.rollback()
            raise ve
        except Exception as e:
            db.rollback()
            error_msg = f"Error procesando comentarios para {correo_usuario}: {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)