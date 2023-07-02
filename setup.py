from setuptools import setup

with open("README.md", "r") as f:
    long_description = f.read()

with open('requirements.txt', "r") as f:
    requirements = f.readlines()

setup(
    name='bili-uas',
    version='0.1.0',
    license='GPLv3',
    author='jhzg',
    author_email='jhzg02200059@163.com',
    url='https://github.com/jhzgjhzg/BiliBili-UP-Auxiliary-System',
    description='Assist up in personal, live, and video data analysis and prediction.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords=["BiliBili", "auxiliary", "analysis"],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Topic :: Software Development :: Build Tools',
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)"
    ],
    packages=['Bili_UAS',
              'Bili_UAS.utils',
              'Bili_UAS.writer',
              'Bili_UAS.scripts'],
    package_data={'': ['*.txt', '*.md', 'LICENSE', 'py.typed', 'setup.py'],
                  'Bili_UAS': ['*.txt', '*.md', 'LICENSE', 'py.typed'],
                  'readme_dir': ['*.jpg']},
    include_package_data=True,
    python_requires='>=3.9',
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'bili_config = Bili_UAS.bili_config:tyro_cli',
            'bili_live = Bili_UAS.bili_live:tyro_cli',
            'bili_user = Bili_UAS.bili_user:tyro_cli',
            'bili_video = Bili_UAS.bili_video:tyro_cli',
            'bili-user = Bili_UAS.bili_user:tyro_cli'
        ],
    }
)
