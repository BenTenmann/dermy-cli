import os
import subprocess
from pathlib import Path

import srsly
from glom import glom, Coalesce

from .utils import dag_templating, pipe_templating, get_image

HOME = os.environ.get('HOME')


class Interface:
    _pachyderm: Path = Path(HOME) / '.pachyderm/config.json'
    assert _pachyderm.exists()

    _config: dict = srsly.read_json(_pachyderm)
    _active_context: str = glom(_config, Coalesce('v1.active_context', 'v2.active_context'))
    _base: list = ['pachctl']

    def _docker_build(self, directory: Path):
        if self._active_context == 'local':
            subprocess.run('eval $(minikube docker-env)', shell=True)

        image = get_image(directory)
        subprocess.run(['docker', 'build', '-t', image, directory], check=True)

        if self._active_context != 'local':
            # remote registry
            pass

    def pipe(self, name=None, description=None, repo=None, image=None):
        if name is None:
            subprocess.run([*self._base, 'list', 'pipeline'])

        else:
            dirname = Path(name)
            if dirname.exists():
                out = subprocess.run([*self._base, 'list', 'pipeline'], capture_output=True)
                if name in out:
                    # update pipeline branch
                    pass

                else:
                    # create pipeline branch
                    subprocess.run([*self._base, 'create', 'pipeline', '-f', dirname / 'manifest.yml'])

            else:
                # generate pipeline template branch
                dirname.mkdir()

                transform = f'{name}/transform.py'
                params = {
                    'name': name,
                    'description': f'\n{description}\n' if description else '',
                    'repo': repo if repo else '<insert repo>',
                    'image': image if image else get_image(dirname.parent),
                    'cmd': transform
                }
                for template in pipe_templating:
                    template(dirname, **params)

                with (dirname.parent / 'Dockerfile').open(mode='a') as file:
                    file.write(f'COPY {transform} {name}/')

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
