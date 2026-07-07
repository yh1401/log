from setuptools import setup

setup(
    name="log_analyzer",
    version="2.5.2",
    description="LLM based large-scale log analyzer and PCAP analysis system.",
    package_dir={"log_analyzer": "."},
    packages=["log_analyzer"],
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        "httpx>=0.25.0",
        "aiofiles>=23.0.0",
        "fastapi>=0.109.0",
        "uvicorn>=0.27.0",
        "python-multipart>=0.0.6",
        "reportlab>=4.0.0",
        "python-docx>=1.1.0",
        "markdown>=3.4.0",
        "weasyprint>=69.0",
        "requests>=2.34.2",
    ],
)
