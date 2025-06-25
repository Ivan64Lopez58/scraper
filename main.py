from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import asyncio
from scraper import ejecutar_scraping_rapido

app = FastAPI()

class Accion(BaseModel):
    empresa: str
    url: str

@app.post("/scrap")
async def scrap_acciones(acciones: List[Accion]):
    dicts = [accion.dict() for accion in acciones]
    resultados = await ejecutar_scraping_rapido(dicts)
    return resultados
