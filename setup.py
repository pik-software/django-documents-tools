from setuptools import setup, find_packages


requirements = [
    r.strip() for r in open('requirements.txt').readlines() if '#' not in r]


setup(
    name='documents-tools',
    author='pik-software',
    version='0.1.0',
    license='BSD-3-Clause',
    url='https://github.com/pik-software/documents-tools',
    install_requires=requirements,
    description='Toolset to work with documents and snapshots',
    packages=find_packages(),
    extras_require={'dev': ['ipdb==0.12.2', 'pytest==5.2.0']},
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython'
    ],
    zip_safe=False,
    include_package_data=True
)
