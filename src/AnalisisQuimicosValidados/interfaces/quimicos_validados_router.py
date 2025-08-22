# src/AnalisisQuimicosValidados/interfaces/quimicos_validados_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
import traceback

from src.core.database import get_db
from src.AnalisisQuimicosValidados.application.quimicos_validados_service import (
    obtener_analisis_pendientes_por_usuario,
    obtener_todos_usuarios_con_pendientes,
    validar_analisis_quimicos,
    obtener_analisis_validados_por_usuario,
    validar_analisis_por_correo_usuario,  # NUEVA FUNCIÓN
)

router = APIRouter(prefix="/analisis-quimicos-validados", tags=["Análisis Químicos Validados"])


@router.get("/usuarios-con-pendientes/")
def obtener_usuarios_con_pendientes(db: Session = Depends(get_db)):
    """
    Obtiene todos los usuarios que tienen análisis químicos pendientes.
    Versión con mejor manejo de errores.
    """
    try:
        print("=== INICIANDO obtener_usuarios_con_pendientes ===")
        
        # Verificar conexión a base de datos
        try:
            db.execute(text("SELECT 1"))
            print("✓ Conexión a BD exitosa")
        except Exception as e:
            print(f"✗ Error de conexión a BD: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error de conexión a base de datos: {str(e)}"
            )
        
        # Llamar al servicio
        usuarios = obtener_todos_usuarios_con_pendientes(db)
        print(f"✓ Servicio ejecutado, usuarios encontrados: {len(usuarios)}")
        
        return {
            "success": True,
            "total_usuarios": len(usuarios),
            "usuarios": usuarios
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"✗ Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al validar análisis del usuario: {str(e)}"
        )




@router.get("/usuario/{correo_usuario}/pendientes/")
def obtener_pendientes_por_usuario(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los análisis químicos pendientes de un usuario específico.
    """
    try:
        print(f"=== OBTENIENDO PENDIENTES PARA: {correo_usuario} ===")
        
        resultado = obtener_analisis_pendientes_por_usuario(correo_usuario, db)
        
        if resultado is None:
            raise HTTPException(
                status_code=404,
                detail=f"Usuario con correo '{correo_usuario}' no encontrado"
            )
        
        return {
            "success": True,
            **resultado
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"✗ Error: {e}")
        print(f"✗ Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener análisis pendientes: {str(e)}"
        )


@router.post("/validar/")
def validar_analisis(
    validacion_data: dict,
    db: Session = Depends(get_db)
):
    """
    Valida análisis químicos pendientes y los mueve a la tabla de validados.
    """
    try:
        print(f"=== VALIDANDO ANÁLISIS ===")
        print(f"Data recibida: {validacion_data}")
        
        analisis_ids = validacion_data.get("analisis_ids", [])
        comentario = validacion_data.get("comentario_validacion")
        
        if not analisis_ids:
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar al menos un ID de análisis para validar"
            )
        
        resultado = validar_analisis_quimicos(analisis_ids, comentario, db)
        
        return resultado
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"✗ Error: {e}")
        print(f"✗ Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al validar análisis: {str(e)}"
        )


@router.get("/usuario/{correo_usuario}/validados/")
def obtener_validados_por_usuario(
    correo_usuario: str,
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0)
):
    """
    Obtiene los análisis químicos validados de un usuario específico.
    """
    try:
        resultado = obtener_analisis_validados_por_usuario(
            correo_usuario, db, limit, offset
        )
        
        if resultado is None:
            raise HTTPException(
                status_code=404,
                detail=f"Usuario con correo '{correo_usuario}' no encontrado"
            )
        
        return {
            "success": True,
            **resultado
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"✗ Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener análisis validados: {str(e)}"
        )




@router.post("/validar-simple/{correo_usuario}/")
def validar_usuario_simple(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint simple que retorna {"status": "validado"} o error.
    Valida todos los análisis pendientes del usuario, los asigna al Administrador (ID=1)
    y ELIMINA completamente los registros de la tabla analisis_quimicos_pendientes.
    """
    try:
        print(f"=== VALIDACIÓN SIMPLE CON ELIMINACIÓN PARA: {correo_usuario} ===")
        
        # Validar análisis del usuario (ahora incluye eliminación)
        resultado = validar_analisis_por_correo_usuario(
            correo_usuario, None, db
        )
        
        if resultado["success"] and resultado["validados"] > 0:
            print(f"✅ PROCESO COMPLETADO EXITOSAMENTE:")
            print(f"   - Usuario: {correo_usuario}")
            print(f"   - Análisis validados: {resultado['validados']}")
            print(f"   - Registros eliminados: {resultado.get('eliminados', 0)}")
            print(f"   - Asignados a Administrador ID: {resultado['administrador_id']}")
            
            # Respuesta simple como solicitaste
            return {"status": "validado"}
            
        elif resultado["success"] and resultado["validados"] == 0:
            print(f"ℹ️  Usuario sin pendientes: {correo_usuario}")
            return {"status": "sin_pendientes"}
            
        else:
            print(f"❌ Error en validación: {resultado['message']}")
            raise HTTPException(
                status_code=400,
                detail=resultado["message"]
            )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"✗ Error crítico: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al validar análisis del usuario: {str(e)}"
        )
    
    except HTTPException:
        raise