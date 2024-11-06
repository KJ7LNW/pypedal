from setuptools import setup, find_packages

setup(
    name="pypedal",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",  # For CLI interface
    ],
    entry_points={
        "console_scripts": [
            "pypedal=pypedal.cli:main",
        ],
    },
    author="Evan Wheeler",
    description="A Python-based command line tool",
    python_requires=">=3.6",
)
