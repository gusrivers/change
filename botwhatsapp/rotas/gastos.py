from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import Gasto
from database import SessionLocal
from pydantic import BaseModel
from datetime import date

router = APIRouter()

# Dependência para obter a sessão do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Modelo Pydantic para entrada de dados
class GastoCreate(BaseModel):
    valor: float
    categoria: str
    data: date
    usuario_id: str

# Rota para registrar um gasto
@router.post("/gastos/")
def registrar_gasto(gasto: GastoCreate, db: Session = Depends(get_db)):
    db_gasto = Gasto(**gasto.dict())
    db.add(db_gasto)
    db.commit()
    db.refresh(db_gasto)
    return db_gasto

# Rota para listar gastos de um usuário
@router.get("/gastos/{usuario_id}")
def listar_gastos(usuario_id: str, db: Session = Depends(get_db)):
    gastos = db.query(Gasto).filter(Gasto.usuario_id == usuario_id).all()
    return gastos