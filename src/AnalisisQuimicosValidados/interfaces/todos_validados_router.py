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
def descargar_excel_filtrado_por_usuario_archivo(
    user_id: int = Query(..., description="ID del usuario propietario de los análisis"),
    nombre_archivo: str = Query(..., description="Nombre exacto del archivo a descargar"),
    db: Session = Depends(get_db)
):
    """
    Descarga análisis validados de un usuario específico y archivo específico en formato Excel.
    
    Args:
        user_id (int): ID del usuario propietario de los análisis
        nombre_archivo (str): Nombre exacto del archivo a descargar
        
    Returns:
        StreamingResponse: Archivo Excel con los análisis del usuario y archivo especificado
        
    Raises:
        HTTPException:
            - 400: Si faltan parámetros requeridos
            - 404: Si no se encuentran análisis con los criterios especificados
            - 500: Error interno del servidor
    """
    try:
        print("=== DESCARGA EXCEL: FILTRADO POR USUARIO Y ARCHIVO ===")
        print(f"User ID: {user_id}")
        print(f"Nombre archivo: {nombre_archivo}")
        
        # Validaciones de entrada
        if not user_id or user_id <= 0:
            raise HTTPException(
                status_code=400,
                detail="El user_id es requerido y debe ser mayor a 0"
            )
            
        if not nombre_archivo or not nombre_archivo.strip():
            raise HTTPException(
                status_code=400,
                detail="El nombre_archivo es requerido y no puede estar vacío"
            )
        
        # Importar el nuevo servicio
        from src.AnalisisQuimicosValidados.application.excel_usuario_archivo_service import (
            generar_excel_por_usuario_archivo,
            verificar_datos_usuario_archivo,
            obtener_nombre_archivo_descarga
        )
        
        # Verificar que existan datos con los criterios especificados
        verificacion = verificar_datos_usuario_archivo(db, user_id, nombre_archivo.strip())
        
        if not verificacion["success"]:
            if "no encontrado" in verificacion.get("message", "").lower():
                raise HTTPException(
                    status_code=404,
                    detail={
                        "message": verificacion["message"],
                        "user_id": user_id,
                        "nombre_archivo": nombre_archivo,
                        "detalles": verificacion.get("detalles", {})
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error verificando datos: {verificacion['message']}"
                )
        
        print(f"✓ Datos encontrados: {verificacion['total_registros']} análisis")
        print(f"✓ Usuario: {verificacion.get('usuario_info', {}).get('nombre', 'N/A')}")
        
        # Generar archivo Excel
        buffer_excel = generar_excel_por_usuario_archivo(db, user_id, nombre_archivo.strip())
        
        if buffer_excel is None:
            raise HTTPException(
                status_code=500,
                detail="Error al generar el archivo Excel"
            )
        
        # Obtener nombre del archivo para descarga
        nombre_descarga = obtener_nombre_archivo_descarga(
            verificacion.get("usuario_info", {}),
            nombre_archivo.strip()
        )
        
        print(f"✅ Archivo Excel generado exitosamente: {nombre_descarga}")
        
        return StreamingResponse(
            buffer_excel,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={nombre_descarga}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Error al generar Excel: {str(e)}",
                "error": str(e),
                "user_id": user_id,
                "nombre_archivo": nombre_archivo
            }
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

@router.get("/listar/todos/")
def listar_todos_validados(
    db: Session = Depends(get_db)
):
    """
    Lista TODOS los análisis químicos validados AGRUPADOS por archivo.
    Muestra un registro por archivo con la cantidad de análisis que contiene.
    
    Returns:
        Dict: Lista de archivos validados con cantidad de análisis
    """
    try:
        print("=== ENDPOINT: LISTAR TODOS LOS VALIDADOS AGRUPADOS ===")
        
        # Importar servicio
        from src.AnalisisQuimicosValidados.application.listar_validados_service import (
            listar_todos_validados_con_usuario
        )
        
        resultado = listar_todos_validados_con_usuario(db)
        
        if not resultado["success"]:
            raise HTTPException(
                status_code=500,
                detail=resultado["message"]
            )
        
        return {
            "success": True,
            "message": "Archivos validados obtenidos exitosamente",
            "data": resultado["data"],
            "total": resultado["total"],
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener análisis validados: {str(e)}"
        )