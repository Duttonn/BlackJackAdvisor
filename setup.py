"""
Blackjack Decision Engine
A professional-grade blackjack decision engine with Hi-Lo counting and Kelly betting.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="blackjack-engine",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Real-time blackjack decision engine with Hi-Lo counting, Illustrious 18/Fab 4 deviations, and Kelly betting",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/blackjack-engine",
    packages=find_packages(include=["src", "src.*", "interfaces", "interfaces.*"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Topic :: Games/Entertainment",
        "Topic :: Scientific/Engineering :: Mathematics",
    ],
    python_requires=">=3.12",
    install_requires=[],  # Pure Python, no external dependencies for core
    extras_require={
        "dev": [
            "pytest>=9.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "blackjack-cli=interfaces.live_api:cli_main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["data/**/*.json"],
    },
)
