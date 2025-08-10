from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import kactus, incapacities

app = FastAPI(title='Incapacidades - Backend')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(kactus.router, prefix='/api/kactus')
app.include_router(incapacities.router, prefix='/api')
