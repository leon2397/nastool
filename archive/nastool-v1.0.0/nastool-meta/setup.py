from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="nastool",
    version="1.0.0",
    author="NASTool Team",
    author_email="",
    description="NAS System Diagnostic Tool - Comprehensive health checks for ARM-based NAS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nastool/nastool",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Systems Administration",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.8",
    install_requires=[
        "nastool-cli>=1.0.0",
        "nastool-core>=1.0.0",
        "nastool-common>=1.0.0",
        "nastool-adapters>=1.0.0",
        "nastool-reporters>=1.0.0",
        "nastool-fixes>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "nastool=nastool_cli.main:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/nastool/nastool/issues",
        "Source": "https://github.com/nastool/nastool",
    },
)
