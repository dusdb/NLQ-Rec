# test_settings.py (Backend 폴더)

from app.config.settings import get_settings

settings = get_settings()

print("📋 설정 확인:\n")
print(f"POSTGRES_HOST: {settings.POSTGRES_HOST}")
print(f"POSTGRES_PORT: {settings.POSTGRES_PORT}")
print(f"POSTGRES_DB: {settings.POSTGRES_DB}")
print(f"POSTGRES_USER: {settings.POSTGRES_USER}")
print(f"POSTGRES_PASSWORD: {settings.POSTGRES_PASSWORD[:10]}...")
print(f"\nANTHROPIC_API_KEY: {settings.anthropic_api_key[:20]}...")