# app/api/v1/endpoints/__init__.py
"""
API 엔드포인트 모듈
"""
from .debug import router as debug_router
from .health import router as health_router

__all__ = ['debug_router', 'health_router']