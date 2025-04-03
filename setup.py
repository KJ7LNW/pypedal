from setuptools import setup, find_packages
import os

# Set umask to get standard permissions (rwxr-xr-x for dirs, rw-r--r-- for files)
os.umask(0o022)

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
    author="Eric Wheeler",
    author_email="pypedal@z.ewheeler.org",
    description="Tool for creating custom foot pedal controls and keyboard/mouse macros",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Topic :: Desktop Environment :: Accessibility",
    ],
)
