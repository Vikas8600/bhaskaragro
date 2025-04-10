from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in bhaskaragro/__init__.py
from bhaskaragro import __version__ as version

setup(
	name='bhaskaragro',
	version=version,
	description='dexciss',
	author='Dexciss Technology',
	author_email='info@dexciss.com',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
