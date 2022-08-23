import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="cyber_record",
    version="0.1.5",
    author="daohu527",
    author_email="daohu527@gmail.com",
    description="Cyber record offline parse tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/daohu527/cyber_record",
    project_urls={
        "Bug Tracker": "https://github.com/daohu527/cyber_record/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "."},
    packages=setuptools.find_packages(where="."),
    install_requires=[
        'protobuf>=3.17.0',
    ],
    python_requires=">=3.6",
)
