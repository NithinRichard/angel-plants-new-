"""
Script to optimize the Django site performance.
"""
import os
import sys
import logging
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('optimization.log')
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

def optimize_database():
    """Run database optimization tasks."""
    logger.info('Optimizing database...')
    return run_command(['python', 'manage.py', 'optimize_db', '--all'])

def clear_cache():
    """Clear the application cache."""
    logger.info('Clearing cache...')
    return run_command(['python', 'manage.py', 'clear_cache'])

def collect_static():
    """Collect and compress static files."""
    logger.info('Collecting static files...')
    if not run_command(['python', 'manage.py', 'collectstatic', '--noinput']):
        return False
    
    logger.info('Compressing static files...')
    return run_command(['python', 'manage.py', 'compress', '--force'])

def run_migrations():
    """Run database migrations."""
    logger.info('Running migrations...')
    return run_command(['python', 'manage.py', 'migrate'])

def check_deploy():
    """Check deployment settings."""
    logger.info('Checking deployment settings...')
    return run_command(['python', 'manage.py', 'check', '--deploy'])

def main():
    """Main optimization routine."""
    # Ensure we're in the project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    logger.info('Starting site optimization...')
    
    # Run optimization tasks
    success = all([
        check_deploy(),
        run_migrations(),
        optimize_database(),
        clear_cache(),
        collect_static(),
    ])
    
    if success:
        logger.info('Site optimization completed successfully!')
    else:
        logger.error('Site optimization completed with errors')
        sys.exit(1)

if __name__ == '__main__':
    main()
