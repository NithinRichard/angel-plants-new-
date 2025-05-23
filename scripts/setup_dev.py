"""
Development environment setup script.
"""
import os
import sys
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('setup.log')
    ]
)
logger = logging.getLogger(__name__)

def run_command(cmd, cwd=None):
    """Run a shell command and log the output."""
    logger.info(f'Running: {" ".join(cmd)}')
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or os.getcwd(),
            check=True,
            text=True,
            capture_output=True
        )
        if result.stdout:
            logger.info(result.stdout)
        if result.stderr:
            logger.warning(result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f'Command failed with error: {e}')
        if e.stdout:
            logger.error(f'Stdout: {e.stdout}')
        if e.stderr:
            logger.error(f'Stderr: {e.stderr}')
        return False

def check_prerequisites():
    """Check for required software."""
    required_software = {
        'python': ('--version', 'Python 3'),
        'pip': ('--version', 'pip'),
        'node': ('--version', 'v'),
        'npm': ('--version', None),
        'redis-cli': ('--version', 'Redis'),
    }
    
    missing = []
    for cmd, (arg, expected) in required_software.items():
        try:
            result = subprocess.run(
                [cmd, arg] if arg else [cmd],
                capture_output=True,
                text=True
            )
            if expected and expected not in result.stdout + result.stderr:
                raise Exception(f'Unexpected version: {result.stdout}')
            logger.info(f'Found {cmd}: {result.stdout.strip() or result.stderr.strip()}')
        except Exception as e:
            logger.error(f'Missing or invalid {cmd}: {e}')
            missing.append(cmd)
    
    if missing:
        logger.error(f'Missing required software: {", ".join(missing)}')
        return False
    return True

def setup_virtualenv():
    """Set up Python virtual environment."""
    venv_dir = 'venv'
    if not os.path.exists(venv_dir):
        logger.info('Creating virtual environment...')
        if not run_command([sys.executable, '-m', 'venv', venv_dir]):
            return False
    
    # Activate virtual environment
    activate_script = 'Scripts/activate' if os.name == 'nt' else 'bin/activate'
    activate_path = os.path.join(venv_dir, activate_script)
    
    # Install requirements
    commands = [
        [activate_path, '&&', 'pip', 'install', '-r', 'requirements.txt'],
        [activate_path, '&&', 'pip', 'install', '-r', 'requirements-dev.txt'],
    ]
    
    for cmd in commands:
        if not run_command(cmd):
            return False
    
    return True

def setup_environment():
    """Set up environment variables."""
    env_file = '.env'
    if not os.path.exists(env_file):
        logger.info('Creating .env file...')
        with open('.env.example', 'r') as src, open(env_file, 'w') as dst:
            dst.write(src.read())
        logger.info('Please edit .env with your configuration')
    else:
        logger.info('.env file already exists')
    
    # Create necessary directories
    for directory in ['logs', 'media', 'staticfiles']:
        Path(directory).mkdir(exist_ok=True)
    
    return True

def setup_database():
    """Set up the database."""
    logger.info('Setting up database...')
    commands = [
        ['python', 'manage.py', 'migrate'],
        ['python', 'manage.py', 'createcachetable'],
    ]
    
    for cmd in commands:
        if not run_command(cmd):
            return False
    return True

def setup_frontend():
    """Set up frontend dependencies."""
    if os.path.exists('package.json'):
        logger.info('Installing frontend dependencies...')
        return run_command(['npm', 'install'])
    return True

def main():
    """Main setup function."""
    logger.info('Starting development environment setup...')
    
    if not check_prerequisites():
        logger.error('Prerequisites check failed')
        return 1
    
    if not setup_virtualenv():
        logger.error('Virtual environment setup failed')
        return 1
    
    if not setup_environment():
        logger.error('Environment setup failed')
        return 1
    
    if not setup_database():
        logger.error('Database setup failed')
        return 1
    
    if not setup_frontend():
        logger.error('Frontend setup failed')
        return 1
    
    logger.info('\nSetup completed successfully!')
    logger.info('\nNext steps:')
    logger.info('1. Edit the .env file with your configuration')
    logger.info('2. Run the development server: python manage.py runserver')
    logger.info('3. Access the site at http://localhost:8000')
    logger.info('\nFor more information, see PERFORMANCE_GUIDE.md')
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
