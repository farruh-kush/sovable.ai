from setuptools import find_packages, setup


setup(
    name="ai-routing-layer",
    version="0.1.0",
    description="Unified AI routing platform with provider abstraction, routing, billing, and observability.",
    package_dir={"": "src"},
    packages=find_packages("src"),
    install_requires=[
        "fastapi>=0.115.0,<1.0.0",
        "uvicorn[standard]>=0.34.0,<1.0.0",
        "httpx>=0.28.0,<1.0.0",
        "pydantic>=2.11.0,<3.0.0",
        "pydantic-settings>=2.8.0,<3.0.0",
        "pyyaml>=6.0.2,<7.0.0",
        "sqlalchemy>=2.0.38,<3.0.0",
        "aiosqlite>=0.21.0,<1.0.0",
        "prometheus-client>=0.21.1,<1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=8.3.5,<9.0.0",
            "pytest-asyncio>=0.26.0,<1.0.0",
            "respx>=0.22.0,<1.0.0",
        ]
    },
)
