# main.py
from fastapi import FastAPI
from src.core.database import Base, engine
from src.AnalisisQuimicosPendientes.infrastructure.analisis_quimicos_model import AnalisisQuimicosPendientes
from src.AnalisisQuimicosPendientes.interfaces import analisis_quimicos_router
from src.AnalisisSuelosPendientes.infrastructure.analisis_suelos_model import AnalisisSuelosPendientes
from src.AnalisisSuelosPendientes.interfaces import analisis_suelos_router
from src.Users.infrastructure.users_model import Users
from src.municipios.infrastructure.municipios_model import Municipios
from src.municipios.interfaces import municipios_router

# Crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API Análisis de Suelos",
    description="API para gestión de análisis de suelos y análisis químicos",
    version="1.0.0"
)

# Incluir routers
app.include_router(analisis_quimicos_router.router)
app.include_router(analisis_suelos_router.router)
app.include_router(municipios_router.router)

@app.get("/")
def read_root():
    return {"message": "API de Análisis de Suelos - Funcionando correctamente"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API funcionando correctamente"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)