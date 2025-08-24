# src/AnalisisQuimicosValidados/application/quimicos_validados_service.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from sqlalchemy import and_
from src.AnalisisQuimicosPendientes.infrastructure.analisis_quimicos_model import (
    AnalisisQuimicosPendientes,
)
from src.AnalisisQuimicosValidados.infrastructure.analisis_quimicos_validados_model import (
    AnalisisQuimicosValidados,
)
from src.Users.infrastructure.users_model import Users

# Importaciones de schemas con manejo de errores
try:
    from src.AnalisisQuimicosValidados.application.quimicos_validados_schema import (
        UserAnalisisResponse,
        AnalisisPendienteResponse,
        ValidacionResponse,
        AnalisisQuimicoValidadoResponse,
    )
except ImportError as e:
    print(f"Error importing schemas: {e}")
    # Definir clases básicas como fallback
    class UserAnalisisResponse:
        pass
    class AnalisisPendienteResponse:
        pass
    class ValidacionResponse:
        pass
    class AnalisisQuimicoValidadoResponse:
        pass

# Constante para el ID del Administrador
ADMINISTRADOR_ID = 1


def obtener_todos_usuarios_con_pendientes(db: Session) -> List[dict]:
    """
    Obtiene todos los usuarios que tienen análisis pendientes.
    Versión mejorada con mejor manejo de errores.
    """
    try:
        print("Iniciando consulta de usuarios con pendientes...")
        
        # Verificar que las tablas existen
        usuarios_con_pendientes = (
            db.query(
                Users.ID_user,
                Users.correo,
                Users.nombre,
                Users.apellido,
                func.count(AnalisisQuimicosPendientes.id).label('total_pendientes')
            )
            .join(
                AnalisisQuimicosPendientes,
                Users.ID_user == AnalisisQuimicosPendientes.user_id_FK
            )
            .filter(AnalisisQuimicosPendientes.estatus == "pendiente")
            .group_by(Users.ID_user, Users.correo, Users.nombre, Users.apellido)
            .order_by(func.count(AnalisisQuimicosPendientes.id).desc())
            .all()
        )
        
        print(f"Encontrados {len(usuarios_con_pendientes)} usuarios con pendientes")
        
        resultado = []
        for usuario in usuarios_con_pendientes:
            try:
                nombre_completo = f"{usuario.nombre or ''} {usuario.apellido or ''}".strip()
                if not nombre_completo:
                    nombre_completo = "Sin nombre"
                
                resultado.append({
                    "user_id": usuario.ID_user,
                    "correo": usuario.correo,
                    "nombre_completo": nombre_completo,
                    "total_pendientes": int(usuario.total_pendientes)
                })
            except Exception as e:
                print(f"Error procesando usuario {usuario.ID_user}: {e}")
                continue
        
        return resultado
        
    except Exception as e:
        print(f"Error en obtener_todos_usuarios_con_pendientes: {e}")
        print(f"Tipo de error: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return []


def obtener_analisis_pendientes_por_usuario(
    correo_usuario: str, db: Session
) -> Optional[dict]:
    """
    Obtiene información simplificada de análisis químicos pendientes de un usuario.
    Solo retorna: nombre_archivo único y cantidad total por archivo.
    """
    try:
        print(f"Buscando pendientes para usuario: {correo_usuario}")
        
        # Buscar usuario por correo
        usuario = db.query(Users).filter(
            Users.correo == correo_usuario.strip().lower()
        ).first()
        
        if not usuario:
            print(f"Usuario no encontrado: {correo_usuario}")
            return None
        
        print(f"Usuario encontrado: {usuario.ID_user}")
        
        # Obtener análisis pendientes agrupados por nombre_archivo
        from sqlalchemy import func
        
        analisis_agrupados = (
            db.query(
                AnalisisQuimicosPendientes.nombre_archivo,
                func.count(AnalisisQuimicosPendientes.id).label('cantidad'),
                func.min(AnalisisQuimicosPendientes.fecha_creacion).label('primera_fecha'),
                func.max(AnalisisQuimicosPendientes.fecha_creacion).label('ultima_fecha')
            )
            .filter(
                AnalisisQuimicosPendientes.user_id_FK == usuario.ID_user,
                AnalisisQuimicosPendientes.estatus == "pendiente"
            )
            .group_by(AnalisisQuimicosPendientes.nombre_archivo)
            .order_by(func.max(AnalisisQuimicosPendientes.fecha_creacion).desc())
            .all()
        )
        
        print(f"Archivos encontrados: {len(analisis_agrupados)}")
        
        # Calcular total de análisis pendientes
        total_pendientes = sum(archivo.cantidad for archivo in analisis_agrupados)
        
        # Convertir a lista de archivos únicos
        archivos_response = []
        for archivo in analisis_agrupados:
            try:
                archivo_dict = {
                    "nombre_archivo": archivo.nombre_archivo or "Sin archivo",
                    "cantidad_analisis": int(archivo.cantidad),
                    "fecha_primer_registro": archivo.primera_fecha.strftime("%Y-%m-%d %H:%M:%S") if archivo.primera_fecha else None,
                    "fecha_ultimo_registro": archivo.ultima_fecha.strftime("%Y-%m-%d %H:%M:%S") if archivo.ultima_fecha else None
                }
                archivos_response.append(archivo_dict)
            except Exception as e:
                print(f"Error procesando archivo {archivo.nombre_archivo}: {e}")
                continue
        
        return {
            "user_id": usuario.ID_user,
            "correo_usuario": usuario.correo,
            "nombre_usuario": f"{usuario.nombre or ''} {usuario.apellido or ''}".strip() or "Sin nombre",
            "total_pendientes": total_pendientes,
            "total_archivos": len(analisis_agrupados),
            "archivos_pendientes": archivos_response
        }
        
    except Exception as e:
        print(f"Error en obtener_analisis_pendientes_por_usuario: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def validar_analisis_quimicos(
    analisis_ids: List[int], 
    comentario_validacion: Optional[str],
    db: Session
) -> dict:
    """
    Valida análisis químicos pendientes, los mueve a la tabla de validados
    y actualiza su estatus. Versión que retorna dict simple.
    """
    validados = 0
    errores = []
    
    try:
        print(f"Iniciando validación de análisis: {analisis_ids}")
        
        # Obtener análisis pendientes
        analisis_pendientes = (
            db.query(AnalisisQuimicosPendientes)
            .filter(
                AnalisisQuimicosPendientes.id.in_(analisis_ids),
                AnalisisQuimicosPendientes.estatus == "pendiente"
            )
            .all()
        )
        
        print(f"Análisis pendientes encontrados: {len(analisis_pendientes)}")
        
        if not analisis_pendientes:
            return {
                "success": False,
                "message": "No se encontraron análisis pendientes con los IDs proporcionados",
                "validados": 0,
                "errores": []
            }
        
        fecha_validacion = datetime.now()
        
        for analisis in analisis_pendientes:
            try:
                # Crear registro en tabla de validados
                analisis_validado = AnalisisQuimicosValidados(
                    municipio_id_FK=analisis.municipio_id_FK,
                    user_id_FK=ADMINISTRADOR_ID,  # CAMBIO: Usar ID del administrador
                    municipio=analisis.municipio,
                    localidad=analisis.localidad,
                    nombre_productor=analisis.nombre_productor,
                    cultivo_anterior=analisis.cultivo_anterior,
                    arcilla=analisis.arcilla,
                    limo=analisis.limo,
                    arena=analisis.arena,
                    textura=analisis.textura,
                    da=analisis.da,
                    ph=analisis.ph,
                    mo=analisis.mo,
                    fosforo=analisis.fosforo,
                    n_inorganico=analisis.n_inorganico,
                    k=analisis.k,
                    mg=analisis.mg,
                    ca=analisis.ca,
                    na=analisis.na,
                    al=analisis.al,
                    cic=analisis.cic,
                    cic_calculada=analisis.cic_calculada,
                    h=analisis.h,
                    azufre=analisis.azufre,
                    hierro=analisis.hierro,
                    cobre=analisis.cobre,
                    zinc=analisis.zinc,
                    manganeso=analisis.manganeso,
                    boro=analisis.boro,
                    columna1=analisis.columna1,
                    columna2=analisis.columna2,
                    ca_mg=analisis.ca_mg,
                    mg_k=analisis.mg_k,
                    ca_k=analisis.ca_k,
                    ca_mg_k=analisis.ca_mg_k,
                    k_mg=analisis.k_mg,
                    fecha_validacion=fecha_validacion,
                    fecha_creacion=analisis.fecha_creacion
                )
                
                db.add(analisis_validado)
                
                # Actualizar estatus en tabla de pendientes
                analisis.estatus = "validado"
                if comentario_validacion:
                    analisis.comentario_invalido = comentario_validacion
                
                validados += 1
                print(f"Análisis {analisis.id} validado exitosamente")
                
            except Exception as e:
                print(f"Error validando análisis {analisis.id}: {e}")
                errores.append({
                    "analisis_id": analisis.id,
                    "error": f"Error al validar análisis {analisis.id}: {str(e)}"
                })
                continue
        
        # Hacer commit si hay validaciones exitosas
        if validados > 0:
            db.commit()
            print(f"Commit exitoso. {validados} análisis validados")
            return {
                "success": True,
                "message": f"Se validaron {validados} análisis exitosamente",
                "validados": validados,
                "errores": errores
            }
        else:
            db.rollback()
            return {
                "success": False,
                "message": "No se pudo validar ningún análisis",
                "validados": 0,
                "errores": errores
            }
            
    except Exception as e:
        print(f"Error general en validación: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        db.rollback()
        return {
            "success": False,
            "message": f"Error general en la validación: {str(e)}",
            "validados": 0,
            "errores": [{"error": f"Error general: {str(e)}"}]
        }






from src.AnalisisQuimicosPendientes.infrastructure.analisis_quimicos_model import AnalisisQuimicosPendientes
from src.AnalisisQuimicosValidados.infrastructure.analisis_quimicos_validados_model import AnalisisQuimicosValidados
from src.Users.infrastructure.users_model import Users

def validar_analisis_por_correo_usuario(
    correo_usuario: str,
    comentario_validacion: Optional[str],
    db: Session
) -> dict:
    """
    Valida todos los análisis pendientes de un usuario por su correo.
    Incluye el campo nombre_archivo en la transferencia.
    
    Args:
        correo_usuario: Correo del usuario
        comentario_validacion: Comentario opcional de validación
        db: Sesión de base de datos
        
    Returns:
        dict: Resultado de la operación con detalles
    """
    try:
        print(f"=== INICIANDO VALIDACIÓN POR CORREO: {correo_usuario} ===")
        
        # 1. Buscar usuario por correo
        usuario = db.query(Users).filter(Users.correo == correo_usuario.strip().lower()).first()
        
        if not usuario:
            return {
                "success": False,
                "message": f"Usuario con correo '{correo_usuario}' no encontrado",
                "validados": 0
            }
        
        print(f"✓ Usuario encontrado: ID {usuario.ID_user}")
        
        # 2. Obtener análisis pendientes del usuario
        analisis_pendientes = db.query(AnalisisQuimicosPendientes).filter(
            and_(
                AnalisisQuimicosPendientes.user_id_FK == usuario.ID_user,
                AnalisisQuimicosPendientes.estatus == "pendiente"
            )
        ).all()
        
        if not analisis_pendientes:
            return {
                "success": True,
                "message": f"Usuario '{correo_usuario}' no tiene análisis pendientes",
                "validados": 0
            }
        
        print(f"✓ Encontrados {len(analisis_pendientes)} análisis pendientes")
        
        # 3. Transferir a tabla de validados
        validados_count = 0
        eliminados_count = 0
        
        for analisis in analisis_pendientes:
            try:
                # Crear registro en tabla de validados incluyendo nombre_archivo
                nuevo_validado = AnalisisQuimicosValidados(
                    municipio_id_FK=analisis.municipio_id_FK,
                    user_id_FK=1,  # Administrador
                    municipio=analisis.municipio,
                    localidad=analisis.localidad,
                    nombre_productor=analisis.nombre_productor,
                    cultivo_anterior=analisis.cultivo_anterior,
                    arcilla=analisis.arcilla,
                    limo=analisis.limo,
                    arena=analisis.arena,
                    textura=analisis.textura,
                    da=analisis.da,
                    ph=analisis.ph,
                    mo=analisis.mo,
                    fosforo=analisis.fosforo,
                    n_inorganico=analisis.n_inorganico,
                    k=analisis.k,
                    mg=analisis.mg,
                    ca=analisis.ca,
                    na=analisis.na,
                    al=analisis.al,
                    cic=analisis.cic,
                    cic_calculada=analisis.cic_calculada,
                    h=analisis.h,
                    azufre=analisis.azufre,
                    hierro=analisis.hierro,
                    cobre=analisis.cobre,
                    zinc=analisis.zinc,
                    manganeso=analisis.manganeso,
                    boro=analisis.boro,
                    columna1=analisis.columna1,
                    columna2=analisis.columna2,
                    ca_mg=analisis.ca_mg,
                    mg_k=analisis.mg_k,
                    ca_k=analisis.ca_k,
                    ca_mg_k=analisis.ca_mg_k,
                    k_mg=analisis.k_mg,
                    # ¡INCLUIR EL CAMPO NOMBRE_ARCHIVO!
                    nombre_archivo=analisis.nombre_archivo,
                    fecha_validacion=datetime.now(),
                    fecha_creacion=analisis.fecha_creacion
                )
                
                db.add(nuevo_validado)
                validados_count += 1
                
                # Eliminar de pendientes
                db.delete(analisis)
                eliminados_count += 1
                
                print(f"✓ Análisis {analisis.id} transferido (archivo: {analisis.nombre_archivo})")
                
            except Exception as e:
                print(f"✗ Error al transferir análisis {analisis.id}: {e}")
                continue
        
        # 4. Confirmar cambios
        db.commit()
        
        print(f"✅ PROCESO COMPLETADO:")
        print(f"   - Validados: {validados_count}")
        print(f"   - Eliminados: {eliminados_count}")
        print(f"   - Asignados a Administrador ID: 1")
        
        return {
            "success": True,
            "message": f"Análisis validados exitosamente para {correo_usuario}",
            "validados": validados_count,
            "eliminados": eliminados_count,
            "administrador_id": 1
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error en validación: {e}")
        return {
            "success": False,
            "message": f"Error al validar análisis: {str(e)}",
            "validados": 0
        }


def obtener_analisis_validados_por_usuario(
    correo_usuario: str, db: Session, limit: int = 50, offset: int = 0
) -> Optional[dict]:
    """
    Obtiene los análisis químicos validados de un usuario por su correo.
    """
    try:
        # Buscar usuario por correo
        usuario = db.query(Users).filter(
            Users.correo == correo_usuario.strip().lower()
        ).first()
        
        if not usuario:
            return None
        
        # Obtener análisis validados del usuario (estos tendrán user_id_FK = 1 del Administrador)
        analisis_validados = (
            db.query(AnalisisQuimicosValidados)
            .filter(AnalisisQuimicosValidados.user_id_FK == ADMINISTRADOR_ID)
            .order_by(AnalisisQuimicosValidados.fecha_validacion.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        # Contar total de análisis validados
        total_validados = (
            db.query(AnalisisQuimicosValidados)
            .filter(AnalisisQuimicosValidados.user_id_FK == ADMINISTRADOR_ID)
            .count()
        )
        
        # Convertir a diccionarios simples
        analisis_response = []
        for analisis in analisis_validados:
            try:
                analisis_dict = {
                    "id": analisis.id,
                    "municipio_id_FK": analisis.municipio_id_FK,
                    "user_id_FK": analisis.user_id_FK,  # Será siempre 1 (Administrador)
                    "municipio": analisis.municipio,
                    "localidad": analisis.localidad,
                    "nombre_productor": analisis.nombre_productor,
                    "ph": float(analisis.ph) if analisis.ph else None,
                    "mo": float(analisis.mo) if analisis.mo else None,
                    "fosforo": float(analisis.fosforo) if analisis.fosforo else None,
                    "fecha_validacion": analisis.fecha_validacion.isoformat() if analisis.fecha_validacion else None,
                    "fecha_creacion": analisis.fecha_creacion.isoformat() if analisis.fecha_creacion else None,
                }
                analisis_response.append(analisis_dict)
            except Exception as e:
                print(f"Error procesando análisis validado {analisis.id}: {e}")
                continue
        
        return {
            "user_id": usuario.ID_user,
            "correo_usuario": usuario.correo,
            "nombre_usuario": f"{usuario.nombre or ''} {usuario.apellido or ''}".strip(),
            "total_validados": total_validados,
            "analisis_validados": analisis_response,
            "administrador_validador_id": ADMINISTRADOR_ID,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        print(f"Error en obtener_analisis_validados_por_usuario: {e}")
        return None
    
    
def eliminar_analisis_validados_por_correo(
    correo_usuario: str,
    db: Session
) -> dict:
    """
    Elimina TODOS los análisis validados asociados a un usuario por su correo.
    Busca todos los registros en analisis_quimicos_validados que tengan user_id_FK = usuario.ID_user
    y los elimina permanentemente.
    
    Args:
        correo_usuario (str): Correo electrónico del usuario
        db (Session): Sesión de base de datos
        
    Returns:
        dict: Resultado de la operación de eliminación
    """
    try:
        print(f"=== ELIMINANDO ANÁLISIS VALIDADOS PARA: {correo_usuario} ===")
        
        # Buscar usuario por correo
        usuario = db.query(Users).filter(
            Users.correo == correo_usuario.strip().lower()
        ).first()
        
        if not usuario:
            print(f"Usuario no encontrado: {correo_usuario}")
            return {
                "success": False,
                "message": f"Usuario con correo '{correo_usuario}' no encontrado",
                "eliminados": 0
            }
        
        print(f"Usuario encontrado: ID={usuario.ID_user}, correo={usuario.correo}")
        
        # Contar cuántos análisis validados tiene el usuario
        total_validados = (
            db.query(AnalisisQuimicosValidados)
            .filter(AnalisisQuimicosValidados.user_id_FK == usuario.ID_user)
            .count()
        )
        
        print(f"Análisis validados encontrados para eliminar: {total_validados}")
        
        if total_validados == 0:
            return {
                "success": True,
                "message": "El usuario no tiene análisis validados para eliminar",
                "usuario": correo_usuario,
                "eliminados": 0
            }
        
        # ELIMINAR todos los análisis validados del usuario
        registros_eliminados = (
            db.query(AnalisisQuimicosValidados)
            .filter(AnalisisQuimicosValidados.user_id_FK == usuario.ID_user)
            .delete(synchronize_session=False)
        )
        
        # Hacer commit de la eliminación
        db.commit()
        
        print(f"✅ ELIMINACIÓN COMPLETADA:")
        print(f"   - Usuario: {correo_usuario} (ID: {usuario.ID_user})")
        print(f"   - Registros eliminados: {registros_eliminados}")
        
        return {
            "success": True,
            "message": f"Se eliminaron {registros_eliminados} análisis validados exitosamente",
            "usuario": correo_usuario,
            "usuario_id": usuario.ID_user,
            "eliminados": registros_eliminados
        }
        
    except Exception as e:
        print(f"❌ Error en eliminación: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        # Rollback en caso de error
        db.rollback()
        return {
            "success": False,
            "message": f"Error al eliminar análisis validados: {str(e)}",
            "usuario": correo_usuario,
            "eliminados": 0,
            "error": str(e)
        }
        
        
def validar_analisis_por_correo_y_archivo(
    correo_usuario: str,
    nombre_archivo: str,
    comentario_validacion: Optional[str],
    db: Session
) -> dict:
    """
    Valida todos los análisis pendientes de un usuario por su correo Y nombre de archivo específico.
    Incluye el campo nombre_archivo en la transferencia.
    
    Args:
        correo_usuario: Correo del usuario
        nombre_archivo: Nombre específico del archivo a validar
        comentario_validacion: Comentario opcional de validación
        db: Sesión de base de datos
        
    Returns:
        dict: Resultado de la operación con detalles
    """
    try:
        print(f"=== INICIANDO VALIDACIÓN POR CORREO Y ARCHIVO ===")
        print(f"Usuario: {correo_usuario}")
        print(f"Archivo: {nombre_archivo}")
        
        # 1. Buscar usuario por correo
        usuario = db.query(Users).filter(Users.correo == correo_usuario.strip().lower()).first()
        
        if not usuario:
            return {
                "success": False,
                "message": f"Usuario con correo '{correo_usuario}' no encontrado",
                "validados": 0
            }
        
        print(f"✓ Usuario encontrado: ID {usuario.ID_user}")
        
        # 2. Obtener análisis pendientes del usuario CON EL NOMBRE DE ARCHIVO ESPECÍFICO
        analisis_pendientes = db.query(AnalisisQuimicosPendientes).filter(
            and_(
                AnalisisQuimicosPendientes.user_id_FK == usuario.ID_user,
                AnalisisQuimicosPendientes.estatus == "pendiente",
                AnalisisQuimicosPendientes.nombre_archivo == nombre_archivo.strip()
            )
        ).all()
        
        if not analisis_pendientes:
            return {
                "success": False,
                "message": f"Usuario '{correo_usuario}' no tiene análisis pendientes con el archivo '{nombre_archivo}'",
                "validados": 0,
                "usuario": correo_usuario,
                "archivo_solicitado": nombre_archivo
            }
        
        print(f"✓ Encontrados {len(analisis_pendientes)} análisis pendientes para el archivo '{nombre_archivo}'")
        
        # 3. Transferir a tabla de validados
        validados_count = 0
        eliminados_count = 0
        
        for analisis in analisis_pendientes:
            try:
                # Crear registro en tabla de validados incluyendo nombre_archivo
                nuevo_validado = AnalisisQuimicosValidados(
                    municipio_id_FK=analisis.municipio_id_FK,
                    user_id_FK=1,  # Administrador
                    municipio=analisis.municipio,
                    localidad=analisis.localidad,
                    nombre_productor=analisis.nombre_productor,
                    cultivo_anterior=analisis.cultivo_anterior,
                    arcilla=analisis.arcilla,
                    limo=analisis.limo,
                    arena=analisis.arena,
                    textura=analisis.textura,
                    da=analisis.da,
                    ph=analisis.ph,
                    mo=analisis.mo,
                    fosforo=analisis.fosforo,
                    n_inorganico=analisis.n_inorganico,
                    k=analisis.k,
                    mg=analisis.mg,
                    ca=analisis.ca,
                    na=analisis.na,
                    al=analisis.al,
                    cic=analisis.cic,
                    cic_calculada=analisis.cic_calculada,
                    h=analisis.h,
                    azufre=analisis.azufre,
                    hierro=analisis.hierro,
                    cobre=analisis.cobre,
                    zinc=analisis.zinc,
                    manganeso=analisis.manganeso,
                    boro=analisis.boro,
                    columna1=analisis.columna1,
                    columna2=analisis.columna2,
                    ca_mg=analisis.ca_mg,
                    mg_k=analisis.mg_k,
                    ca_k=analisis.ca_k,
                    ca_mg_k=analisis.ca_mg_k,
                    k_mg=analisis.k_mg,
                    # ¡INCLUIR EL CAMPO NOMBRE_ARCHIVO!
                    nombre_archivo=analisis.nombre_archivo,
                    fecha_validacion=datetime.now(),
                    fecha_creacion=analisis.fecha_creacion
                )
                
                db.add(nuevo_validado)
                validados_count += 1
                
                # Eliminar de pendientes
                db.delete(analisis)
                eliminados_count += 1
                
                print(f"✓ Análisis {analisis.id} transferido (archivo: {analisis.nombre_archivo})")
                
            except Exception as e:
                print(f"✗ Error al transferir análisis {analisis.id}: {e}")
                continue
        
        # 4. Confirmar cambios
        db.commit()
        
        print(f"✅ PROCESO COMPLETADO:")
        print(f"   - Usuario: {correo_usuario}")
        print(f"   - Archivo: {nombre_archivo}")
        print(f"   - Validados: {validados_count}")
        print(f"   - Eliminados: {eliminados_count}")
        print(f"   - Asignados a Administrador ID: 1")
        
        return {
            "success": True,
            "message": f"Análisis del archivo '{nombre_archivo}' validados exitosamente para {correo_usuario}",
            "validados": validados_count,
            "eliminados": eliminados_count,
            "administrador_id": 1,
            "usuario": correo_usuario,
            "archivo_validado": nombre_archivo
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error en validación: {e}")
        return {
            "success": False,
            "message": f"Error al validar análisis: {str(e)}",
            "validados": 0,
            "usuario": correo_usuario,
            "archivo_solicitado": nombre_archivo,
            "error": str(e)
        }
        
def eliminar_analisis_pendientes_por_archivo(
    correo_usuario: str,
    nombre_archivo: str,
    db: Session
) -> dict:
    """
    Elimina todos los análisis pendientes de un usuario por correo y nombre de archivo específico.
    """
    try:
        print(f"=== ELIMINANDO PENDIENTES POR ARCHIVO ===")
        print(f"Usuario: {correo_usuario}, Archivo: {nombre_archivo}")
        
        # Buscar usuario por correo
        usuario = db.query(Users).filter(
            Users.correo == correo_usuario.strip().lower()
        ).first()
        
        if not usuario:
            return {
                "success": False,
                "message": f"Usuario con correo '{correo_usuario}' no encontrado",
                "eliminados": 0
            }
        
        # Contar análisis pendientes con ese archivo
        total_pendientes = (
            db.query(AnalisisQuimicosPendientes)
            .filter(
                AnalisisQuimicosPendientes.user_id_FK == usuario.ID_user,
                AnalisisQuimicosPendientes.estatus == "pendiente",
                AnalisisQuimicosPendientes.nombre_archivo == nombre_archivo.strip()
            )
            .count()
        )
        
        if total_pendientes == 0:
            return {
                "success": True,
                "message": f"No hay análisis pendientes con el archivo '{nombre_archivo}'",
                "eliminados": 0,
                "usuario": correo_usuario,
                "archivo": nombre_archivo
            }
        
        # Eliminar análisis pendientes
        registros_eliminados = (
            db.query(AnalisisQuimicosPendientes)
            .filter(
                AnalisisQuimicosPendientes.user_id_FK == usuario.ID_user,
                AnalisisQuimicosPendientes.estatus == "pendiente",
                AnalisisQuimicosPendientes.nombre_archivo == nombre_archivo.strip()
            )
            .delete(synchronize_session=False)
        )
        
        db.commit()
        
        print(f"✅ Eliminados {registros_eliminados} análisis pendientes del archivo '{nombre_archivo}'")
        
        return {
            "success": True,
            "message": f"Se eliminaron {registros_eliminados} análisis pendientes exitosamente",
            "usuario": correo_usuario,
            "archivo": nombre_archivo,
            "eliminados": registros_eliminados
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        return {
            "success": False,
            "message": f"Error al eliminar análisis pendientes: {str(e)}",
            "eliminados": 0,
            "error": str(e)
        }
        
        
def obtener_analisis_validados_agrupados_por_usuario(
    correo_usuario: str, db: Session
) -> Optional[dict]:
    """
    Obtiene los análisis validados de un usuario agrupados por nombre de archivo.
    """
    try:
        print(f"Obteniendo validados agrupados para: {correo_usuario}")
        
        # Buscar usuario por correo
        usuario = db.query(Users).filter(
            Users.correo == correo_usuario.strip().lower()
        ).first()
        
        if not usuario:
            return None

        analisis_agrupados = (
            db.query(
                AnalisisQuimicosValidados.nombre_archivo,
                func.count(AnalisisQuimicosValidados.id).label('cantidad'),
                func.min(AnalisisQuimicosValidados.fecha_creacion).label('primera_fecha'),
                func.max(AnalisisQuimicosValidados.fecha_creacion).label('ultima_fecha')
            )
            .filter(AnalisisQuimicosValidados.user_id_FK == 1)  # Administrador
            .group_by(AnalisisQuimicosValidados.nombre_archivo)
            .order_by(func.max(AnalisisQuimicosValidados.fecha_validacion).desc())
            .all()
        )
        
        # Calcular totales
        total_validados = sum(archivo.cantidad for archivo in analisis_agrupados)
        
        # Convertir a lista de archivos únicos
        archivos_response = []
        for archivo in analisis_agrupados:
            try:
                archivo_dict = {
                    "nombre_archivo": archivo.nombre_archivo or "Sin archivo",
                    "cantidad_analisis": int(archivo.cantidad),
                    "fecha_primer_registro": archivo.primera_fecha.strftime("%Y-%m-%d %H:%M:%S") if archivo.primera_fecha else None,
                    "fecha_ultimo_registro": archivo.ultima_fecha.strftime("%Y-%m-%d %H:%M:%S") if archivo.ultima_fecha else None
                }
                archivos_response.append(archivo_dict)
            except Exception as e:
                print(f"Error procesando archivo validado {archivo.nombre_archivo}: {e}")
                continue
        
        return {
            "user_id": usuario.ID_user,
            "correo_usuario": usuario.correo,
            "nombre_usuario": f"{usuario.nombre or ''} {usuario.apellido or ''}".strip() or "Sin nombre",
            "total_validados": total_validados,
            "total_archivos": len(analisis_agrupados),
            "archivos_validados": archivos_response
        }
        
    except Exception as e:
        print(f"Error en obtener_analisis_validados_agrupados_por_usuario: {e}")
        return None
    
