from pydantic_settings import BaseSettings


class DockerTestSettings(BaseSettings):
    DATABASE_URL: str = "postgresql://smalda:1234@db:5432/langflow"
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASS: str = "guest"
    API_HOST: str = "localhost"
    API_PORT: int = 8000


docker_settings = DockerTestSettings()
