"""
Setup configuration for Antonlytics Python SDK.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="antonlytics",
    version="2.2.0",
    author="Voidback",
    author_email="hello@voidback.com",
    description="Memory for AI Agents - Simple natural language SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Voidback-Inc/antonlytics-python-sdk",
    project_urls={
        "Documentation": "https://antonlytics.com/docs/python-sdk",
        "Source": "https://github.com/Voidback-Inc/antonlytics-python-sdk",
        "Bug Reports": "https://github.com/Voidback-Inc/antonlytics-python-sdk/issues",
    },
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "langchain": [
            "langchain-core>=0.2.0",
            "pydantic>=2.0.0",
        ],
    },
    keywords="ai agent memory llm knowledge-graph natural-language",
)
