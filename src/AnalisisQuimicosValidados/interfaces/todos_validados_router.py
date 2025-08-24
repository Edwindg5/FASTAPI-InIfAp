# src/AnalisisQuimicosValidados/interfaces/todos_validados_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import traceback

from src.core.database import get_db
from src.AnalisisQuimicosValidados.application.todos_validados_service import (
    obtener_todos_los_validados,
    obtener_validados_por_usuario_completo,
    buscar_validados_por_filtros,
    generar_estadisticas_validados
)
from src.AnalisisQuimicosValidados.application.excel_validados_service import (
    generar_excel_todos_validados,
    generar_excel_validados_por_usuario,
    generar_excel_validados_filtrado,
    obtener_nombre_archivo_validados,
    validar_datos_para_excel
)

from src.AnalisisQuimicosValidados.application.eliminar_validados_service import (
    eliminar_todos_validados_por_correo,
    verificar_analisis_validados_usuario
)

# Definir el route
router = APIRouter(prefix="/todos-los-validados", tags=["Todos los Análisis Quimicos Validados"])

# EXPORTAR el router con el nombre esperado en main.py
todos_validados_router = router


@router.get("/completo/")
def obtener_todos_validados_completo(db: Session = Depends(get_db)):
    """
    Obtiene TODOS los análisis validados sin límite (usar con precaución).
    
    Returns:
        Dict: Todos los análisis validados sin paginación
    """
    try:
        print("=== ENDPOINT: OBTENER TODOS LOS VALIDADOS COMPLETO (SIN LÍMITE) ===")
        
        # Obtener todos sin límite
        resultado = obtener_todos_los_validados(db, limit=None)
        
        if not resultado["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"Error al obtener análisis validados: {resultado.get('error', 'Error desconocido')}"
            )
        
        return {
            "success": True,
            "message": f"Se obtuvieron TODOS los {resultado['total_registros']} análisis validados",
            "warning": "Este endpoint retorna todos los registros sin paginación",
            **resultado
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener todos los validados: {str(e)}"
        )


# =================== ENDPOINTS DE DESCARGA EXCEL ===================

@router.get("/excel/todos/")
def descargar_excel_todos_validados(db: Session = Depends(get_db)):
    """
    Descarga TODOS los análisis químicos validados en formato Excel.
    
    ⚠️  PRECAUCIÓN: Este endpoint descarga todos los registros sin límite.
    
    Returns:
        StreamingResponse: Archivo Excel con todos los análisis validados
    """
    try:
        print("=== DESCARGA EXCEL: TODOS LOS VALIDADOS ===")
        
        # Validar que existan datos
        validacion = validar_datos_para_excel(db)
        if not validacion["tiene_datos"]:
            raise HTTPException(
                status_code=404,
                detail=validacion["mensaje"]
            )
        
        print(f"✓ Datos disponibles: {validacion['total_registros']} registros")
        
        # Generar archivo Excel
        buffer_excel = generar_excel_todos_validados(db)
        
        if buffer_excel is None:
            raise HTTPException(
                status_code=500,
                detail="Error al generar el archivo Excel"
            )
        
        # Nombre del archivo
        nombre_archivo = obtener_nombre_archivo_validados("completo")
        
        print(f"✅ Archivo Excel generado: {nombre_archivo}")
        
        return StreamingResponse(
            buffer_excel,  # Primer parámetro posicional, NO usar 'io='
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={nombre_archivo}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar Excel: {str(e)}"
        )


@router.get("/excel/filtrado/")
def descargar_excel_filtrado(
    municipio: Optional[str] = Query(default=None),
    fecha_desde: Optional[str] = Query(default=None),
    fecha_hasta: Optional[str] = Query(default=None),
    usuario_validador_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db)
):
    """
    Descarga análisis validados con filtros aplicados en formato Excel.
    
    Args:
        municipio (Optional[str]): Filtro por municipio
        fecha_desde (Optional[str]): Fecha inicio (YYYY-MM-DD)
        fecha_hasta (Optional[str]): Fecha fin (YYYY-MM-DD)  
        usuario_validador_id (Optional[int]): ID del usuario validador
        
    Returns:
        StreamingResponse: Archivo Excel filtrado
    """
    try:
        print("=== DESCARGA EXCEL: FILTRADO ===")
        
        # Convertir fechas
        fecha_desde_dt = None
        fecha_hasta_dt = None
        
        if fecha_desde:
            try:
                fecha_desde_dt = datetime.strptime(fecha_desde, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_desde inválido")
        
        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.strptime(fecha_hasta, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Formato de fecha_hasta inválido")
        
        # Verificar que hay resultados con los filtros
        verificacion = buscar_validados_por_filtros(
            db, municipio, fecha_desde_dt, fecha_hasta_dt, 
            usuario_validador_id, limit=1, offset=0
        )
        
        if not verificacion["success"]:
            raise HTTPException(status_code=500, detail="Error verificando filtros")
        
        if verificacion["total_encontrados"] == 0:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron análisis con los filtros aplicados"
            )
        
        print(f"✓ Filtros válidos: {verificacion['total_encontrados']} registros encontrados")
        
        # Generar Excel
        buffer_excel = generar_excel_validados_filtrado(
            db, municipio, fecha_desde_dt, fecha_hasta_dt, usuario_validador_id
        )
        
        if buffer_excel is None:
            raise HTTPException(
                status_code=500,
                detail="Error al generar el archivo Excel filtrado"
            )
        
        # Nombre del archivo
        filtros = {
            "municipio": municipio,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "usuario_validador_id": usuario_validador_id
        }
        nombre_archivo = obtener_nombre_archivo_validados("filtrado", filtros=filtros)
        
        print(f"✅ Archivo Excel filtrado generado: {nombre_archivo}")
        
        return StreamingResponse(
            buffer_excel,  # Primer parámetro posicional, NO usar 'io='
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={nombre_archivo}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar Excel filtrado: {str(e)}"
        )



    """
    Endpoint de prueba para verificar la conexión y funcionalidad básica.
    
    Returns:
        Dict: Estado de la conexión y funcionamiento
    """
    try:
        print("=== TEST: CONEXIÓN VALIDADOS ===")
        
        # Importar modelo para prueba
        from src.AnalisisQuimicosValidados.infrastructure.analisis_quimicos_validados_model import (
            AnalisisQuimicosValidados,
        )
        
        # Hacer una consulta simple
        count = db.query(AnalisisQuimicosValidados).count()
        
        # Obtener un registro de ejemplo
        ejemplo = db.query(AnalisisQuimicosValidados).first()
        
        return {
            "success": True,
            "message": "Conexión exitosa",
            "test_results": {
                "total_registros_en_bd": count,
                "tiene_datos": count > 0,
                "ejemplo_disponible": ejemplo is not None,
                "ejemplo_id": ejemplo.id if ejemplo else None,
                "servicios_funcionando": True
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error en test: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error en test de conexión: {str(e)}"
        )
        
        
@router.delete("/usuario/{correo_usuario}/eliminar")
def eliminar_todos_validados_usuario(
    correo_usuario: str,
    confirmar: bool = Query(default=False, description="Confirmación requerida para eliminar"),
    db: Session = Depends(get_db)
):
    """
    Elimina TODOS los análisis químicos validados de un usuario por su correo electrónico.
    
    ⚠️  **OPERACIÓN DESTRUCTIVA**: Esta acción es irreversible.
    
    Args:
        correo_usuario (str): Correo electrónico del usuario
        confirmar (bool): Debe ser True para confirmar la eliminación
        
    Returns:
        Dict: Resultado de la eliminación con detalles del proceso
        
    Raises:
        HTTPException: 
            - 400: Si falta confirmación o datos inválidos
            - 404: Si el usuario no existe
            - 500: Error interno del servidor
    """
    try:
        print(f"=== ENDPOINT: ELIMINAR ANÁLISIS VALIDADOS POR CORREO ===")
        print(f"Correo usuario: {correo_usuario}")
        print(f"Confirmación: {confirmar}")
        
        # Validación de entrada
        if not correo_usuario or not correo_usuario.strip():
            raise HTTPException(
                status_code=400,
                detail="El correo del usuario es requerido"
            )
        
        # Validación de confirmación
        if not confirmar:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Confirmación requerida para esta operación destructiva",
                    "required_parameter": "confirmar=true",
                    "warning": "Esta operación eliminará TODOS los análisis validados del usuario de forma permanente"
                }
            )
        
        # Ejecutar eliminación
        resultado = eliminar_todos_validados_por_correo(correo_usuario, db)
        
        # Manejar diferentes tipos de resultado
        if not resultado["success"]:
            # Error de usuario no encontrado
            if "no encontrado" in resultado.get("message", "").lower():
                raise HTTPException(
                    status_code=404,
                    detail={
                        "message": resultado["message"],
                        "usuario_buscado": correo_usuario,
                        "error": resultado.get("error", "Usuario no encontrado")
                    }
                )
            
            # Otros errores
            raise HTTPException(
                status_code=500,
                detail={
                    "message": resultado["message"],
                    "error": resultado.get("error", "Error desconocido"),
                    "usuario": correo_usuario
                }
            )
        
        # Éxito
        status_code = 200
        response_data = {
            "success": True,
            "message": resultado["message"],
            "operation": "DELETE_ALL_VALIDATED_ANALYSES",
            "usuario": resultado["usuario"],
            "usuario_id": resultado.get("usuario_id"),
            "registros_eliminados": resultado["eliminados"],
            "timestamp": datetime.now().isoformat()
        }
        
        # Agregar detalles adicionales si están disponibles
        if "detalles" in resultado:
            response_data["detalles"] = resultado["detalles"]
        
        print(f"✅ Eliminación exitosa: {resultado['eliminados']} registros")
        
        return response_data
        
    except HTTPException:
        # Re-levantar HTTPException para mantener el código de estado
        raise
    except Exception as e:
        print(f"❌ Error crítico en endpoint: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Error interno del servidor: {str(e)}",
                "error": str(e),
                "tipo_error": type(e).__name__,
                "usuario": correo_usuario
            }
        )


@router.get("/usuario/{correo_usuario}/verificar")
def verificar_analisis_validados_usuario_endpoint(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Verifica cuántos análisis químicos validados tiene un usuario sin eliminarlos.
    
    Útil para verificar antes de realizar una eliminación masiva.
    
    Args:
        correo_usuario (str): Correo electrónico del usuario
        
    Returns:
        Dict: Información sobre los análisis validados del usuario
    """
    try:
        print(f"=== ENDPOINT: VERIFICAR ANÁLISIS VALIDADOS ===")
        print(f"Usuario: {correo_usuario}")
        
        if not correo_usuario or not correo_usuario.strip():
            raise HTTPException(
                status_code=400,
                detail="El correo del usuario es requerido"
            )
        
        # Ejecutar verificación
        resultado = verificar_analisis_validados_usuario(correo_usuario, db)
        
        if not resultado["success"]:
            if "no encontrado" in resultado.get("message", "").lower():
                raise HTTPException(
                    status_code=404,
                    detail=resultado["message"]
                )
            raise HTTPException(
                status_code=500,
                detail=resultado["message"]
            )
        
        return {
            **resultado,
            "timestamp": datetime.now().isoformat(),
            "operation": "VERIFY_VALIDATED_ANALYSES"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al verificar análisis validados: {str(e)}"
        )