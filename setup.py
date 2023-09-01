from setuptools import setup

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

requirements = [
    'bilibili-api-python>=15.5.5',
    'setuptools>=68.1.2',
    'wordcloud>=1.9.2',
    'jieba>=0.42.1',
    'scipy>=1.11.2',
    'numpy>=1.25.2',
    'tyro>=0.5.5',
    'pandas>=2.0.3',
    'tqdm>=4.66.1',
    'matplotlib>=3.7.2',
    'asyncio>=3.4.3',
    'apscheduler>=3.10.4',
    'requests>=2.31.0',
    'httpx>=0.24.1',
    'openpyxl>=3.1.2',
    'opencv-python>=4.8.0.76']

setup(
    name='bili-uas',
    version='0.3.5',
    license='GPLv3',
    author='jhzg',
    author_email='jhzg02200059@163.com',
    url='https://github.com/jhzgjhzg/BiliBili-UP-Auxiliary-System',
    description='Assist up in personal, live, and video data analysis and prediction.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    keywords=["BiliBili", "auxiliary", "analysis", "live", "video", "word_cloud", "monitor"],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Topic :: Software Development :: Build Tools',
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)"
    ],
    packages=['Bili_UAS',
              'Bili_UAS.cli',
              'Bili_UAS.utils',
              'Bili_UAS.writer',
              'Bili_UAS.scripts'],
    package_data={'': ['*.txt', '*.md', 'LICENSE', 'setup.py', 'requirements.txt', '.gitignore']},
    include_package_data=True,
    python_requires='>=3.9',
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'bili-config = Bili_UAS.bili_config:tyro_cli',
            'bili-live = Bili_UAS.bili_live:tyro_cli',
            'bili-login = Bili_UAS.bili_login:tyro_cli',
            'bili-video = Bili_UAS.bili_video:tyro_cli',
            'bili-user = Bili_UAS.bili_user:tyro_cli'
        ],
    }
)
