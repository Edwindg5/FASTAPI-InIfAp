# main.py
from fastapi import FastAPI
from src.core.database import Base, engine
from src.AnalisisQuimicosPendientes.infrastructure.analisis_quimicos_model import AnalisisQuimicosPendientes
from src.AnalisisQuimicosPendientes.interfaces import analisis_quimicos_router
from src.Users.infrastructure.users_model import Users
from src.municipios.infrastructure.municipios_model import Municipios

# Crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="API Análisis de Suelos")

# Incluir routers
app.include_router(analisis_quimicos_router.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
