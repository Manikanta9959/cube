from fastapi import APIRouter
from api_v1.endpoints.review import router as review_router

api_v1_router = APIRouter()

api_v1_router.include_router(prefix = "/review", router=review_router)

