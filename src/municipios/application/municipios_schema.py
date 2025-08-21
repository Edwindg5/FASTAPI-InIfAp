# src/municipios/application/municipios_schema.py
from pydantic import BaseModel
from typing import Optional

class MunicipioCreate(BaseModel):
    clave_estado: Optional[int] = None
    clave_municipio: Optional[int] = None
    nombre: str

class MunicipioResponse(BaseModel):
    id_municipio: int
    clave_estado: Optional[int]
    clave_municipio: Optional[int]
    nombre: str

    class Config:
        orm_mode = True
