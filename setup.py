#!/usr/bin/env python
# encoding=utf-8
import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.md')).read()

setup(name='saturn',
      version='0.1.0',  # Use bumpversio to update
      description='Add URNs to Alma records.',
      long_description=README,
      classifiers=[
          'Programming Language :: Python',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
      ],
      keywords='marc alma',
      author='Scriptoteket',
      author_email='scriptoteket@ub.uio.no',
      url='https://github.com/scriptotek/saturn',
      license='MIT',
      install_requires=['requests',
                        'colorama',
                        'lxml',
                        'zeep',
                        'questionary',
                        'python-dotenv',
                        'PyYAML',
                        ],
      setup_requires=['pytest-runner'],
      tests_require=['pytest', 'pytest-pycodestyle', 'pytest-cov', 'responses', 'mock'],
      entry_points={'console_scripts': ['saturn=saturn.saturn:main']},
      options={
          'build_scripts': {
              'executable': '/usr/bin/env python',
          },
      },
      packages=['saturn']
      )
