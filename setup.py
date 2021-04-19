from setuptools import setup, find_packages
import pathlib

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

setup(
    name='instacli',
    version='0.2.11',
    license='Apache Software License',
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    install_requires=[
        'Click',
        'instaclient',
        'webdrivermanager'
    ],
    url = 'https://github.com/davidwickerhf/instacli',   # Provide either the link to your github or to your website
    download_url = 'https://github.com/davidwickerhf/instacli/archive/v0.2.11.tar.gz',
    long_description=README,
    long_description_content_type="text/markdown",
    author = 'David Wicker',                   # Type in your name
    author_email = 'davidwickerhf@gmail.com',
    keywords = ['INSTAGRAM', 'BOT', 'INSTAGRAM BOT', 'INSTAGRAM CLIENT'],
    classifiers=[
    'Development Status :: 3 - Alpha',      # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
    'Intended Audience :: Developers',      # Define that your audience are developers
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: Apache Software License',   # Again, pick a license      #Specify which pyhton versions that you want to support
    'Programming Language :: Python :: 3.9'
    ],
    entry_points='''
        [console_scripts]
        instacli=instacli.instacli:instacli
    ''',
)