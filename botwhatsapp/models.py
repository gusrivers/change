from sqlalchemy import Column, Integer, String, Float, Date
from database import Base

class Gasto(Base):
    __tablename__ = "gastos"
    id = Column(Integer, primary_key=True, index=True)
    valor = Column(Float, nullable=False)
    categoria = Column(String, nullable=False)
    data = Column(Date, nullable=False)
    usuario_id = Column(String, nullable=False)