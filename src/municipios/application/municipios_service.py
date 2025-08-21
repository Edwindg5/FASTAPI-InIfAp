# src/municipios/application/municipios_service.py
from sqlalchemy.orm import Session
from src.municipios.infrastructure.municipios_model import Municipios
from src.municipios.application.municipios_schema import MunicipioCreate

def crear_municipio(db: Session, municipio: MunicipioCreate):
    nuevo_municipio = Municipios(
        clave_estado=municipio.clave_estado,
        clave_municipio=municipio.clave_municipio,
        nombre=municipio.nombre
    )
    db.add(nuevo_municipio)
    db.commit()
    db.refresh(nuevo_municipio)
    return nuevo_municipio

def obtener_municipios(db: Session):
    return db.query(Municipios).all()
