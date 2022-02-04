#!/usr/bin/env python

from setuptools import setup
import shutil
import glob
setup(name='ClasseVivaHelper',
      version='1.1',
      description='ClasseViva Helper Toolkit',
      author='coval3nte',
      author_email='covalente@posteo.eu',
      url='https://github.com/coval3nte/ClasseVivaHelper',
      install_requires=[
          'colorama',
          'requests',
          'pyyaml',
          'lxml',
          'asyncio'
      ],
      packages=['cvv', 'cvv.methods'],
      package_dir={'classeviva': 'cvv'},
      entry_points={
          'console_scripts': [
              'classeviva = cvv.main:main',
          ],
      },
      )

shutil.rmtree('dist')
shutil.rmtree(glob.glob('*.egg-info')[0])
shutil.rmtree(glob.glob('build')[0])
