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
    
    @staticmethod
    def cache_municipios(db: Session) -> Dict[str, int]:
        """
        🚀 OPTIMIZACIÓN: Cache todos los municipios en memoria para búsqueda rápida
        """
        print("🚀 Cargando cache de municipios...")
        municipios_cache = {}
        
        # Obtener todos los municipios de una vez
        municipios = db.query(Municipios).all()
        
        for municipio in municipios:
            nombre = municipio.nombre
            if nombre:
                # Múltiples variaciones para búsqueda rápida
                municipios_cache[nombre] = municipio.id_municipio
                municipios_cache[nombre.upper()] = municipio.id_municipio
                municipios_cache[nombre.lower()] = municipio.id_municipio
                municipios_cache[nombre.strip()] = municipio.id_municipio
                
                # Versión sin acentos (básica)
                nombre_sin_acentos = (nombre.replace('á', 'a').replace('é', 'e')
                                    .replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
                                    .replace('ñ', 'n').replace('Á', 'A').replace('É', 'E')
                                    .replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')
                                    .replace('Ñ', 'N'))
                municipios_cache[nombre_sin_acentos.upper()] = municipio.id_municipio
        
        print(f"✓ Cache cargado: {len(municipios)} municipios únicos, {len(municipios_cache)} variaciones")
        return municipios_cache
    
    @staticmethod
    def find_municipio_id_fast(municipio_nombre: str, municipios_cache: Dict[str, int]) -> int:
        """
        🚀 OPTIMIZACIÓN: Búsqueda ultra rápida usando cache en memoria
        """
        if not municipio_nombre or pd.isna(municipio_nombre):
            return None
            
        municipio_clean = str(municipio_nombre).strip()
        
        if not municipio_clean or municipio_clean.lower() == 'nan':
            return None
        
        # Búsquedas progresivas en cache (sin queries SQL)
        search_variants = [
            municipio_clean,                    # Exacto
            municipio_clean.upper(),           # Mayúsculas
            municipio_clean.lower(),           # Minúsculas
            municipio_clean.strip(),           # Sin espacios
        ]
        
        # Búsqueda directa en cache
        for variant in search_variants:
            if variant in municipios_cache:
                return municipios_cache[variant]
        
        # Búsqueda parcial en cache (más lenta pero aún en memoria)
        municipio_upper = municipio_clean.upper()
        for cached_name, municipio_id in municipios_cache.items():
            if municipio_upper in cached_name.upper() or cached_name.upper() in municipio_upper:
                return municipio_id
        
        return None
    
    @staticmethod
    def process_date_fast(value) -> datetime.date:
        """
        🚀 OPTIMIZACIÓN: Procesamiento rápido de fechas
        """
        if pd.isna(value) or value == '' or str(value).strip() == '':
            return None
        
        try:
            # Si ya es datetime
            if hasattr(value, 'date'):
                return value.date()
            
            # Si es string
            if isinstance(value, str):
                value_clean = value.strip().replace('/', '/').replace('-', '/')
                
                # Caso especial "07/052024"
                if '/' in value_clean:
                    parts = value_clean.split('/')
                    if len(parts) == 2 and len(parts[1]) >= 6:
                        day = parts[0]
                        month_year = parts[1]
                        if len(month_year) == 6:
                            month = month_year[:2]
                            year = month_year[2:]
                            value_clean = f"{day}/{month}/{year}"
                
                # Intentar formatos más comunes primero (optimización)
                date_formats = ['%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%d-%m-%Y', '%d-%m-%y']
                
                for fmt in date_formats:
                    try:
                        return datetime.strptime(value_clean, fmt).date()
                    except ValueError:
                        continue
            
            return None
        except:
            return None
    
    @staticmethod
    def process_int_fast(value) -> int:
        """
        🚀 OPTIMIZACIÓN: Conversión rápida a entero
        """
        if pd.isna(value) or value == '' or str(value).strip() == '':
            return None
        
        try:
            # Limpiar y convertir
            clean_value = str(value).replace(',', '').replace(' ', '').strip()
            return int(float(clean_value)) if clean_value else None
        except:
            return None
    
    @staticmethod
    def process_text_fast(value) -> str:
        """
        🚀 OPTIMIZACIÓN: Procesamiento rápido de texto
        """
        if pd.isna(value) or value == '':
            return None
        
        clean_text = str(value).strip()
        return clean_text if clean_text and clean_text.lower() != 'nan' else None
    
    @staticmethod
    def bulk_insert_optimized(records: List[Dict], db: Session) -> Tuple[int, int, List[str]]:
        """
        🚀 OPTIMIZACIÓN: Inserción masiva ultra rápida usando SQL crudo
        """
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
            
            # Insertar en lotes para mejor rendimiento
            BATCH_SIZE = 500  # Ajustable según tu BD
            total_batches = (len(records) + BATCH_SIZE - 1) // BATCH_SIZE
            
            print(f"🚀 Insertando {len(records)} registros en {total_batches} lotes de {BATCH_SIZE}...")
            
            for i in range(0, len(records), BATCH_SIZE):
                batch = records[i:i + BATCH_SIZE]
                batch_num = (i // BATCH_SIZE) + 1
                
                try:
                    # Ejecutar lote
                    db.execute(insert_sql, batch)
                    success_count += len(batch)
                    print(f"  ✓ Lote {batch_num}/{total_batches}: {len(batch)} registros insertados")
                    
                except Exception as e:
                    error_count += len(batch)
                    error_msg = f"Error en lote {batch_num}: {str(e)}"
                    errors.append(error_msg)
                    print(f"  ✗ {error_msg}")
                    continue
            
            # Confirmar transacción
            if success_count > 0:
                db.commit()
                print(f"✓ Transacción confirmada: {success_count} registros insertados exitosamente")
            
        except Exception as e:
            db.rollback()
            error_msg = f"Error en inserción masiva: {str(e)}"
            errors.append(error_msg)
            print(f"✗ {error_msg}")
        
        return success_count, error_count, errors
    
    @staticmethod
    def process_excel_file(file_content: bytes, user_id: int, db: Session) -> Dict[str, Any]:
        """
        🚀 VERSIÓN OPTIMIZADA: Procesamiento ultra rápido de Excel
        """
        try:
            print("🚀 INICIANDO PROCESAMIENTO OPTIMIZADO...")
            start_time = datetime.now()
            
            # 1. CARGAR CACHE DE MUNICIPIOS (una sola consulta)
            municipios_cache = AnalisisSuelosService.cache_municipios(db)
            
            # 2. LEER EXCEL MÁS EFICIENTE
            print("📊 Leyendo archivo Excel...")
            df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl', header=1)
            
            print(f"📊 Archivo cargado: {len(df)} filas")
            
            # Limpiar nombres de columnas una sola vez
            df.columns = [str(col).strip() for col in df.columns]
            
            # 3. MAPEO OPTIMIZADO POR POSICIÓN
            position_mapping = {
                0: 'numero', 1: 'clave_estatal', 2: 'estado_cuadernillo', 3: 'clave_municipio',
                4: 'clave_munip', 5: 'municipio_cuadernillo', 6: 'clave_localidad', 7: 'localidad_cuadernillo',
                8: 'recuento_curp_renapo', 9: 'extraccion_edo', 10: 'clave', 11: 'ddr', 12: 'cader',
                13: 'coordenada_x', 14: 'coordenada_y', 15: 'elevacion_msnm', 16: 'profundidad_muestreo',
                17: 'fecha_muestreo', 18: 'parcela', 19: 'cultivo_anterior', 20: 'cultivo_establecer',
                21: 'manejo', 22: 'tipo_vegetacion', 23: 'nombre_tecnico', 24: 'tel_tecnico', 25: 'correo_tecnico',
                26: 'nombre_productor', 27: 'tel_productor', 28: 'correo_productor', 29: 'muestra',
                30: 'reemplazo', 31: 'nombre_revisor'
            }
            
            # 4. PROCESAMIENTO EN LOTES (SIN PRINTS POR FILA)
            print("⚡ Procesando datos en lotes...")
            
            # Campos que necesitan conversión especial
            int_fields = {'numero', 'clave_estatal', 'clave_municipio', 'elevacion_msnm', 'recuento_curp_renapo'}
            date_fields = {'fecha_muestreo'}
            
            records_to_insert = []
            municipios_not_found = set()
            
            # Procesar por lotes para eficiencia de memoria
            PROCESS_BATCH_SIZE = 1000
            total_processed = 0
            
            for batch_start in range(0, len(df), PROCESS_BATCH_SIZE):
                batch_end = min(batch_start + PROCESS_BATCH_SIZE, len(df))
                batch_df = df.iloc[batch_start:batch_end]
                
                print(f"  Procesando lote {batch_start + 1}-{batch_end} de {len(df)}...")
                
                for index, row in batch_df.iterrows():
                    try:
                        data = {}
                        
                        # Mapear valores por posición (más rápido que por nombre)
                        for pos, db_field in position_mapping.items():
                            if pos < len(df.columns):
                                value = row.iloc[pos] if pos < len(row) else None
                                
                                # Aplicar conversión según tipo de campo
                                if db_field in int_fields:
                                    data[db_field] = AnalisisSuelosService.process_int_fast(value)
                                elif db_field in date_fields:
                                    data[db_field] = AnalisisSuelosService.process_date_fast(value)
                                else:
                                    data[db_field] = AnalisisSuelosService.process_text_fast(value)
                            else:
                                data[db_field] = None
                        
                        # VALIDACIÓN RÁPIDA DE MUNICIPIO
                        municipio_nombre = data.get('municipio_cuadernillo')
                        if municipio_nombre:
                            municipio_id = AnalisisSuelosService.find_municipio_id_fast(municipio_nombre, municipios_cache)
                            data['municipio_id_FK'] = municipio_id
                            if not municipio_id:
                                municipios_not_found.add(municipio_nombre)
                        else:
                            data['municipio_id_FK'] = None
                        
                        # Campos obligatorios
                        data['user_id_FK'] = user_id
                        data['estatus'] = 'pendiente'
                        
                        # Validar número
                        if data.get('numero') is None:
                            data['numero'] = index + 1
                        
                        records_to_insert.append(data)
                        total_processed += 1
                        
                    except Exception as e:
                        print(f"  ⚠️ Error procesando fila {index + 1}: {str(e)}")
                        continue
                
                print(f"  ✓ Lote procesado: {len(batch_df)} filas")
            
            # 5. INSERCIÓN MASIVA OPTIMIZADA
            print(f"🚀 Insertando {len(records_to_insert)} registros...")
            success_count, error_count, errors = AnalisisSuelosService.bulk_insert_optimized(records_to_insert, db)
            
            # 6. ESTADÍSTICAS FINALES
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            print(f"🎉 PROCESAMIENTO COMPLETADO en {processing_time:.2f} segundos")
            print(f"📊 Estadísticas: {success_count} exitosos, {error_count} errores")
            if municipios_not_found:
                print(f"⚠️  Municipios no encontrados: {len(municipios_not_found)}")
            
            # Crear mensaje de resumen
            message_parts = []
            message_parts.append(f"Archivo procesado en {processing_time:.2f}s. {success_count} registros insertados.")
            
            if municipios_not_found:
                message_parts.append(f"⚠️ {len(municipios_not_found)} municipios no encontrados.")
            
            final_message = " ".join(message_parts) if success_count > 0 else "No se pudo procesar ningún registro"
            
            return {
                "message": final_message,
                "records_processed": len(df),
                "success_count": success_count,
                "error_count": error_count,
                "processing_time_seconds": round(processing_time, 2),
                "errors": errors[:5],  # Solo mostrar primeros 5 errores
                "municipios_not_found": list(municipios_not_found)[:10] if municipios_not_found else []
            }
            
        except Exception as e:
            db.rollback()
            print(f"💥 Error general procesando archivo: {str(e)}")
            raise Exception(f"Error al procesar el archivo Excel: {str(e)}")
    
    @staticmethod
    def get_all_analisis_suelos(db: Session, skip: int = 0, limit: int = 100) -> List[AnalisisSuelosPendientes]:
        """
        Obtiene todos los análisis de suelos pendientes
        """
        return db.query(AnalisisSuelosPendientes).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_analisis_suelos_by_id(db: Session, analisis_id: int) -> AnalisisSuelosPendientes:
        """
        Obtiene un análisis de suelos por ID
        """
        return db.query(AnalisisSuelosPendientes).filter(AnalisisSuelosPendientes.id == analisis_id).first()
    
    @staticmethod
    def create_analisis_suelos(db: Session, analisis_data: AnalisisSuelosCreate) -> AnalisisSuelosPendientes:
        """
        Crea un nuevo análisis de suelos
        """
        db_analisis = AnalisisSuelosPendientes(**analisis_data.dict())
        db.add(db_analisis)
        db.commit()
        db.refresh(db_analisis)
        return db_analisis
    
    @staticmethod
    def delete_analisis_suelos(db: Session, analisis_id: int) -> bool:
        """
        Elimina un análisis de suelos por ID
        """
        analisis = db.query(AnalisisSuelosPendientes).filter(AnalisisSuelosPendientes.id == analisis_id).first()
        if analisis:
            db.delete(analisis)
            db.commit()
            return True
        return False