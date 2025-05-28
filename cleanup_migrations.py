import os
import sys
import shutil
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent))

# Remove all migration files except initial
migrations_dir = Path('store/migrations')
if migrations_dir.exists():
    for file in migrations_dir.glob('*'):
        if file.name != '0001_initial.py' and file.name != '__init__.py':
            try:
                os.remove(file)
                print(f'Removed: {file}')
            except Exception as e:
                print(f'Error removing {file}: {e}')

# Create new migrations
try:
    os.system('python manage.py makemigrations store')
    print('Created new migrations')
except Exception as e:
    print(f'Error creating migrations: {e}')

# Apply migrations
try:
    os.system('python manage.py migrate store')
    print('Migrations applied successfully')
except Exception as e:
    print(f'Error applying migrations: {e}')

print('Migration cleanup complete!')
