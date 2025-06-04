# This is a placeholder for your project's setup.py file.
# You can use this file to make your project installable, e.g., via pip.
# For more information, see:
# https://packaging.python.org/en/latest/tutorials/packaging-projects/

from setuptools import setup, find_packages

setup(
    name='omni_agent', # Replace with your project's name
    version='0.1.0',    # Replace with your project's version
    description='An autonomous agent for UI interaction.', # Replace with a short description
    author='Your Name', # Replace with your name
    author_email='your.email@example.com', # Replace with your email
    # url='https://github.com/yourusername/omni-agent', # Replace with your project's URL
    packages=find_packages(where='src'), # Tells setuptools to find packages in src/
    package_dir={'': 'src'}, # Specifies that packages are under src/
    install_requires=[
        # List your project's dependencies here.
        # They should match the ones in requirements.txt
        # e.g., 'google-generativeai>=0.5.0',
        #       'langgraph>=0.0.30',
    ],
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.org/classifiers/
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'License :: OSI Approved :: MIT License', # Choose your license
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    python_requires='>=3.9',
    # entry_points={
    #     'console_scripts': [
    #         'omni-agent=omni_agent.src.core.workflow:main_cli_function', # Example if you have a CLI
    #     ],
    # },
) 