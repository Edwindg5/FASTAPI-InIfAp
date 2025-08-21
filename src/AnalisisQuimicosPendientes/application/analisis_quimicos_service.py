# src/AnalisisQuimicosPendientes/application/analisis_quimicos_service.py
import io
import math
import re
import unicodedata
from typing import Dict, List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from src.AnalisisQuimicosPendientes.infrastructure.analisis_quimicos_model import (
    AnalisisQuimicosPendientes,
)

# ===================== Helpers de normalización y limpieza ===================== #

def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def _norm_text(s: Optional[str]) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = _strip_accents(s.lower())
    s = re.sub(r"[\s\-/]+", "_", s)
    s = re.sub(r"[^a-z0-9_]+", "", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")

def _is_empty_cell(v) -> bool:
    if v is None:
        return True
    if pd.isna(v):
        return True
    s = str(v).strip()
    if s == "":
        return True
    # Solo considerar vacío si es explícitamente un marcador de dato faltante
    s_lower = s.lower()
    return s_lower in {"na", "nd", "n/a", "n/d", "nan", "none", "null", "nil", "#n/a", "#null!"}

def _to_decimal(v) -> Optional[float]:
    """
    Convierte valores "raros" a float de forma robusta.
    Maneja: "1,234.56", "1.234,56", "74..04", "< 0.01", "10 %", etc.
    """
    if v is None:
        return None
    if pd.isna(v):
        return None
    
    # Si ya es numérico, validar y retornar
    if isinstance(v, (int, float)):
        if math.isnan(float(v)) or math.isinf(float(v)):
            return None
        return float(v)

    s = str(v).strip()
    if s == "":
        return None

    # Marcadores comunes de vacío - ser más específico
    s_lower = s.lower()
    if s_lower in {"na", "nd", "n/a", "n/d", "nan", "null", "nil", "#n/a", "#null!", "none"}:
        return None

    # Guardar el signo
    is_negative = s.startswith('-')
    if is_negative:
        s = s[1:]

    # Quitar símbolos comunes pero preservar números
    s = s.replace("%", "")
    s = re.sub(r"^\s*[<>≈~±]\s*", "", s)  # Quitar comparadores al inicio
    s = s.replace(" ", "")
    s = s.replace("\t", "")

    # Arreglar múltiples puntos consecutivos (error de digitación)
    s = re.sub(r"\.{2,}", ".", s)
    
    # Manejar separadores decimales mixtos
    if "." in s and "," in s:
        # Determinar cuál es el separador decimal por posición
        last_dot_pos = s.rfind(".")
        last_comma_pos = s.rfind(",")
        
        if last_comma_pos > last_dot_pos:
            # La coma es el separador decimal
            s = s[:last_comma_pos].replace(".", "").replace(",", "") + "." + s[last_comma_pos+1:]
        else:
            # El punto es el separador decimal
            s = s[:last_dot_pos].replace(",", "").replace(".", "") + "." + s[last_dot_pos+1:]
    elif "," in s and s.count(",") == 1:
        # Solo una coma - probablemente separador decimal
        comma_pos = s.find(",")
        # Si hay máximo 3 dígitos después de la coma, es decimal
        if len(s) - comma_pos <= 4:
            s = s.replace(",", ".")
        else:
            # Es separador de miles
            s = s.replace(",", "")
    elif "," in s:
        # Múltiples comas - separadores de miles
        s = s.replace(",", "")

    # Limpiar caracteres no numéricos adicionales pero preservar punto decimal
    s = re.sub(r"[^\d.-]", "", s)
    
    # Validar formato final
    if not re.match(r"^\d*\.?\d*$", s):
        # Intentar extraer el primer número válido
        match = re.search(r"\d+(?:\.\d+)?", s)
        if match:
            s = match.group()
        else:
            return None

    # Convertir a float
    try:
        result = float(s)
        if is_negative:
            result = -result
        # Validar que el resultado sea un número válido
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except (ValueError, OverflowError):
        return None


# ----------- Mapeo de nombres esperados a posibles sinónimos/variantes ---------- #

EXPECTED_MAP: Dict[str, List[str]] = {
    "municipio": ["municipio"],
    "localidad": ["localidad", "comunidad", "localidad_comunidad"],
    "nombre_productor": ["nombre_del_productor", "nombre_productor", "productor", "productor_nombre", "nombre"],
    "cultivo_anterior": ["cultivo_anterior", "cultivo_previo", "cultivo", "anterior"],
    "arcilla": ["arcilla", "porc_arcilla", "arcilla_", "clay"],
    "limo": ["limo", "porc_limo", "limo_", "silt"],
    "arena": ["arena", "porc_arena", "arena_", "sand"],
    "textura": ["textura", "clase_textural", "texture"],
    "da": ["da", "densidad_aparente", "dens_aparente", "densidadaparente", "bulk_density"],
    "ph": ["ph", "p_h"],
    "mo": ["mo", "materia_organica", "materiaorganica", "organic_matter"],
    "fosforo": ["fosforo", "p", "p_olsen", "p_bray", "p_disp", "phosphorus"],
    "n_inorganico": ["n_inorganico", "nmineral", "n_mineral", "n_inorganico_", "nitrogen"],
    "k": ["k", "potasio", "k_intercambiable", "potassium"],
    "mg": ["mg", "magnesio", "magnesium"],
    "ca": ["ca", "calcio", "calcium"],
    "na": ["na", "sodio", "sodium"],
    "al": ["al", "aluminio", "aluminum"],
    "cic": ["cic", "cice", "capacidad_intercambio_cationico", "cation_exchange"],
    "cic_calculada": ["cic_calculada", "cic_calc", "cic_teorica", "calculated"],
    "h": ["h", "hidrogeno", "hydrogen"],
    "azufre": ["azufre", "s", "sulfatos", "s_disp", "sulfur"],
    "hierro": ["hierro", "fe", "iron"],
    "cobre": ["cobre", "cu", "copper"],
    "zinc": ["zinc", "zn"],
    "manganeso": ["manganeso", "mn", "manganese"],
    "boro": ["boro", "b", "boron"],
    "columna1": ["columna1", "extra1", "obs1", "observacion1"],
    "columna2": ["columna2", "extra2", "obs2", "observacion2"],
    "ca_mg": ["ca_mg", "rel_ca_mg", "ca_mg_razon", "camg"],
    "mg_k": ["mg_k", "rel_mg_k", "mg_k_razon", "mgk"],
    "ca_k": ["ca_k", "rel_ca_k", "ca_k_razon", "cak"],
    "ca_mg_k": ["ca_mg_k", "rel_ca_mg_k", "camgk"],
    "k_mg": ["k_mg", "rel_k_mg", "k_mg_razon", "kmg"],
}

NUMERIC_FIELDS = [
    "arcilla", "limo", "arena", "da", "ph", "mo", "fosforo", "n_inorganico", "k", "mg",
    "ca", "na", "al", "cic", "cic_calculada", "h", "azufre", "hierro", "cobre", "zinc",
    "manganeso", "boro", "ca_mg", "mg_k", "ca_k", "ca_mg_k", "k_mg",
]

FILLDOWN_FIELDS = ["municipio", "localidad", "nombre_productor"]


# ========================= Detección de encabezados mejorada ============================ #

def _find_header_row(df_raw: pd.DataFrame) -> int:
    """
    Busca una fila que contenga varios encabezados esperados (o variantes).
    Escanea las primeras 50 filas y busca patrones específicos.
    """
    # Patrones específicos que identifican la fila de encabezados
    header_indicators = [
        "municipio", "localidad", "nombre", "productor", "cultivo", "anterior",
        "arcilla", "limo", "arena", "textura", "fosforo", "ph", "mo"
    ]
    
    max_rows_to_scan = min(50, len(df_raw))
    best_row = 0
    best_score = 0
    
    for i in range(max_rows_to_scan):
        row = df_raw.iloc[i]
        score = 0
        
        for cell in row:
            if cell is None:
                continue
            cell_norm = _norm_text(str(cell))
            if not cell_norm:
                continue
                
            # Buscar coincidencias con indicadores de encabezados
            for indicator in header_indicators:
                if indicator in cell_norm or cell_norm in indicator:
                    score += 1
                    
            # Bonificación especial para palabras clave exactas
            if cell_norm in ["municipio", "localidad", "nombre_del_productor", "cultivo_anterior"]:
                score += 2
        
        if score > best_score:
            best_score = score
            best_row = i
            
        # Si encontramos una fila con muchas coincidencias, la usamos
        if score >= 8:
            return i
    
    return best_row


def _build_column_map(cols: List[str]) -> Dict[str, Optional[str]]:
    """
    Recibe columnas (originales) y regresa:
       campo_esperado -> nombre_columna_original (o None si no existe)
    Versión mejorada que maneja mejor las coincidencias parciales.
    """
    mapping: Dict[str, Optional[str]] = {k: None for k in EXPECTED_MAP.keys()}

    # Crear una copia de las columnas disponibles para rastrear cuáles ya se usaron
    available_cols = list(cols)

    for exp, variants in EXPECTED_MAP.items():
        candidates = variants + [exp]
        best_match = None
        best_score = 0
        
        for col in available_cols:
            if col is None:
                continue
            col_norm = _norm_text(str(col))
            if not col_norm:
                continue
                
            # 1) igualdad exacta (máxima prioridad)
            for cand in candidates:
                if col_norm == _norm_text(cand):
                    mapping[exp] = col
                    if col in available_cols:
                        available_cols.remove(col)  # Evitar reutilizar columnas
                    best_match = col
                    break
            
            if best_match:
                break
                
            # 2) coincidencia parcial con scoring mejorado
            for cand in candidates:
                cand_norm = _norm_text(cand)
                score = 0
                
                # Coincidencia completa de una palabra dentro de otra
                if col_norm in cand_norm or cand_norm in col_norm:
                    score = min(len(col_norm), len(cand_norm)) * 2
                
                # Coincidencias parciales al inicio/final (más relevantes)
                if col_norm.startswith(cand_norm) or cand_norm.startswith(col_norm):
                    score += len(cand_norm) * 1.5
                if col_norm.endswith(cand_norm) or cand_norm.endswith(col_norm):
                    score += len(cand_norm) * 1.2
                
                # Bonificación para coincidencias de palabras clave específicas
                key_matches = 0
                for word in cand_norm.split('_'):
                    if word in col_norm:
                        key_matches += 1
                score += key_matches * 3
                
                if score > best_score:
                    best_score = score
                    best_match = col
        
        # Usar la mejor coincidencia si no hay exacta y no se ha asignado ya
        if mapping[exp] is None and best_match is not None:
            mapping[exp] = best_match
            if best_match in available_cols:
                available_cols.remove(best_match)

    return mapping


def _get_val(row: pd.Series, colname: Optional[str]):
    """Obtiene el valor de una columna específica en la fila."""
    if not colname or colname not in row.index:
        return None
    return row[colname]


# ============================ Función principal corregida ================================ #

def procesar_excel_y_guardar(file_bytes: bytes, db: Session):
    """
    Lee el Excel desde bytes, detecta encabezados, mapea columnas, limpia/convierte valores,
    hace forward-fill en campos clave y guarda en BD. Devuelve un resumen.
    """
    try:
        # 1) Leer todo como objeto para preservar tipos. Sin encabezados.
        df_raw = pd.read_excel(io.BytesIO(file_bytes), header=None, engine="openpyxl")

        # 2) Detectar fila de encabezados
        header_row_idx = _find_header_row(df_raw)

        # 3) Releer con encabezados reales
        df = pd.read_excel(io.BytesIO(file_bytes), header=header_row_idx, engine="openpyxl")

        # 4) Limpiar el DataFrame
        # Remover filas completamente vacías
        df = df.dropna(how="all")
        
        # Filtrar filas que son completamente vacías o contienen solo valores inválidos
        valid_rows = []
        for idx, row in df.iterrows():
            has_valid_data = False
            for col in df.columns:
                val = row[col]
                if not _is_empty_cell(val):
                    has_valid_data = True
                    break
            if has_valid_data:
                valid_rows.append(idx)
        
        df = df.loc[valid_rows]

        # 5) Mapear columnas usando nombres originales
        original_cols = [str(col) if col is not None else f"unnamed_{i}" for i, col in enumerate(df.columns)]
        df.columns = original_cols
        
        col_map = _build_column_map(original_cols)

        # 6) Forward-fill en campos clave (por celdas combinadas/vacías visualmente)
        for field in FILLDOWN_FIELDS:
            colname = col_map.get(field)
            if colname and colname in df.columns:
                # Usar una estrategia más inteligente para forward fill
                # Solo llenar si la celda está realmente vacía, no si contiene espacios o datos
                col_values = df[colname].copy()
                for i in range(len(col_values)):
                    if _is_empty_cell(col_values.iloc[i]) and i > 0:
                        # Buscar el último valor válido hacia atrás
                        for j in range(i-1, -1, -1):
                            if not _is_empty_cell(col_values.iloc[j]):
                                col_values.iloc[i] = col_values.iloc[j]
                                break
                df[colname] = col_values

        inserted = 0
        skipped = 0
        errors: List[dict] = []

        # 7) Iterar filas y construir objetos del modelo
        for idx, row in df.iterrows():
            try:
                data = {}
                
                # ----- Campos texto -----
                text_fields = ["municipio", "localidad", "nombre_productor", "cultivo_anterior", "textura", "columna1", "columna2"]
                for field in text_fields:
                    val = _get_val(row, col_map.get(field))
                    if val is None or _is_empty_cell(val):
                        data[field] = None
                    else:
                        s = str(val).strip()
                        data[field] = s if s else None

                # ----- Campos numéricos -----
                for field in NUMERIC_FIELDS:
                    val = _get_val(row, col_map.get(field))
                    data[field] = _to_decimal(val)

                # Verificar si la fila tiene datos mínimos requeridos
                # Ser más permisivo - solo saltar si REALMENTE no hay datos útiles
                has_key_data = any(not (_is_empty_cell(data.get(f)) or data.get(f) is None) 
                                 for f in ["municipio", "localidad", "nombre_productor"])
                has_numeric_data = any(data.get(f) is not None and data.get(f) != 0 
                                     for f in NUMERIC_FIELDS)

                # Solo saltar si no tiene datos clave Y no tiene datos numéricos significativos
                if not has_key_data and not has_numeric_data:
                    skipped += 1
                    continue

                # Crear registro
                registro = AnalisisQuimicosPendientes(
                    municipio=data.get("municipio"),
                    localidad=data.get("localidad"),
                    nombre_productor=data.get("nombre_productor"),
                    cultivo_anterior=data.get("cultivo_anterior"),
                    arcilla=data.get("arcilla"),
                    limo=data.get("limo"),
                    arena=data.get("arena"),
                    textura=data.get("textura"),
                    da=data.get("da"),
                    ph=data.get("ph"),
                    mo=data.get("mo"),
                    fosforo=data.get("fosforo"),
                    n_inorganico=data.get("n_inorganico"),
                    k=data.get("k"),
                    mg=data.get("mg"),
                    ca=data.get("ca"),
                    na=data.get("na"),
                    al=data.get("al"),
                    cic=data.get("cic"),
                    cic_calculada=data.get("cic_calculada"),
                    h=data.get("h"),
                    azufre=data.get("azufre"),
                    hierro=data.get("hierro"),
                    cobre=data.get("cobre"),
                    zinc=data.get("zinc"),
                    manganeso=data.get("manganeso"),
                    boro=data.get("boro"),
                    columna1=data.get("columna1"),
                    columna2=data.get("columna2"),
                    ca_mg=data.get("ca_mg"),
                    mg_k=data.get("mg_k"),
                    ca_k=data.get("ca_k"),
                    ca_mg_k=data.get("ca_mg_k"),
                    k_mg=data.get("k_mg"),
                )

                db.add(registro)
                inserted += 1

            except Exception as e:
                skipped += 1
                errors.append({"row_index": int(idx), "error": str(e)})
                continue

        # 8) Commit al final
        if inserted > 0:
            db.commit()

        # 9) Resumen detallado de depuración
        # Crear estadísticas adicionales para debugging
        mapped_columns = {k: v for k, v in col_map.items() if v is not None}
        unmapped_columns = [col for col in original_cols if col not in mapped_columns.values()]
        
        return {
            "rows_total_leidas": int(len(df)),
            "insertadas": int(inserted),
            "saltadas": int(skipped),
            "errores": errors[:10],  # Limitar errores mostrados
            "header_row_idx": int(header_row_idx),
            "column_map": col_map,
            "columns_detected": original_cols,
            "mapped_columns": mapped_columns,
            "unmapped_columns": unmapped_columns,
            "mapping_success_rate": f"{len(mapped_columns)}/{len(EXPECTED_MAP)} ({len(mapped_columns)/len(EXPECTED_MAP)*100:.1f}%)"
        }

    except Exception as e:
        return {
            "rows_total_leidas": 0,
            "insertadas": 0,
            "saltadas": 0,
            "errores": [{"error": f"Error general: {str(e)}"}],
            "header_row_idx": 0,
            "column_map": {},
            "columns_detected": [],
        }