from setuptools import setup, find_packages

setup(
    name="ai-routing-layer",
    version="2.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
)
