from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='angels-plants',
    version='1.0.0',
    description='Angel Plants - E-commerce Platform for Plants',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Your Name',
    author_email='your.email@example.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Django>=4.2,<5.0',
        'psycopg2-binary>=2.9.5',
        'whitenoise>=6.4.0',
        'django-redis>=5.2.0',
        'redis>=4.5.0',
        'django-compressor>=4.1',
        'django-debug-toolbar>=4.0.0',
        'psutil>=5.9.0',
        'python-dotenv>=1.0.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-django>=4.5.0',
            'pytest-cov>=4.0.0',
            'black>=23.0.0',
            'isort>=5.12.0',
            'flake8>=6.0.0',
            'mypy>=1.0.0',
            'ipython>=8.0.0',
            'django-extensions>=3.2.0',
        ],
        'monitoring': [
            'sentry-sdk>=1.15.0',
            'prometheus-client>=0.17.0',
            'psutil>=5.9.0',
        ],
    },
    scripts=[
        'scripts/performance_monitor.py',
        'scripts/optimize_site.py',
    ],
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 4.2',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
    ],
)
