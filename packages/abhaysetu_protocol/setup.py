from setuptools import find_packages, setup

setup(
    name="abhaysetu-protocol",
    version="1.0.0",
    packages=find_packages(),
    install_requires=["pydantic>=2.6", "pynacl>=1.5"],
)
