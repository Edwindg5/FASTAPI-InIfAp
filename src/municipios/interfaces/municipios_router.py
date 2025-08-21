# src/municipios/interfaces/municipios_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from src.core.database import get_db
from src.municipios.application import municipios_service
from src.municipios.application.municipios_schema import MunicipioCreate, MunicipioResponse

router = APIRouter(prefix="/municipios", tags=["Municipios"])

@router.post("/", response_model=MunicipioResponse)
def crear_municipio(municipio: MunicipioCreate, db: Session = Depends(get_db)):
    return municipios_service.crear_municipio(db, municipio)

@router.get("/", response_model=List[MunicipioResponse])
def listar_municipios(db: Session = Depends(get_db)):
    return municipios_service.obtener_municipios(db)
