#!/usr/bin/env python

import setuptools

setuptools.setup(
    name="sphinxcontrib-yamcs",
    version="1.2.3",
    license="BSD",
    description="Sphinx extensions for use within the Yamcs project.",
    author="Space Applications Services",
    author_email="yamcs@spaceapplications.com",
    url="https://github.com/yamcs/sphinxcontrib-yamcs",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    namespace_packages=["sphinxcontrib"],
    include_package_data=True,
    install_requires=["yamcs-client", "Sphinx>=4.0.0", "pyyaml"],
    python_requires=">=3.6",
    zip_safe=False,
    platforms="any",
    classifiers=[
        "Framework :: Sphinx :: Extension",
        "Intended Audience :: Developers",
    ],
)
