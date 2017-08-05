long_description = '''
This is a library for interactively exploring the heap of a python program to track down leaks.
The basic intuition is that you _know_ that your program shouldn't be taking 2 gigabytes of memory at this point, and it's probably a bunch of objects of a single type taking up all that memory.
But how do you figure out who's holding the references to them?

Python's built in `gc` module gives you the tools to figure it out, but it's a tedious process and if you do it in an interactive session you're going to be generating a bunch of additional references that will complicate your search pretty drastically.
This tool was built after several hours of frustration with this!

Then, to detox, I learned `prompt_toolkit` and made the prompt pretty.
'''

from setuptools import setup
setup(name='dive',
      version='0.1',
      py_modules=['dive'],
      install_requires=['prompt_toolkit'],
      author_email='andrewrdutcher@gmail.com',
      author='rhelmot',
      url='https://github.com/rhelmot/dumpsterdiver',
      description='A tool for interactively traversing the python heap to find memory leaks',
      license='MIT',
      keywords='heap memory leak interative',
)
