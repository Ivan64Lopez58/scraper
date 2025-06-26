FROM mcr.microsoft.com/playwright/python:v1.53.0-jammy


# Establece el directorio de trabajo
WORKDIR /app

# Copia primero solo los requirements para aprovechar cacheo
COPY requirements.txt .

# Instala dependencias sin cache
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código
COPY . .

# Expone el puerto del microservicio
EXPOSE 8000

# Comando para iniciar el servidor FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
