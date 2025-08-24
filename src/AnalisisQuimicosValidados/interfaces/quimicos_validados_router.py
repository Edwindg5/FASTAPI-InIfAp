# src/AnalisisQuimicosValidados/interfaces/quimicos_validados_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
import traceback

from src.AnalisisQuimicosValidados.application.eliminar_validados_service import eliminar_analisis_validados_con_admin
from src.core.database import get_db
from src.Users.infrastructure.users_model import Users
from src.AnalisisQuimicosValidados.application.quimicos_validados_service import (
    obtener_analisis_pendientes_por_usuario,
    obtener_todos_usuarios_con_pendientes,
    validar_analisis_quimicos,
    obtener_analisis_validados_por_usuario,
    validar_analisis_por_correo_usuario,
    eliminar_analisis_validados_por_correo,
    eliminar_analisis_pendientes_por_archivo,
    obtener_analisis_validados_agrupados_por_usuario,

)
from src.AnalisisQuimicosValidados.application.excel_export_service import (
    generar_excel_pendientes_por_usuario,
    obtener_nombre_archivo_excel,
    validar_usuario_existe,
    contar_pendientes_usuario
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
            detail=f"Error al obtener usuarios con pendientes: {str(e)}"
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


@router.get("/usuario/{correo_usuario}/pendientes/excel/")
def descargar_pendientes_excel(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Descarga todos los análisis químicos pendientes de un usuario en formato Excel.
    
    Args:
        correo_usuario: Correo electrónico del usuario
        
    Returns:
        StreamingResponse: Archivo Excel para descarga
    """
    try:
        print(f"=== DESCARGA EXCEL PENDIENTES PARA: {correo_usuario} ===")
        
        # Validar que el usuario existe
        if not validar_usuario_existe(correo_usuario, db):
            raise HTTPException(
                status_code=404,
                detail=f"Usuario con correo '{correo_usuario}' no encontrado"
            )
        
        # Contar análisis pendientes
        total_pendientes = contar_pendientes_usuario(correo_usuario, db)
        if total_pendientes == 0:
            raise HTTPException(
                status_code=404,
                detail=f"El usuario '{correo_usuario}' no tiene análisis pendientes"
            )
        
        print(f"✓ Usuario encontrado con {total_pendientes} análisis pendientes")
        
        # Generar archivo Excel
        buffer_excel = generar_excel_pendientes_por_usuario(correo_usuario, db)
        
        if buffer_excel is None:
            raise HTTPException(
                status_code=500,
                detail="Error al generar el archivo Excel"
            )
        
        # Generar nombre del archivo
        nombre_archivo = obtener_nombre_archivo_excel(correo_usuario)
        
        print(f"✅ Archivo Excel generado: {nombre_archivo}")
        
        # Retornar como descarga
        return StreamingResponse(
            buffer_excel,
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




@router.post("/validar-simple/{correo_usuario}/")
def validar_usuario_simple(
    correo_usuario: str,
    request_data: dict,  # Cambio: ahora recibe datos en el body
    db: Session = Depends(get_db)
):
    """
    Endpoint que valida análisis pendientes de un usuario por correo Y nombre de archivo específico.
    Retorna {"status": "validado"} o error.
    
    Body esperado:
    {
        "nombre_archivo": "archivo.xlsx",
        "comentario_validacion": "opcional"
    }
    """
    try:
        print(f"=== VALIDACIÓN SIMPLE CON ARCHIVO ESPECÍFICO PARA: {correo_usuario} ===")
        
        # Obtener nombre del archivo del request body
        nombre_archivo = request_data.get("nombre_archivo")
        comentario_validacion = request_data.get("comentario_validacion")
        
        if not nombre_archivo:
            raise HTTPException(
                status_code=400,
                detail="El campo 'nombre_archivo' es requerido en el body del request"
            )
        
        print(f"Archivo a validar: {nombre_archivo}")
        
        # Importar la nueva función
        from src.AnalisisQuimicosValidados.application.quimicos_validados_service import (
            validar_analisis_por_correo_y_archivo
        )
        
        # Validar análisis del usuario con archivo específico
        resultado = validar_analisis_por_correo_y_archivo(
            correo_usuario, nombre_archivo, comentario_validacion, db
        )
        
        if resultado["success"] and resultado["validados"] > 0:
            print(f"✅ PROCESO COMPLETADO EXITOSAMENTE:")
            print(f"   - Usuario: {correo_usuario}")
            print(f"   - Archivo: {nombre_archivo}")
            print(f"   - Análisis validados: {resultado['validados']}")
            print(f"   - Registros eliminados: {resultado.get('eliminados', 0)}")
            print(f"   - Asignados a Administrador ID: {resultado['administrador_id']}")
            
            # Respuesta simple como solicitaste
            return {"status": "validado"}
            
        elif not resultado["success"] and "no tiene análisis pendientes" in resultado["message"]:
            print(f"ℹ️  No hay pendientes para el archivo: {nombre_archivo}")
            return {"status": "sin_pendientes"}
            
        elif not resultado["success"] and "no encontrado" in resultado["message"]:
            print(f"❌ Usuario no encontrado: {correo_usuario}")
            raise HTTPException(
                status_code=404,
                detail=f"Usuario con correo '{correo_usuario}' no encontrado"
            )
            
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

# Opcionalmente, puedes agregar un endpoint alernativo con query parameters
@router.post("/validar-simple-query/{correo_usuario}/")
def validar_usuario_simple_query(
    correo_usuario: str,
    nombre_archivo: str = Query(..., description="Nombre del archivo a validar"),
    comentario_validacion: Optional[str] = Query(None, description="Comentario opcional"),
    db: Session = Depends(get_db)
):
    """
    Endpoint alternativo que valida análisis pendientes usando query parameters.
    Ejemplo: /validar-simple-query/usuario@email.com/?nombre_archivo=datos.xlsx&comentario_validacion=ok
    """
    try:
        print(f"=== VALIDACIÓN CON QUERY PARAMS ===")
        print(f"Usuario: {correo_usuario}, Archivo: {nombre_archivo}")
        
        # Importar la función
        from src.AnalisisQuimicosValidados.application.quimicos_validados_service import (
            validar_analisis_por_correo_y_archivo
        )
        
        # Validar análisis
        resultado = validar_analisis_por_correo_y_archivo(
            correo_usuario, nombre_archivo, comentario_validacion, db
        )
        
        if resultado["success"] and resultado["validados"] > 0:
            return {"status": "validado"}
        elif not resultado["success"] and "no tiene análisis pendientes" in resultado["message"]:
            return {"status": "sin_pendientes"}
        elif not resultado["success"] and "no encontrado" in resultado["message"]:
            raise HTTPException(status_code=404, detail=resultado["message"])
        else:
            raise HTTPException(status_code=400, detail=resultado["message"])
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"✗ Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al validar análisis: {str(e)}"
        )
        

@router.delete("/usuario/{correo_usuario}/validados/")
def eliminar_validados_usuario_por_archivo(
    correo_usuario: str,
    request_data: dict,  # Recibe datos en el body
    db: Session = Depends(get_db)
):
    """
    Elimina análisis químicos validados de un usuario por correo Y nombre de archivo específico.
    Requiere ID de administrador para autorizar la eliminación.
    
    Args:
        correo_usuario (str): Correo electrónico del usuario
        request_data (dict): Body del request con formato:
            {
                "nombre_archivo": "archivo.xlsx",
                "admin_id": 1,
                "user_id_objetivo": 1  # Opcional: ID específico del usuario propietario de los registros
            }
        
    Returns:
        dict: Resultado de la eliminación
        
    Raises:
        HTTPException: Si ocurre un error durante la eliminación
    """
    try:
        print(f"=== ENDPOINT DELETE VALIDADOS CON ADMIN PARA: {correo_usuario} ===")
        
        # Obtener datos del request body
        nombre_archivo = request_data.get("nombre_archivo")
        admin_id = request_data.get("admin_id")
        user_id_objetivo = request_data.get("user_id_objetivo")  # Opcional
        
        if not nombre_archivo:
            raise HTTPException(
                status_code=400,
                detail="El campo 'nombre_archivo' es requerido en el body del request"
            )
            
        if not admin_id:
            raise HTTPException(
                status_code=400,
                detail="El campo 'admin_id' es requerido para autorizar la eliminación"
            )
        
        print(f"Archivo a eliminar: {nombre_archivo}")
        print(f"Admin ID: {admin_id}")
        print(f"User ID objetivo: {user_id_objetivo}")
        
        # Llamar al servicio de eliminación con admin
        resultado = eliminar_analisis_validados_con_admin(
            correo_usuario, 
            nombre_archivo, 
            admin_id,
            db,
            user_id_objetivo
        )
        
        if not resultado["success"]:
            if "no autorizado" in resultado["message"]:
                raise HTTPException(status_code=403, detail=resultado["message"])
            elif "no encontrado" in resultado["message"]:
                raise HTTPException(status_code=404, detail=resultado["message"])
            else:
                status_code = 400 if "no tiene análisis validados" in resultado["message"] else 500
                raise HTTPException(status_code=status_code, detail=resultado["message"])
        
        # Eliminación exitosa
        print(f"✅ Eliminación exitosa: {resultado['eliminados']} registros")
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error crítico en endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar análisis validados del usuario: {str(e)}"
        )
        
@router.delete("/usuario/{correo_usuario}/pendientes/archivo/")
def eliminar_pendientes_por_archivo(
    correo_usuario: str,
    request_data: dict,
    db: Session = Depends(get_db)
):
    """
    Elimina análisis pendientes de un usuario por correo y nombre de archivo específico.
    
    Body esperado:
    {
        "nombre_archivo": "archivo.xlsx"
    }
    """
    try:
        nombre_archivo = request_data.get("nombre_archivo")
        
        if not nombre_archivo:
            raise HTTPException(
                status_code=400,
                detail="El campo 'nombre_archivo' es requerido"
            )
        
        resultado = eliminar_analisis_pendientes_por_archivo(correo_usuario, nombre_archivo, db)
        
        if not resultado["success"] and "no encontrado" in resultado["message"]:
            raise HTTPException(status_code=404, detail=resultado["message"])
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar análisis pendientes: {str(e)}"
        )

@router.get("/usuario/{correo_usuario}/validados/")
def obtener_validados_por_usuario(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los análisis validados de un usuario agrupados por archivo.
    """
    try:
        resultado = obtener_analisis_validados_agrupados_por_usuario(correo_usuario, db)
        
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
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener análisis validados: {str(e)}"
        )