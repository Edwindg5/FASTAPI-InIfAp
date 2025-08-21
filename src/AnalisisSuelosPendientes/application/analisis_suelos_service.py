# src/AnalisisSuelosPendientes/application/analisis_suelos_service.py
import pandas as pd
import io
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.AnalisisSuelosPendientes.infrastructure.analisis_suelos_model import AnalisisSuelosPendientes
from src.AnalisisSuelosPendientes.application.analisis_suelos_schemas import AnalisisSuelosCreate, AnalisisSuelosResponse

class AnalisisSuelosService:
    
    @staticmethod
    def process_excel_file(file_content: bytes, user_id: int, db: Session) -> Dict[str, Any]:
        """
        Procesa el archivo Excel y extrae datos para insertar en la base de datos
        """
        try:
            # Leer el archivo Excel - IMPORTANTE: Saltar la primera fila si tiene encabezados agrupados
            df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl', header=1)
            
            # Imprimir las columnas para debugging
            print("Columnas encontradas en el Excel:")
            print(df.columns.tolist())
            print(f"\nTotal de filas: {len(df)}")
            print("\nPrimeras 3 filas del DataFrame:")
            print(df.head(3))
            print("\nTipos de datos:")
            print(df.dtypes)
            
            # Limpiar nombres de columnas (eliminar espacios extra y caracteres especiales)
            df.columns = [str(col).strip() for col in df.columns]
            
            # Imprimir cada fila para ver el contenido real
            print("\n=== DATOS REALES DE LAS PRIMERAS 3 FILAS ===")
            for i in range(min(3, len(df))):
                print(f"\nFila {i+1}:")
                for j, col in enumerate(df.columns):
                    print(f"  Columna {j} ({col}): '{df.iloc[i, j]}' (tipo: {type(df.iloc[i, j])})")
            
            # Mapeo por POSICIÓN de columnas basado en el Excel real
            # Según tu imagen, el orden exacto es:
            position_mapping = {
                0: 'numero',                    # N°
                1: 'clave_estatal',            # Clave estatal  
                2: 'estado_cuadernillo',       # estado_cuadernillo
                3: 'clave_municipio',          # Clave municipio
                4: 'clave_munip',              # clave munip
                5: 'municipio_cuadernillo',    # municipio_cuadernillo
                6: 'clave_localidad',          # Clave localidad
                7: 'localidad_cuadernillo',    # localidad_cuadernillo
                8: 'recuento_curp_renapo',     # Recuento de CURP_Renapo
                9: 'extraccion_edo',           # extraccion edo
                10: 'clave',                   # CLAVE
                11: 'ddr',                     # DDR
                12: 'cader',                   # CADER
                13: 'coordenada_x',            # X
                14: 'coordenada_y',            # Y
                15: 'elevacion_msnm',          # Elevacion msnm
                16: 'profundidad_muestreo',    # Profundidad de muestreo
                17: 'fecha_muestreo',          # Fecha de muestreo
                18: 'parcela',                 # Parcela
                19: 'cultivo_anterior',        # Cultivo anterior
                20: 'cultivo_establecer',      # Cultivo a establecer
                21: 'manejo',                  # Manejo
                22: 'tipo_vegetacion',         # Tipo vegetación
                23: 'nombre_tecnico',          # Nombre (técnico)
                24: 'tel_tecnico',             # Tel (técnico)
                25: 'correo_tecnico',          # Correo (técnico)
                26: 'nombre_productor',        # Nombre (productor)
                27: 'tel_productor',           # Tel (productor)
                28: 'correo_productor',        # Correo (productor)
                29: 'muestra',                 # Muestra
                30: 'reemplazo',               # Reemplazo
                31: 'nombre_revisor'           # NOMBRE REVISOR
            }
            
            success_count = 0
            error_count = 0
            errors = []
            
            print(f"\nProcesando {len(df)} filas...")
            
            for index, row in df.iterrows():
                try:
                    # Crear diccionario con los datos mapeados por posición
                    data = {}
                    
                    print(f"\n--- Procesando fila {index + 1} ---")
                    
                    # Mapear por posición de columna
                    for pos, db_field in position_mapping.items():
                        if pos < len(df.columns):
                            # Obtener valor por posición
                            value = row.iloc[pos] if pos < len(row) else None
                            col_name = df.columns[pos] if pos < len(df.columns) else f"Col_{pos}"
                            
                            print(f"  Pos {pos} ({col_name}) -> {db_field}: '{value}' (tipo: {type(value)})")
                            
                            # Manejar valores nulos/NaN
                            if pd.isna(value) or value == '' or str(value).strip() == '' or str(value).lower() == 'nan':
                                data[db_field] = None
                            else:
                                # Conversiones específicas por tipo de campo
                                if db_field in ['numero', 'clave_estatal', 'clave_municipio', 'elevacion_msnm']:
                                    try:
                                        # Limpiar el valor si contiene comas como separadores de miles
                                        clean_value = str(value).replace(',', '').replace(' ', '').strip()
                                        if clean_value:
                                            data[db_field] = int(float(clean_value))
                                        else:
                                            data[db_field] = None
                                    except (ValueError, TypeError):
                                        print(f"    Error convirtiendo a entero: {value}")
                                        data[db_field] = None
                                elif db_field == 'recuento_curp_renapo':
                                    try:
                                        # Manejar formato con comas y espacios como " 1,264 "
                                        clean_value = str(value).replace(',', '').replace(' ', '').strip()
                                        if clean_value:
                                            data[db_field] = int(float(clean_value))
                                        else:
                                            data[db_field] = None
                                    except (ValueError, TypeError):
                                        print(f"    Error convirtiendo CURP a entero: {value}")
                                        data[db_field] = None
                                elif db_field == 'fecha_muestreo':
                                    try:
                                        if isinstance(value, str):
                                            # Manejar diferentes formatos de fecha
                                            value_clean = str(value).strip().replace('/', '/').replace('-', '/')
                                            
                                            # Caso especial para formato como "07/052024"
                                            if '/' in value_clean:
                                                parts = value_clean.split('/')
                                                if len(parts) == 2 and len(parts[1]) >= 6:
                                                    # Formato como "07/052024"
                                                    day = parts[0]
                                                    month_year = parts[1]
                                                    if len(month_year) == 6:  # 052024
                                                        month = month_year[:2]
                                                        year = month_year[2:]
                                                        value_clean = f"{day}/{month}/{year}"
                                            
                                            # Intentar varios formatos de fecha
                                            date_formats = [
                                                '%d/%m/%Y',   # 13/05/2024
                                                '%d/%m/%y',   # 13/05/24  
                                                '%d-%m-%Y',   # 13-05-2024
                                                '%d-%m-%y',   # 13-05-24
                                                '%Y-%m-%d',   # 2024-05-13
                                            ]
                                            
                                            for fmt in date_formats:
                                                try:
                                                    data[db_field] = datetime.strptime(value_clean, fmt).date()
                                                    print(f"    Fecha convertida: {data[db_field]} (formato: {fmt})")
                                                    break
                                                except ValueError:
                                                    continue
                                            else:
                                                print(f"    No se pudo convertir la fecha: {value}")
                                                data[db_field] = None
                                        elif hasattr(value, 'date'):
                                            data[db_field] = value.date()
                                        elif hasattr(value, 'strftime'):
                                            data[db_field] = value.date() if hasattr(value, 'date') else value
                                        else:
                                            print(f"    Tipo de fecha no reconocido: {type(value)} - {value}")
                                            data[db_field] = None
                                    except Exception as e:
                                        print(f"    Error procesando fecha: {e}")
                                        data[db_field] = None
                                else:
                                    # Para campos de texto, convertir a string y limpiar
                                    clean_text = str(value).strip() if value else None
                                    data[db_field] = clean_text if clean_text and clean_text.lower() != 'nan' else None
                        else:
                            print(f"  Posición {pos} fuera de rango")
                            data[db_field] = None
                    
                    # Agregar user_id y estatus por defecto
                    data['user_id_FK'] = user_id
                    data['estatus'] = 'pendiente'
                    
                    # Validar que tenemos el número (campo crítico)
                    if data.get('numero') is None:
                        print(f"  ⚠️  ADVERTENCIA: Número es None para fila {index + 1}")
                        # Usar el índice + 1 como número si no existe
                        data['numero'] = index + 1
                    
                    print(f"  Datos finales para insertar:")
                    for key, value in data.items():
                        if value is not None:
                            print(f"    {key}: {value}")
                        else:
                            print(f"    {key}: NULL")
                    
                    # Lista de campos requeridos para el INSERT
                    required_fields = [
                        'numero', 'clave_estatal', 'estado_cuadernillo', 'clave_municipio',
                        'clave_munip', 'municipio_cuadernillo', 'clave_localidad', 'localidad_cuadernillo',
                        'recuento_curp_renapo', 'extraccion_edo', 'clave', 'ddr', 'cader',
                        'coordenada_x', 'coordenada_y', 'elevacion_msnm', 'profundidad_muestreo',
                        'fecha_muestreo', 'parcela', 'cultivo_anterior', 'cultivo_establecer',
                        'manejo', 'tipo_vegetacion', 'nombre_tecnico', 'tel_tecnico', 'correo_tecnico',
                        'nombre_productor', 'tel_productor', 'correo_productor', 'muestra',
                        'reemplazo', 'nombre_revisor', 'estatus', 'user_id_FK'
                    ]
                    
                    # Asegurarse de que todos los campos están en el diccionario
                    for field in required_fields:
                        if field not in data:
                            data[field] = None
                    
                    # USAR SQL RAW para insertar
                    insert_sql = text("""
                        INSERT INTO analisis_suelos_pendientes (
                            numero, clave_estatal, estado_cuadernillo, clave_municipio,
                            clave_munip, municipio_cuadernillo, clave_localidad, localidad_cuadernillo,
                            recuento_curp_renapo, extraccion_edo, clave, ddr, cader,
                            coordenada_x, coordenada_y, elevacion_msnm, profundidad_muestreo,
                            fecha_muestreo, parcela, cultivo_anterior, cultivo_establecer,
                            manejo, tipo_vegetacion, nombre_tecnico, tel_tecnico, correo_tecnico,
                            nombre_productor, tel_productor, correo_productor, muestra,
                            reemplazo, nombre_revisor, estatus, user_id_FK
                        ) VALUES (
                            :numero, :clave_estatal, :estado_cuadernillo, :clave_municipio,
                            :clave_munip, :municipio_cuadernillo, :clave_localidad, :localidad_cuadernillo,
                            :recuento_curp_renapo, :extraccion_edo, :clave, :ddr, :cader,
                            :coordenada_x, :coordenada_y, :elevacion_msnm, :profundidad_muestreo,
                            :fecha_muestreo, :parcela, :cultivo_anterior, :cultivo_establecer,
                            :manejo, :tipo_vegetacion, :nombre_tecnico, :tel_tecnico, :correo_tecnico,
                            :nombre_productor, :tel_productor, :correo_productor, :muestra,
                            :reemplazo, :nombre_revisor, :estatus, :user_id_FK
                        )
                    """)
                    
                    db.execute(insert_sql, data)
                    
                    print(f"  ✓ Fila {index + 1} procesada exitosamente")
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    error_msg = f"Fila {index + 2}: {str(e)}"
                    print(f"  ✗ Error en fila {index + 1}: {str(e)}")
                    errors.append(error_msg)
                    continue
            
            # Confirmar todas las transacciones exitosas
            if success_count > 0:
                db.commit()
                print(f"\n✓ Transacción confirmada: {success_count} registros insertados")
            else:
                db.rollback()
                print("\n✗ No se insertaron registros, rollback realizado")
            
            return {
                "message": f"Archivo procesado exitosamente. {success_count} registros insertados." if success_count > 0 else "No se pudo procesar ningún registro",
                "records_processed": len(df),
                "success_count": success_count,
                "error_count": error_count,
                "errors": errors[:10]
            }
            
        except Exception as e:
            db.rollback()
            print(f"Error general procesando archivo: {str(e)}")
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