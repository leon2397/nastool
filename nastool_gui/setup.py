# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name="nastool-gui",
    version="1.0.0",
    description="CustomTkinter GUI for NASTool",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "nastool-core>=1.0.0",
        "nastool-fixes>=1.0.0",
        "nastool-reporters>=1.0.0",
        "nastool-adapters>=1.0.0",
    ],
)
