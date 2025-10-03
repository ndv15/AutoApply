from setuptools import setup, find_packages

setup(
    name="autoapply",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.111.0",
        "uvicorn==0.30.1",
        "pydantic==2.8.2",
        "pyyaml==6.0.1",
        "requests==2.32.3",
        "python-docx==1.1.2",
        "pdfminer.six==20231228",
        "docx2txt==0.8",
        "jinja2>=3.1.0",
        "pypandoc==1.13",
        "beautifulsoup4==4.12.3",
        "lxml==5.3.0"
    ]
)