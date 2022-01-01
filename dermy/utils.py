from pathlib import Path

__all__ = [
    'bump_version',
    'get_image',
    'dag_templating',
    'pipe_templating',
]

# ----- Constants ---------------------------------------------------------------------------------------------------- #
DOCKER_TEMPLATE = """FROM python:3.7-slim AS base
FROM base AS builder

COPY requirements.txt .
RUN pip install -r requirements.txt
"""

IGNORE_TEMPLATE = """**
!**/*.py
"""

TAG_TEMPLATE = """0.0.0"""

MANIFEST_TEMPLATE = """---
pipeline:
  name: {name}{description}
input:
  pfs:
    repo: {repo}
    glob: /*
    name: data
transform:
  image: {image}
  cmd:
    - python3
    - {cmd}
"""

TRANSFORM_TEMPLATE = """import logging
import os
from pathlib import Path

# ----- Logging Setup ------------------------------------------------------------------------------------------------ #
logging.basicConfig(
    level=logging.DEBUG,
    format='%(name)s - %(asctime)s.%(msecs)03d - %(levelname)s - %(module)s.%(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ----- Environment Variables ---------------------------------------------------------------------------------------- #
INPUT = os.environ.get('data')
OUTPUT = os.environ.get('OUTPUT', '/pfs/out')


# ----- Script ------------------------------------------------------------------------------------------------------- #
def main():
    input_path = Path(INPUT)
    output_path = Path(OUTPUT)
    
    logging.debug(f'input path: {input_path}')
    logging.debug(f'output path: {output_path}')
    

if __name__ == '__main__':
    main()"""


# ----- Helper Functions --------------------------------------------------------------------------------------------- #
def bump_version(version: str) -> str:
    a, b, c = map(int, version.split('.'))

    if all(part == 0 for part in [a, b, c]):
        return '0.1.0'

    c += 1
    if c == 10:
        b += 1
        c = 0

    if b == 10:
        a += 1
        b = 0

    out = '.'.join(map(str, [a, b, c]))
    return out


def get_image(directory: Path) -> str:
    tag = (directory / '.tag').read_text()

    image = f'{directory.name}:{tag}'
    return image


def create_template(path: Path, template: str, **kwargs):
    with path.open(mode='w') as file:
        file.write(template.format(**kwargs))


# ----- DAG templating ----------------------------------------------------------------------------------------------- #
def create_docker_file(directory: Path):
    create_template(directory / 'Dockerfile', DOCKER_TEMPLATE)


def create_docker_ignore(directory: Path):
    create_template(directory / '.dockerignore', IGNORE_TEMPLATE)


def create_tag_file(directory: Path):
    create_template(directory / '.tag', TAG_TEMPLATE)


def create_requirements(directory: Path):
    create_template(directory / 'requirements.txt', """""")


dag_templating = [
    create_docker_file,
    create_docker_ignore,
    create_tag_file,
    create_requirements
]


# ----- PIPE templating ---------------------------------------------------------------------------------------------- #
def create_manifest_template(directory: Path, **kwargs):
    create_template(directory / 'manifest.yml', MANIFEST_TEMPLATE, **kwargs)


def create_transform_template(directory: Path, **kwargs):
    create_template(directory / 'transform.py', TRANSFORM_TEMPLATE, **kwargs)


pipe_templating = [
    create_manifest_template,
    create_transform_template
]
