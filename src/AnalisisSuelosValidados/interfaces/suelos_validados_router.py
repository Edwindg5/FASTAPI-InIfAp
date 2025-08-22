# src/AnalisisSuelosValidados/interfaces/suelos_validados_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, EmailStr
from src.core.database import get_db
from src.AnalisisSuelosValidados.application.analisis_suelos_validados_service import AnalisisSuelosValidadosService

router = APIRouter(
    prefix="/api/v1/suelos-validados",
    tags=["Análisis de Suelos Validados"]
)

# Schemas
class ValidarPorCorreoRequest(BaseModel):
    correo_usuario: EmailStr

class ValidarPorCorreoResponse(BaseModel):
    success: bool
    message: str
    validados: int = None
    usuario: dict = None

class AnalisisSuelosValidadosResponse(BaseModel):
    id: int
    municipio_cuadernillo: str = None
    localidad_cuadernillo: str = None
    nombre_productor: str = None
    nombre_tecnico: str = None
    cultivo_anterior: str = None
    cultivo_establecer: str = None
    fecha_muestreo: str = None
    fecha_validacion: str = None
    fecha_creacion: str = None
    
    class Config:
        from_attributes = True



class AnalisisSuelosPendientesResponse(BaseModel):
    id: int
    municipio_cuadernillo: str = None
    localidad_cuadernillo: str = None
    nombre_productor: str = None  # ✅ Ya estaba correcto
    nombre_tecnico: str = None    # ✅ Ya estaba correcto
    cultivo_anterior: str = None
    cultivo_establecer: str = None
    fecha_muestreo: str = None
    fecha_creacion: str = None
    correo_tecnico: str = None
    tel_tecnico: str = None
    correo_productor: str = None  # ✅ Ya estaba correcto
    tel_productor: str = None     # ✅ Ya estaba correcto
    coordenada_x: str = None
    coordenada_y: str = None
    elevacion_msnm: int = None
    profundidad_muestreo: str = None
    parcela: str = None           # ✅ Ya estaba correcto
    manejo: str = None            # ✅ Ya estaba correcto
    tipo_vegetacion: str = None   # ✅ Ya estaba correcto
    muestra: str = None
    reemplazo: str = None         # ✅ Ya estaba correcto
    nombre_revisor: str = None    # ✅ Ya estaba correcto
    ddr: str = None
    cader: str = None
    usuario_correo: str = None
    usuario_nombre: str = None
    usuario_apellido: str = None
    
    class Config:
        from_attributes = True

class EstadisticasResponse(BaseModel):
    total_validados: int
    por_municipio: List[dict]

# Endpoints existentes
@router.post("/validar-por-correo", response_model=ValidarPorCorreoResponse)
def validar_analisis_por_correo(
    request: ValidarPorCorreoRequest,
    db: Session = Depends(get_db)
):
    """
    Valida todos los análisis pendientes de un usuario específico por su correo.
    Mueve los datos a la tabla validados y los elimina de pendientes.
    """
    service = AnalisisSuelosValidadosService(db)
    resultado = service.validar_analisis_por_correo(request.correo_usuario)
    
    if not resultado["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=resultado["message"]
        )
    
    return ValidarPorCorreoResponse(
        success=resultado["success"],
        message=resultado["message"],
        validados=resultado.get("validados"),
        usuario=resultado.get("usuario")
    )

@router.get("/todos", response_model=List[AnalisisSuelosValidadosResponse])
def obtener_todos_validados(db: Session = Depends(get_db)):
    """
    Obtiene todos los análisis de suelos validados.
    """
    service = AnalisisSuelosValidadosService(db)
    validados = service.obtener_todos_validados()
    
    return [
        AnalisisSuelosValidadosResponse(
            id=v.id,
            municipio_cuadernillo=v.municipio_cuadernillo,
            localidad_cuadernillo=v.localidad_cuadernillo,
            nombre_productor=v.nombre_productor,
            nombre_tecnico=v.nombre_tecnico,
            cultivo_anterior=v.cultivo_anterior,
            cultivo_establecer=v.cultivo_establecer,
            fecha_muestreo=str(v.fecha_muestreo) if v.fecha_muestreo else None,
            fecha_validacion=str(v.fecha_validacion) if v.fecha_validacion else None,
            fecha_creacion=str(v.fecha_creacion) if v.fecha_creacion else None
        )
        for v in validados
    ]

@router.get("/por-correo/{correo_usuario}", response_model=List[AnalisisSuelosValidadosResponse])
def obtener_validados_por_correo(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los análisis validados de un usuario específico por su correo.
    """
    service = AnalisisSuelosValidadosService(db)
    validados = service.obtener_validados_por_correo(correo_usuario)
    
    if not validados:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron análisis validados para este usuario"
        )
    
    return [
        AnalisisSuelosValidadosResponse(
            id=v.id,
            municipio_cuadernillo=v.municipio_cuadernillo,
            localidad_cuadernillo=v.localidad_cuadernillo,
            nombre_productor=v.nombre_productor,
            nombre_tecnico=v.nombre_tecnico,
            cultivo_anterior=v.cultivo_anterior,
            cultivo_establecer=v.cultivo_establecer,
            fecha_muestreo=str(v.fecha_muestreo) if v.fecha_muestreo else None,
            fecha_validacion=str(v.fecha_validacion) if v.fecha_validacion else None,
            fecha_creacion=str(v.fecha_creacion) if v.fecha_creacion else None
        )
        for v in validados
    ]

# NUEVOS ENDPOINTS PARA PENDIENTES

@router.get("/pendientes/todos", response_model=List[AnalisisSuelosPendientesResponse])
def obtener_todos_pendientes(db: Session = Depends(get_db)):
    """
    Obtiene todos los análisis de suelos pendientes de todos los usuarios.
    """
    try:
        service = AnalisisSuelosValidadosService(db)
        pendientes = service.obtener_todos_pendientes()
        
        # Debug: imprimir algunos valores para ver qué está pasando
        if pendientes:
            print("=== DEBUG INFO ===")
            primer_analisis = pendientes[0]["analisis"]
            print(f"nombre_productor: {primer_analisis.nombre_productor} (tipo: {type(primer_analisis.nombre_productor)})")
            print(f"nombre_tecnico: {primer_analisis.nombre_tecnico} (tipo: {type(primer_analisis.nombre_tecnico)})")
            print(f"correo_productor: {primer_analisis.correo_productor} (tipo: {type(primer_analisis.correo_productor)})")
            print("==================")
        
        resultado = []
        for p in pendientes:
            try:
                # Crear el objeto con manejo de valores None
                item = AnalisisSuelosPendientesResponse(
                    id=p["analisis"].id,
                    municipio_cuadernillo=p["analisis"].municipio_cuadernillo,
                    localidad_cuadernillo=p["analisis"].localidad_cuadernillo,
                    nombre_productor=p["analisis"].nombre_productor,
                    nombre_tecnico=p["analisis"].nombre_tecnico,
                    cultivo_anterior=p["analisis"].cultivo_anterior,
                    cultivo_establecer=p["analisis"].cultivo_establecer,
                    fecha_muestreo=str(p["analisis"].fecha_muestreo) if p["analisis"].fecha_muestreo else None,
                    fecha_creacion=str(p["analisis"].fecha_creacion) if p["analisis"].fecha_creacion else None,
                    correo_tecnico=p["analisis"].correo_tecnico,
                    tel_tecnico=p["analisis"].tel_tecnico,
                    correo_productor=p["analisis"].correo_productor,
                    tel_productor=p["analisis"].tel_productor,
                    coordenada_x=p["analisis"].coordenada_x,
                    coordenada_y=p["analisis"].coordenada_y,
                    elevacion_msnm=p["analisis"].elevacion_msnm,
                    profundidad_muestreo=p["analisis"].profundidad_muestreo,
                    parcela=p["analisis"].parcela,
                    manejo=p["analisis"].manejo,
                    tipo_vegetacion=p["analisis"].tipo_vegetacion,
                    muestra=p["analisis"].muestra,
                    reemplazo=p["analisis"].reemplazo,
                    nombre_revisor=p["analisis"].nombre_revisor,
                    ddr=p["analisis"].ddr,
                    cader=p["analisis"].cader,
                    usuario_correo=p["usuario"].correo if p["usuario"] else None,
                    usuario_nombre=p["usuario"].nombre if p["usuario"] else None,
                    usuario_apellido=p["usuario"].apellido if p["usuario"] else None
                )
                resultado.append(item)
            except Exception as item_error:
                print(f"Error creando item para análisis ID {p['analisis'].id}: {str(item_error)}")
                print(f"Datos problemáticos:")
                print(f"  - nombre_productor: {p['analisis'].nombre_productor}")
                print(f"  - nombre_tecnico: {p['analisis'].nombre_tecnico}")
                print(f"  - correo_productor: {p['analisis'].correo_productor}")
                # Continuar con el siguiente item
                continue
        
        return resultado
        
    except Exception as e:
        print(f"Error general en obtener_todos_pendientes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener análisis pendientes: {str(e)}"
        )
        
        
@router.get("/pendientes/por-correo/{correo_usuario}", response_model=List[AnalisisSuelosPendientesResponse])
def obtener_pendientes_por_correo_json(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene todos los análisis pendientes de un usuario específico por su correo (JSON).
    """
    service = AnalisisSuelosValidadosService(db)
    pendientes = service.obtener_pendientes_por_correo(correo_usuario)
    
    if not pendientes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron análisis pendientes para este usuario"
        )
    
    return [
        AnalisisSuelosPendientesResponse(
            id=p["analisis"].id,
            municipio_cuadernillo=p["analisis"].municipio_cuadernillo,
            localidad_cuadernillo=p["analisis"].localidad_cuadernillo,
            nombre_productor=p["analisis"].nombre_productor,
            nombre_tecnico=p["analisis"].nombre_tecnico,
            cultivo_anterior=p["analisis"].cultivo_anterior,
            cultivo_establecer=p["analisis"].cultivo_establecer,
            fecha_muestreo=str(p["analisis"].fecha_muestreo) if p["analisis"].fecha_muestreo else None,
            fecha_creacion=str(p["analisis"].fecha_creacion) if p["analisis"].fecha_creacion else None,
            correo_tecnico=p["analisis"].correo_tecnico,
            tel_tecnico=p["analisis"].tel_tecnico,
            correo_productor=p["analisis"].correo_productor,
            tel_productor=p["analisis"].tel_productor,
            coordenada_x=p["analisis"].coordenada_x,
            coordenada_y=p["analisis"].coordenada_y,
            elevacion_msnm=p["analisis"].elevacion_msnm,
            profundidad_muestreo=p["analisis"].profundidad_muestreo,
            parcela=p["analisis"].parcela,
            manejo=p["analisis"].manejo,
            tipo_vegetacion=p["analisis"].tipo_vegetacion,
            muestra=p["analisis"].muestra,
            reemplazo=p["analisis"].reemplazo,
            nombre_revisor=p["analisis"].nombre_revisor,
            ddr=p["analisis"].ddr,
            cader=p["analisis"].cader,
            usuario_correo=p["usuario"].correo if p["usuario"] else None,
            usuario_nombre=p["usuario"].nombre if p["usuario"] else None,
            usuario_apellido=p["usuario"].apellido if p["usuario"] else None
        )
        for p in pendientes
    ]

@router.get("/pendientes/vista/{correo_usuario}", response_class=HTMLResponse)
def ver_pendientes_por_correo_html(
    correo_usuario: str,
    db: Session = Depends(get_db)
):
    """
    Vista HTML para mostrar todos los análisis pendientes de un usuario específico.
    Este endpoint abre una nueva pestaña del navegador con una tabla estilizada.
    """
    service = AnalisisSuelosValidadosService(db)
    pendientes = service.obtener_pendientes_por_correo(correo_usuario)
    
    if not pendientes:
        html_content = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Análisis Pendientes - {correo_usuario}</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 15px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    padding: 30px;
                    text-align: center;
                }}
                .error-message {{
                    color: #e74c3c;
                    font-size: 18px;
                    margin: 20px 0;
                }}
                .user-info {{
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 10px;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📋 Análisis de Suelos Pendientes</h1>
                <div class="user-info">
                    <h3>Usuario: {correo_usuario}</h3>
                </div>
                <div class="error-message">
                    ❌ No se encontraron análisis pendientes para este usuario.
                </div>
                <button onclick="window.close()" style="
                    background: #3498db;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                    margin-top: 20px;
                ">Cerrar</button>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    
    # Generar tabla HTML con los datos
    usuario_info = pendientes[0]["usuario"] if pendientes else None
    
    filas_html = ""
    for i, p in enumerate(pendientes, 1):
        analisis = p["analisis"]
        filas_html += f"""
        <tr>
            <td>{i}</td>
            <td>{analisis.municipio_cuadernillo or 'N/A'}</td>
            <td>{analisis.localidad_cuadernillo or 'N/A'}</td>
            <td>{analisis.nombre_productor or 'N/A'}</td>
            <td>{analisis.nombre_tecnico or 'N/A'}</td>
            <td>{analisis.cultivo_anterior or 'N/A'}</td>
            <td>{analisis.cultivo_establecer or 'N/A'}</td>
            <td>{str(analisis.fecha_muestreo) if analisis.fecha_muestreo else 'N/A'}</td>
            <td>{analisis.correo_tecnico or 'N/A'}</td>
            <td>{analisis.tel_tecnico or 'N/A'}</td>
            <td>{analisis.correo_productor or 'N/A'}</td>
            <td>{analisis.tel_productor or 'N/A'}</td>
            <td>{analisis.coordenada_x or 'N/A'}</td>
            <td>{analisis.coordenada_y or 'N/A'}</td>
            <td>{analisis.elevacion_msnm or 'N/A'}</td>
            <td>{analisis.profundidad_muestreo or 'N/A'}</td>
            <td>{analisis.parcela or 'N/A'}</td>
            <td>{analisis.manejo or 'N/A'}</td>
            <td>{analisis.tipo_vegetacion or 'N/A'}</td>
            <td>{analisis.ddr or 'N/A'}</td>
            <td>{analisis.cader or 'N/A'}</td>
            <td>{str(analisis.fecha_creacion) if analisis.fecha_creacion else 'N/A'}</td>
        </tr>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Análisis Pendientes - {correo_usuario}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }}
            .container {{
                background: white;
                border-radius: 15px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                padding: 30px;
                margin: 0 auto;
                max-width: 98%;
                overflow-x: auto;
            }}
            h1 {{
                text-align: center;
                color: #2c3e50;
                margin-bottom: 10px;
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
            }}
            .user-info {{
                background: linear-gradient(45deg, #3498db, #2ecc71);
                color: white;
                padding: 15px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: center;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }}
            .stats {{
                text-align: center;
                margin: 20px 0;
                color: #7f8c8d;
                font-size: 18px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            th {{
                background: linear-gradient(45deg, #34495e, #2c3e50);
                color: white;
                padding: 15px 10px;
                text-align: left;
                font-weight: 600;
                font-size: 14px;
                position: sticky;
                top: 0;
                z-index: 10;
            }}
            td {{
                padding: 12px 10px;
                border-bottom: 1px solid #ecf0f1;
                font-size: 13px;
                word-wrap: break-word;
                max-width: 200px;
            }}
            tr:nth-child(even) {{
                background: #f8f9fa;
            }}
            tr:hover {{
                background: #e3f2fd;
                transition: all 0.3s ease;
            }}
            .actions {{
                text-align: center;
                margin: 30px 0;
            }}
            button {{
                background: linear-gradient(45deg, #e74c3c, #c0392b);
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                margin: 0 10px;
            }}
            button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 7px 20px rgba(0,0,0,0.3);
            }}
            .btn-print {{
                background: linear-gradient(45deg, #27ae60, #2ecc71);
            }}
            .table-wrapper {{
                overflow-x: auto;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }}
            @media print {{
                body {{ background: white; }}
                .container {{ box-shadow: none; }}
                button {{ display: none; }}
            }}
            @media (max-width: 768px) {{
                body {{ padding: 10px; }}
                .container {{ padding: 15px; }}
                h1 {{ font-size: 2em; }}
                th, td {{ padding: 8px 5px; font-size: 12px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📋 Análisis de Suelos Pendientes</h1>
            
            <div class="user-info">
                <h3>👤 Usuario: {usuario_info.correo if usuario_info else correo_usuario}</h3>
                {f"<p><strong>Nombre:</strong> {usuario_info.nombre} {usuario_info.apellido}</p>" if usuario_info and usuario_info.nombre else ""}
            </div>
            
            <div class="stats">
                📊 Total de análisis pendientes: <strong>{len(pendientes)}</strong>
            </div>
            
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Municipio</th>
                            <th>Localidad</th>
                            <th>Productor</th>
                            <th>Técnico</th>
                            <th>Cultivo Anterior</th>
                            <th>Cultivo a Establecer</th>
                            <th>Fecha Muestreo</th>
                            <th>Email Técnico</th>
                            <th>Tel. Técnico</th>
                            <th>Email Productor</th>
                            <th>Tel. Productor</th>
                            <th>Coordenada X</th>
                            <th>Coordenada Y</th>
                            <th>Elevación (msnm)</th>
                            <th>Profundidad</th>
                            <th>Parcela</th>
                            <th>Manejo</th>
                            <th>Tipo Vegetación</th>
                            <th>DDR</th>
                            <th>CADER</th>
                            <th>Fecha Creación</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filas_html}
                    </tbody>
                </table>
            </div>
            
            <div class="actions">
                <button class="btn-print" onclick="window.print()">🖨️ Imprimir</button>
                <button onclick="window.close()">✖️ Cerrar</button>
            </div>
        </div>
        
        <script>
            // Auto-ajustar el tamaño de la ventana si es necesario
            window.addEventListener('load', function() {{
                if (window.outerWidth < 1200) {{
                    window.resizeTo(1200, window.outerHeight);
                }}
            }});
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

# ENDPOINTS ADICIONALES PARA ESTADÍSTICAS

class ConteoUsuariosResponse(BaseModel):
    correo: str
    nombre: str = None
    apellido: str = None
    total_pendientes: int

class EstadisticasPendientesResponse(BaseModel):
    total_pendientes: int
    usuarios_con_pendientes: int
    por_municipio: List[dict]

@router.get("/pendientes/conteo-por-usuario", response_model=List[ConteoUsuariosResponse])
def obtener_conteo_pendientes_por_usuario(db: Session = Depends(get_db)):
    """
    Obtiene el conteo de análisis pendientes agrupados por usuario.
    Útil para mostrar un resumen de cuántos análisis tiene cada usuario pendiente.
    """
    service = AnalisisSuelosValidadosService(db)
    conteos = service.contar_pendientes_por_usuario()
    
    return [
        ConteoUsuariosResponse(
            correo=c["correo"],
            nombre=c["nombre"],
            apellido=c["apellido"],
            total_pendientes=c["total_pendientes"]
        )
        for c in conteos
    ]

@router.get("/estadisticas/pendientes", response_model=EstadisticasPendientesResponse)
def obtener_estadisticas_pendientes(db: Session = Depends(get_db)):
    """
    Obtiene estadísticas generales de los análisis pendientes.
    """
    service = AnalisisSuelosValidadosService(db)
    estadisticas = service.obtener_estadisticas_pendientes()
    
    return EstadisticasPendientesResponse(
        total_pendientes=estadisticas["total_pendientes"],
        usuarios_con_pendientes=estadisticas["usuarios_con_pendientes"],
        por_municipio=estadisticas["por_municipio"]
    )

@router.get("/estadisticas/validados", response_model=EstadisticasResponse)
def obtener_estadisticas_validados(db: Session = Depends(get_db)):
    """
    Obtiene estadísticas generales de los análisis validados.
    """
    service = AnalisisSuelosValidadosService(db)
    estadisticas = service.obtener_estadisticas_validados()
    
    return EstadisticasResponse(
        total_validados=estadisticas["total_validados"],
        por_municipio=estadisticas["por_municipio"]
    )