from setuptools import setup, find_packages

setup(
    name="auto-reporter",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "slack-sdk",
    ],
)
