import re
from pathlib import Path

import srsly

__all__ = [
    'bump_tag',
    'bump_manifest_tag',
    'get_image',
    'get_repo',
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
!requirements.txt
"""

TAG_TEMPLATE = """0.0.0"""

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
    
    logging.debug(f'input path: {{input_path}}')
    logging.debug(f'output path: {{output_path}}')
    

if __name__ == '__main__':
    main()"""

SYMBOLS = {
    '*': 'cross',
    '+': 'join'
}


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


def bump_tag(directory: Path):
    version = (directory / '.tag').read_text()

    version = bump_version(version)
    with (directory / '.tag').open(mode='w') as file:
        file.write(version)


def bump_manifest_tag(transform: Path):
    directory = transform.parent

    version = (directory / '.tag').read_text()
    manifest = srsly.read_yaml(transform / 'manifest.yml')

    img, *_ = manifest['transform']['image'].split(':')
    manifest['transform']['image'] = f'{img}:{version}'

    srsly.write_yaml(transform / 'manifest.yml', manifest)


def get_image(directory: Path, registry: str) -> str:
    tag = (directory / '.tag').read_text()

    image = f'{registry}{directory.name}:{tag}'
    return image


def get_repo(repo_expression: str) -> dict or list:
    if not repo_expression:
        return format_pfs('<insert repo>', name='data')

    # repo*(repo+repo)
    subsidiarity = re.findall(r"\((.+)\)", repo_expression)

    n_expr = re.sub(r"\(.+\)", '', repo_expression)

    repos = re.findall(r"[^*+()]+", n_expr)
    for sub in subsidiarity:
        repos.append(get_repo(sub))

    symbols = set(re.findall('[*+]', n_expr))
    if len(symbols) == 0:
        return format_pfs(repos[0], name='data')

    if len(symbols) > 1:
        raise ValueError

    symbol, = symbols

    key = SYMBOLS.get(symbol, 'cross')
    out = {
        key: repos
    }
    for i, val in enumerate(out[key]):
        if isinstance(val, dict):
            continue

        out[key][i] = format_pfs(val, join=(key == 'join'))

    return out


def format_pfs(repo: str, name: str = '', join: bool = False):
    out = {
        'pfs': {
            'repo': repo,
            'glob': '/(*)' if join else '/*'
        }
    }
    if name:
        out['pfs']['name'] = name
    if join:
        out['pfs']['join_on'] = "$1"

    return out


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
    out = {'pipeline': {'name': kwargs['name']}}
    if kwargs['description']:
        out['description'] = kwargs['description']

    out['input'] = kwargs['repo']
    out['transform'] = {'image': kwargs['image'], 'cmd': ['python3', kwargs['cmd']]}
    out['autoscaling'] = True

    srsly.write_yaml(directory / 'manifest.yml', out)


def create_transform_template(directory: Path, **kwargs):
    create_template(directory / 'transform.py', TRANSFORM_TEMPLATE, **kwargs)


pipe_templating = [
    create_manifest_template,
    create_transform_template
]
