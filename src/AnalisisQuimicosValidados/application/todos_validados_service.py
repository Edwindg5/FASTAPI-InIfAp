# src/AnalisisQuimicosValidados/application/todos_validados_service.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime
import traceback

from src.AnalisisQuimicosValidados.infrastructure.analisis_quimicos_validados_model import (
    AnalisisQuimicosValidados,
)
from src.Users.infrastructure.users_model import Users


def obtener_todos_los_validados(
    db: Session, 
    limit: Optional[int] = None, 
    offset: int = 0
) -> Dict[str, Any]:
    """
    Obtiene todos los análisis químicos validados de la tabla analisis_quimicos_validados.
    
    Args:
        db (Session): Sesión de base de datos
        limit (Optional[int]): Límite de registros (None para todos)
        offset (int): Offset para paginación
        
    Returns:
        Dict: Información completa de los análisis validados
    """
    try:
        print("=== OBTENIENDO TODOS LOS ANÁLISIS VALIDADOS ===")
        
        # Query base
        query = (
            db.query(AnalisisQuimicosValidados)
            .order_by(desc(AnalisisQuimicosValidados.fecha_validacion))
        )
        
        # Contar total de registros
        total_registros = query.count()
        print(f"Total de análisis validados en BD: {total_registros}")
        
        # Aplicar paginación si se especifica
        if limit is not None:
            query = query.offset(offset).limit(limit)
            print(f"Aplicando paginación: offset={offset}, limit={limit}")
        
        # Ejecutar consulta
        analisis_validados = query.all()
        
        if not analisis_validados:
            print("No se encontraron análisis validados")
            return {
                "success": True,
                "total_registros": 0,
                "registros_obtenidos": 0,
                "analisis_validados": [],
                "usuarios_validadores": [],
                "estadisticas": {}
            }
        
        print(f"Análisis validados obtenidos: {len(analisis_validados)}")
        
        # Convertir a diccionarios y procesar datos
        analisis_response = []
        usuarios_validadores = set()
        
        for analisis in analisis_validados:
            try:
                # Obtener información del usuario validador
                usuario_validador = None
                if analisis.user_id_FK:
                    usuario = db.query(Users).filter(
                        Users.ID_user == analisis.user_id_FK
                    ).first()
                    if usuario:
                        usuario_validador = {
                            "id": usuario.ID_user,
                            "correo": usuario.correo,
                            "nombre": f"{usuario.nombre or ''} {usuario.apellido or ''}".strip()
                        }
                        usuarios_validadores.add(usuario.correo)
                
                analisis_dict = {
                    "id": analisis.id,
                    "municipio_id_FK": analisis.municipio_id_FK,
                    "user_id_FK": analisis.user_id_FK,
                    "usuario_validador": usuario_validador,
                    
                    # Datos del productor y ubicación
                    "municipio": analisis.municipio,
                    "localidad": analisis.localidad,
                    "nombre_productor": analisis.nombre_productor,
                    "cultivo_anterior": analisis.cultivo_anterior,
                    
                    # Propiedades físicas
                    "arcilla": float(analisis.arcilla) if analisis.arcilla else None,
                    "limo": float(analisis.limo) if analisis.limo else None,
                    "arena": float(analisis.arena) if analisis.arena else None,
                    "textura": analisis.textura,
                    "da": float(analisis.da) if analisis.da else None,
                    
                    # Propiedades químicas básicas
                    "ph": float(analisis.ph) if analisis.ph else None,
                    "mo": float(analisis.mo) if analisis.mo else None,
                    "fosforo": float(analisis.fosforo) if analisis.fosforo else None,
                    "n_inorganico": float(analisis.n_inorganico) if analisis.n_inorganico else None,
                    
                    # Macronutrientes
                    "k": float(analisis.k) if analisis.k else None,
                    "mg": float(analisis.mg) if analisis.mg else None,
                    "ca": float(analisis.ca) if analisis.ca else None,
                    "na": float(analisis.na) if analisis.na else None,
                    
                    # CIC y otros
                    "al": float(analisis.al) if analisis.al else None,
                    "cic": float(analisis.cic) if analisis.cic else None,
                    "cic_calculada": float(analisis.cic_calculada) if analisis.cic_calculada else None,
                    "h": float(analisis.h) if analisis.h else None,
                    
                    # Micronutrientes
                    "azufre": float(analisis.azufre) if analisis.azufre else None,
                    "hierro": float(analisis.hierro) if analisis.hierro else None,
                    "cobre": float(analisis.cobre) if analisis.cobre else None,
                    "zinc": float(analisis.zinc) if analisis.zinc else None,
                    "manganeso": float(analisis.manganeso) if analisis.manganeso else None,
                    "boro": float(analisis.boro) if analisis.boro else None,
                    
                    # Relaciones catiónicas
                    "ca_mg": float(analisis.ca_mg) if analisis.ca_mg else None,
                    "mg_k": float(analisis.mg_k) if analisis.mg_k else None,
                    "ca_k": float(analisis.ca_k) if analisis.ca_k else None,
                    "ca_mg_k": float(analisis.ca_mg_k) if analisis.ca_mg_k else None,
                    "k_mg": float(analisis.k_mg) if analisis.k_mg else None,
                    
                    # Columnas adicionales
                    "columna1": analisis.columna1,
                    "columna2": analisis.columna2,
                    
                    # Fechas
                    "fecha_validacion": analisis.fecha_validacion.isoformat() if analisis.fecha_validacion else None,
                    "fecha_creacion": analisis.fecha_creacion.isoformat() if analisis.fecha_creacion else None,
                }
                
                analisis_response.append(analisis_dict)
                
            except Exception as e:
                print(f"Error procesando análisis validado {analisis.id}: {e}")
                continue
        
        # Generar estadísticas
        estadisticas = generar_estadisticas_validados(analisis_response)
        
        print(f"✅ Procesamiento completado:")
        print(f"   - Total en BD: {total_registros}")
        print(f"   - Procesados exitosamente: {len(analisis_response)}")
        print(f"   - Usuarios validadores únicos: {len(usuarios_validadores)}")
        
        return {
            "success": True,
            "total_registros": total_registros,
            "registros_obtenidos": len(analisis_response),
            "analisis_validados": analisis_response,
            "usuarios_validadores": list(usuarios_validadores),
            "estadisticas": estadisticas,
            "paginacion": {
                "limit": limit,
                "offset": offset,
                "tiene_mas": (offset + len(analisis_response)) < total_registros if limit else False
            }
        }
        
    except Exception as e:
        print(f"❌ Error en obtener_todos_los_validados: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "total_registros": 0,
            "registros_obtenidos": 0,
            "analisis_validados": [],
            "usuarios_validadores": [],
            "estadisticas": {}
        }


def obtener_validados_por_usuario_completo(
    user_id_FK: int, 
    db: Session,
    limit: Optional[int] = None,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Obtiene todos los análisis validados de un usuario específico por su ID.
    
    Args:
        user_id_FK (int): ID del usuario validador
        db (Session): Sesión de base de datos
        limit (Optional[int]): Límite de registros
        offset (int): Offset para paginación
        
    Returns:
        Dict: Análisis validados del usuario
    """
    try:
        print(f"=== OBTENIENDO VALIDADOS DEL USUARIO ID: {user_id_FK} ===")
        
        # Obtener información del usuario
        usuario = db.query(Users).filter(Users.ID_user == user_id_FK).first()
        if not usuario:
            return {
                "success": False,
                "error": f"Usuario con ID {user_id_FK} no encontrado"
            }
        
        # Query base
        query = (
            db.query(AnalisisQuimicosValidados)
            .filter(AnalisisQuimicosValidados.user_id_FK == user_id_FK)
            .order_by(desc(AnalisisQuimicosValidados.fecha_validacion))
        )
        
        # Contar total
        total_registros = query.count()
        
        # Aplicar paginación
        if limit is not None:
            query = query.offset(offset).limit(limit)
        
        analisis_validados = query.all()
        
        # Procesar resultados (similar al método anterior pero más simple)
        analisis_response = []
        for analisis in analisis_validados:
            try:
                analisis_dict = {
                    "id": analisis.id,
                    "municipio": analisis.municipio,
                    "localidad": analisis.localidad,
                    "nombre_productor": analisis.nombre_productor,
                    "ph": float(analisis.ph) if analisis.ph else None,
                    "mo": float(analisis.mo) if analisis.mo else None,
                    "fosforo": float(analisis.fosforo) if analisis.fosforo else None,
                    "fecha_validacion": analisis.fecha_validacion.isoformat() if analisis.fecha_validacion else None,
                    # Agregar más campos según necesidad
                }
                analisis_response.append(analisis_dict)
            except Exception as e:
                print(f"Error procesando análisis {analisis.id}: {e}")
                continue
        
        return {
            "success": True,
            "usuario": {
                "id": usuario.ID_user,
                "correo": usuario.correo,
                "nombre": f"{usuario.nombre or ''} {usuario.apellido or ''}".strip()
            },
            "total_registros": total_registros,
            "registros_obtenidos": len(analisis_response),
            "analisis_validados": analisis_response
        }
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"success": False, "error": str(e)}


def generar_estadisticas_validados(analisis_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Genera estadísticas sobre los análisis validados.
    
    Args:
        analisis_data (List[Dict]): Lista de análisis validados
        
    Returns:
        Dict: Estadísticas calculadas
    """
    if not analisis_data:
        return {}
    
    try:
        # Contadores básicos
        total_analisis = len(analisis_data)
        
        # Agrupar por municipio
        municipios = {}
        usuarios_validadores = {}
        cultivos_anteriores = {}
        
        # Estadísticas numéricas básicas
        ph_valores = []
        mo_valores = []
        fosforo_valores = []
        
        for analisis in analisis_data:
            # Municipios
            municipio = analisis.get("municipio", "Sin especificar")
            municipios[municipio] = municipios.get(municipio, 0) + 1
            
            # Usuarios validadores
            if analisis.get("usuario_validador"):
                validador = analisis["usuario_validador"]["correo"]
                usuarios_validadores[validador] = usuarios_validadores.get(validador, 0) + 1
            
            # Cultivos anteriores
            cultivo = analisis.get("cultivo_anterior", "Sin especificar")
            cultivos_anteriores[cultivo] = cultivos_anteriores.get(cultivo, 0) + 1
            
            # Valores numéricos para estadísticas
            if analisis.get("ph") is not None:
                ph_valores.append(analisis["ph"])
            if analisis.get("mo") is not None:
                mo_valores.append(analisis["mo"])
            if analisis.get("fosforo") is not None:
                fosforo_valores.append(analisis["fosforo"])
        
        # Calcular promedios
        estadisticas_numericas = {}
        if ph_valores:
            estadisticas_numericas["ph"] = {
                "promedio": sum(ph_valores) / len(ph_valores),
                "minimo": min(ph_valores),
                "maximo": max(ph_valores),
                "total_mediciones": len(ph_valores)
            }
        
        if mo_valores:
            estadisticas_numericas["materia_organica"] = {
                "promedio": sum(mo_valores) / len(mo_valores),
                "minimo": min(mo_valores),
                "maximo": max(mo_valores),
                "total_mediciones": len(mo_valores)
            }
        
        if fosforo_valores:
            estadisticas_numericas["fosforo"] = {
                "promedio": sum(fosforo_valores) / len(fosforo_valores),
                "minimo": min(fosforo_valores),
                "maximo": max(fosforo_valores),
                "total_mediciones": len(fosforo_valores)
            }
        
        return {
            "total_analisis": total_analisis,
            "municipios_top_5": dict(sorted(municipios.items(), key=lambda x: x[1], reverse=True)[:5]),
            "usuarios_validadores": usuarios_validadores,
            "cultivos_anteriores_top_5": dict(sorted(cultivos_anteriores.items(), key=lambda x: x[1], reverse=True)[:5]),
            "estadisticas_numericas": estadisticas_numericas,
            "fecha_generacion": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"Error generando estadísticas: {e}")
        return {"error": str(e)}


def buscar_validados_por_filtros(
    db: Session,
    municipio: Optional[str] = None,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    usuario_validador_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Busca análisis validados aplicando filtros específicos.
    
    Args:
        db (Session): Sesión de base de datos
        municipio (Optional[str]): Filtrar por municipio
        fecha_desde (Optional[datetime]): Fecha inicio
        fecha_hasta (Optional[datetime]): Fecha fin
        usuario_validador_id (Optional[int]): ID del usuario validador
        limit (int): Límite de registros
        offset (int): Offset para paginación
        
    Returns:
        Dict: Resultados filtrados
    """
    try:
        print(f"=== BÚSQUEDA CON FILTROS ===")
        print(f"Municipio: {municipio}")
        print(f"Fecha desde: {fecha_desde}")
        print(f"Fecha hasta: {fecha_hasta}")
        print(f"Usuario validador: {usuario_validador_id}")
        
        # Query base
        query = db.query(AnalisisQuimicosValidados)
        
        # Aplicar filtros
        if municipio:
            query = query.filter(AnalisisQuimicosValidados.municipio.ilike(f"%{municipio}%"))
        
        if fecha_desde:
            query = query.filter(AnalisisQuimicosValidados.fecha_validacion >= fecha_desde)
        
        if fecha_hasta:
            query = query.filter(AnalisisQuimicosValidados.fecha_validacion <= fecha_hasta)
        
        if usuario_validador_id:
            query = query.filter(AnalisisQuimicosValidados.user_id_FK == usuario_validador_id)
        
        # Ordenar y paginar
        query = query.order_by(desc(AnalisisQuimicosValidados.fecha_validacion))
        
        total_registros = query.count()
        analisis_filtrados = query.offset(offset).limit(limit).all()
        
        # Procesar resultados
        analisis_response = []
        for analisis in analisis_filtrados:
            analisis_dict = {
                "id": analisis.id,
                "municipio": analisis.municipio,
                "localidad": analisis.localidad,
                "nombre_productor": analisis.nombre_productor,
                "fecha_validacion": analisis.fecha_validacion.isoformat() if analisis.fecha_validacion else None,
                # Agregar más campos según necesidad
            }
            analisis_response.append(analisis_dict)
        
        return {
            "success": True,
            "total_encontrados": total_registros,
            "registros_obtenidos": len(analisis_response),
            "analisis_filtrados": analisis_response,
            "filtros_aplicados": {
                "municipio": municipio,
                "fecha_desde": fecha_desde.isoformat() if fecha_desde else None,
                "fecha_hasta": fecha_hasta.isoformat() if fecha_hasta else None,
                "usuario_validador_id": usuario_validador_id
            }
        }
        
    except Exception as e:
        print(f"❌ Error en búsqueda filtrada: {e}")
        return {"success": False, "error": str(e)}