from fastapi import FastAPI
from routers import gastos

app = FastAPI()

app.include_router(gastos.router)

@app.get("/")
def read_root():
    return {"message": "Chatbot Financeiro API"}