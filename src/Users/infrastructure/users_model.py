from sqlalchemy import Column, Integer, String, ForeignKey
from src.core.database import Base

class Users(Base):
    __tablename__ = "users"

    ID_user = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nombre = Column(String(100))
    apellido = Column(String(100))
    correo = Column(String(150), unique=True, nullable=False)
    numero_telefonico = Column(String(20))
    password = Column(String(255))
    rol_id_FK = Column(Integer, ForeignKey("rol.id_rol"))
