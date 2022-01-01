from pathlib import Path

from setuptools import setup, find_packages

DIRNAME = Path(__file__).parent
long_description = (DIRNAME / 'README.md').read_text()

setup(
    name='dermy',
    version='0.1.0',
    description='Convenience CLI for pachyderm.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='benjamin-tenmann',
    author_email='b.tenmann@me.com',
    license='MIT',
    python_requires='>=3.7,<3.10',
    install_requires=[
        'fire>=0.4.0',
        'glom>=20.0.0,<21.0.0',
        'pipreqs>=0.4.0',
        'srsly>=2.0.0,<3.0.0',
    ],
    packages=find_packages(exclude=['tests', 'scripts']),
)
