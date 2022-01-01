import os
import re
import subprocess
from pathlib import Path

import srsly
from glom import glom, Coalesce

from .utils import (
    bump_tag,
    bump_manifest_tag,
    dag_templating,
    pipe_templating,
    get_image,
    get_repo
)

HOME = os.environ.get('HOME')


class Interface:
    _pachyderm: Path = Path(HOME) / '.pachyderm/config.json'
    assert _pachyderm.exists()

    _config: dict = srsly.read_json(_pachyderm)
    _active_context: str = glom(_config, Coalesce('v1.active_context', 'v2.active_context'))
    _base: list = ['pachctl']

    def __init__(self):
        pass

    def _docker_build(self, directory: Path):
        env = {**os.environ}
        if self._active_context == 'local':
            proc = subprocess.run(['minikube', 'docker-env'], capture_output=True)
            variables = re.findall(r"^export ([A-Z_]+)=\"(.+)\"$", proc.stdout.decode(), re.MULTILINE)

            env = {
                **env,
                **{key: val for key, val in variables}
            }

        subprocess.run(['pipreqs', '--force', directory], check=True)

        bump_tag(directory)
        image = get_image(directory)
        subprocess.run(['docker', 'build', '-t', image, directory], check=True, env=env)

        if self._active_context != 'local':
            # remote registry
            subprocess.run(['docker', 'push', image], check=True, env=env)

    def _create_or_update_pipeline(self, dirname: Path, reprocess: bool):
        out = subprocess.run([*self._base, 'list', 'pipeline'], capture_output=True)

        self._docker_build(dirname.absolute().parent)
        bump_manifest_tag(dirname)
        if dirname.name.encode() in out.stdout:
            # update pipeline branch
            cmd = [*self._base, 'update', 'pipeline', '-f', dirname / 'manifest.yml']
            if reprocess:
                cmd.append('--reprocess')
            subprocess.run(cmd, check=True)

        else:
            # create pipeline branch
            subprocess.run([*self._base, 'create', 'pipeline', '-f', dirname / 'manifest.yml'], check=True)

    def _generate_pipeline_template(self, dirname: Path, description: str, repo: str, image: str):
        # generate pipeline template branch
        dirname.mkdir()

        transform = f'{dirname.name}/transform.py'
        params = {
            'name': dirname.name,
            'description': description,
            'repo': get_repo(repo),
            'image': image if image else get_image(dirname.absolute().parent),
            'cmd': transform
        }
        for template in pipe_templating:
            template(dirname, **params)

        with (dirname.parent / 'Dockerfile').open(mode='a') as file:
            file.write(f'\nCOPY {transform} {dirname.name}/')

        with (dirname.parent / '.dockerignore').open(mode='a') as file:
            file.write(f'\n!{transform}')

    def pipe(self,
             name: str = None,
             description: str = None,
             repo: str = None,
             image: str = None,
             reprocess: bool = True):
        if name is None:
            subprocess.run([*self._base, 'list', 'pipeline'])

        else:
            dirname = Path(name)
            if dirname.exists():
                self._create_or_update_pipeline(dirname, reprocess)

            else:
                self._generate_pipeline_template(dirname, description, repo, image)

    def repo(self, name=None):
        if name is None:
            subprocess.run([*self._base, 'list', 'repo'])

        else:
            subprocess.run([*self._base, 'create', 'repo', name], check=True)

    def job(self):
        subprocess.run([*self._base, 'list', 'job'])

    def dag(self, name=None):
        if name is None:
            raise ValueError('no name provided')
        else:
            dirname = Path(name)
            dirname.mkdir(parents=True)

            for template in dag_templating:
                template(dirname)

    def log(self, name=None):
        if name is None:
            raise ValueError('no name provided')

        subprocess.run([*self._base, 'logs', f'--pipeline={name}'])

    def view(self, dag: str):
        pass

    def __call__(self, cmd=None):
        if cmd is None:
            subprocess.run([*self._base, 'shell'])

        else:
            prc = ' '.join((*self._base, cmd))
            subprocess.run(prc, shell=True, check=True)
