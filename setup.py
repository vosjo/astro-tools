 
import setuptools

setuptools.setup(
    name="astro-tools", # Replace with your own username
    version="0.0.1",
    author="Joris Vos",
    author_email="joris.vos@uv.cl",
    description="Astronomy related scripts",
    packages=setuptools.find_packages(),
    license='MIT',
    entry_points = {
        'console_scripts': ['astro-sfi=astro_tools.sfi:main',
                            'astro-norm=astro_tools.normalize:main'],
    },
    python_requires='>=2.7',
)
