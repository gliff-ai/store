from setuptools import setup

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(name="etebase-server", install_requires=requirements)
