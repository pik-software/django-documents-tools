from setuptools import setup, find_packages


def _get_requirements(file_name):
    requirements = []
    with open(file_name) as fin:
        for line in fin:
            if '#' not in line:
                requirements.append(line.strip())
    return requirements


REQUIREMENTS = _get_requirements('requirements.txt')
REQUIREMENTS_DEV = _get_requirements('requirements.dev.txt')


setup(
    name='django-documents-tools',
    author='pik-software',
    author_email='no-reply@pik-software.ru',
    version='1.0.0',
    license='BSD-3-Clause',
    url='https://github.com/pik-software/documents-tools',
    install_requires=REQUIREMENTS,
    description='Toolset to work with documents and snapshots',
    packages=find_packages(exclude=['tests*']),
    extras_require={'dev': REQUIREMENTS_DEV},
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython'
    ],
    zip_safe=False,
    include_package_data=True
)
