from setuptools import setup, find_packages

setup(
    name='canvas_langchain',
    version='0.1',
    description='A canvas langchain integration',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='University of Michigan',
    author_email='noreply@umich.edu',
    url='https://github.com/umich-its-ai/langchain-doc-canvas',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
    ],
    install_requires=[
        'langchain',
        'unstructured',
        'canvasapi',
        'beautifulsoup4',
        'lxml',
        'PyPDF2',
        'striprtf'
    ],
)
