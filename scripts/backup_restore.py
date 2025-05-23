"""
Database backup and restore utility.
"""
import os
import sys
import time
import logging
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import django
from django.conf import settings
from django.db import connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('backup_restore.log')
    ]
)
logger = logging.getLogger(__name__)

class DatabaseBackup:
    """Handle database backup and restore operations."""
    
    def __init__(self, database: str = 'default'):
        """Initialize with database connection."""
        self.database = database
        self.connection = connection
        self.vendor = self.connection.vendor
        self.db_settings = settings.DATABASES[database]
        self.backup_dir = Path(settings.BASE_DIR) / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
    
    def _get_backup_filename(self, prefix: str = 'backup') -> Path:
        """Generate a backup filename with timestamp."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return self.backup_dir / f"{prefix}_{timestamp}.sql"
    
    def _run_command(self, cmd: List[str], env: Optional[Dict] = None) -> Tuple[bool, str]:
        """Run a shell command and return (success, output)."""
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                env=env or os.environ
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, f"{e.stderr}\n{e.stdout}"
    
    def backup_postgresql(self) -> Tuple[bool, str]:
        """Backup a PostgreSQL database."""
        backup_file = self._get_backup_filename('postgres')
        
        # Build pg_dump command
        cmd = [
            'pg_dump',
            '--no-owner',
            '--no-privileges',
            '--format=plain',
            f'--file={backup_file}'
        ]
        
        # Add connection parameters
        if 'HOST' in self.db_settings and self.db_settings['HOST']:
            cmd.extend(['-h', self.db_settings['HOST']])
        if 'PORT' in self.db_settings and self.db_settings['PORT']:
            cmd.extend(['-p', str(self.db_settings['PORT'])])
        if 'USER' in self.db_settings and self.db_settings['USER']:
            cmd.extend(['-U', self.db_settings['USER']])
        
        # Add database name
        cmd.append(self.db_settings['NAME'])
        
        # Set password in environment if provided
        env = os.environ.copy()
        if 'PASSWORD' in self.db_settings and self.db_settings['PASSWORD']:
            env['PGPASSWORD'] = self.db_settings['PASSWORD']
        
        success, output = self._run_command(cmd, env)
        if success:
            return True, f"Backup created at {backup_file}"
        return False, f"Backup failed: {output}"
    
    def backup_mysql(self) -> Tuple[bool, str]:
        """Backup a MySQL database."""
        backup_file = self._get_backup_filename('mysql')
        
        # Build mysqldump command
        cmd = ['mysqldump', '--result-file', str(backup_file)]
        
        # Add connection parameters
        if 'HOST' in self.db_settings and self.db_settings['HOST']:
            cmd.extend(['-h', self.db_settings['HOST']])
        if 'PORT' in self.db_settings and self.db_settings['PORT']:
            cmd.extend(['-P', str(self.db_settings['PORT'])])
        if 'USER' in self.db_settings and self.db_settings['USER']:
            cmd.extend(['-u', self.db_settings['USER']])
        
        # Add password if provided
        if 'PASSWORD' in self.db_settings and self.db_settings['PASSWORD']:
            cmd.append(f"--password={self.db_settings['PASSWORD']}")
        
        # Add database name
        cmd.append(self.db_settings['NAME'])
        
        success, output = self._run_command(cmd)
        if success:
            return True, f"Backup created at {backup_file}"
        return False, f"Backup failed: {output}"
    
    def backup_sqlite(self) -> Tuple[bool, str]:
        """Backup a SQLite database."""
        db_path = Path(self.db_settings['NAME'])
        if not db_path.exists():
            return False, f"Database file not found: {db_path}"
        
        backup_file = self._get_backup_filename('sqlite')
        
        # For SQLite, we can just copy the file
        try:
            import shutil
            shutil.copy2(db_path, backup_file)
            return True, f"Backup created at {backup_file}"
        except Exception as e:
            return False, f"Backup failed: {e}"
    
    def backup(self) -> Tuple[bool, str]:
        """Backup the database based on the engine type."""
        logger.info(f"Starting {self.vendor} database backup...")
        
        if 'postgresql' in self.vendor:
            return self.backup_postgresql()
        elif 'mysql' in self.vendor:
            return self.backup_mysql()
        elif 'sqlite' in self.vendor:
            return self.backup_sqlite()
        else:
            return False, f"Unsupported database engine: {self.vendor}"
    
    def restore_postgresql(self, backup_file: Path) -> Tuple[bool, str]:
        """Restore a PostgreSQL database from backup."""
        if not backup_file.exists():
            return False, f"Backup file not found: {backup_file}"
        
        # Build psql command
        cmd = ['psql']
        
        # Add connection parameters
        if 'HOST' in self.db_settings and self.db_settings['HOST']:
            cmd.extend(['-h', self.db_settings['HOST']])
        if 'PORT' in self.db_settings and self.db_settings['PORT']:
            cmd.extend(['-p', str(self.db_settings['PORT'])])
        if 'USER' in self.db_settings and self.db_settings['USER']:
            cmd.extend(['-U', self.db_settings['USER']])
        
        # Add database name and file
        cmd.extend(['-d', self.db_settings['NAME'], '-f', str(backup_file)])
        
        # Set password in environment if provided
        env = os.environ.copy()
        if 'PASSWORD' in self.db_settings and self.db_settings['PASSWORD']:
            env['PGPASSWORD'] = self.db_settings['PASSWORD']
        
        success, output = self._run_command(cmd, env)
        if success:
            return True, f"Database restored from {backup_file}"
        return False, f"Restore failed: {output}"
    
    def restore_mysql(self, backup_file: Path) -> Tuple[bool, str]:
        """Restore a MySQL database from backup."""
        if not backup_file.exists():
            return False, f"Backup file not found: {backup_file}"
        
        # Build mysql command
        cmd = ['mysql']
        
        # Add connection parameters
        if 'HOST' in self.db_settings and self.db_settings['HOST']:
            cmd.extend(['-h', self.db_settings['HOST']])
        if 'PORT' in self.db_settings and self.db_settings['PORT']:
            cmd.extend(['-P', str(self.db_settings['PORT'])])
        if 'USER' in self.db_settings and self.db_settings['USER']:
            cmd.extend(['-u', self.db_settings['USER']])
        
        # Add password if provided
        if 'PASSWORD' in self.db_settings and self.db_settings['PASSWORD']:
            cmd.append(f"--password={self.db_settings['PASSWORD']}")
        
        # Add database name and file
        cmd.append(self.db_settings['NAME'])
        
        # Read backup file content
        try:
            with open(backup_file, 'r') as f:
                content = f.read()
            
            # Run mysql command with input
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                text=True,
                env=os.environ
            )
            process.communicate(input=content)
            
            if process.returncode == 0:
                return True, f"Database restored from {backup_file}"
            return False, f"Restore failed with code {process.returncode}"
            
        except Exception as e:
            return False, f"Restore failed: {e}"
    
    def restore_sqlite(self, backup_file: Path) -> Tuple[bool, str]:
        """Restore a SQLite database from backup."""
        if not backup_file.exists():
            return False, f"Backup file not found: {backup_file}"
        
        db_path = Path(self.db_settings['NAME'])
        
        try:
            import shutil
            shutil.copy2(backup_file, db_path)
            return True, f"Database restored from {backup_file}"
        except Exception as e:
            return False, f"Restore failed: {e}"
    
    def restore(self, backup_file: str) -> Tuple[bool, str]:
        """Restore the database from a backup file."""
        backup_path = Path(backup_file)
        if not backup_path.is_absolute():
            backup_path = self.backup_dir / backup_file
        
        logger.info(f"Restoring {self.vendor} database from {backup_path}...")
        
        if 'postgresql' in self.vendor:
            return self.restore_postgresql(backup_path)
        elif 'mysql' in self.vendor:
            return self.restore_mysql(backup_path)
        elif 'sqlite' in self.vendor:
            return self.restore_sqlite(backup_path)
        else:
            return False, f"Unsupported database engine: {self.vendor}"
    
    def list_backups(self) -> List[Path]:
        """List all available backups."""
        return sorted(
            self.backup_dir.glob('*.sql'),
            key=os.path.getmtime,
            reverse=True
        )

def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='Database backup and restore utility.')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Create a database backup')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore a database backup')
    restore_parser.add_argument('backup_file', nargs='?', help='Backup file to restore')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available backups')
    
    # Common arguments
    for p in [backup_parser, restore_parser, list_parser]:
        p.add_argument('--database', default='default', help='Database connection name')
    
    args = parser.parse_args()
    
    # Setup Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
    django.setup()
    
    db_backup = DatabaseBackup(database=args.database)
    
    if args.command == 'backup':
        success, message = db_backup.backup()
        print(f"{'SUCCESS' if success else 'ERROR'}: {message}")
        sys.exit(0 if success else 1)
    
    elif args.command == 'restore':
        if not args.backup_file:
            # List backups and prompt for selection
            backups = db_backup.list_backups()
            if not backups:
                print("No backup files found.")
                sys.exit(1)
                
            print("Available backups:")
            for i, backup in enumerate(backups, 1):
                mtime = datetime.fromtimestamp(backup.stat().st_mtime)
                print(f"{i}. {backup.name} ({mtime})")
            
            try:
                choice = int(input("Select backup to restore (number): "))
                if 1 <= choice <= len(backups):
                    backup_file = backups[choice - 1]
                else:
                    print("Invalid selection.")
                    sys.exit(1)
            except (ValueError, KeyboardInterrupt):
                print("Operation cancelled.")
                sys.exit(1)
        else:
            backup_file = args.backup_file
        
        confirm = input(f"WARNING: This will overwrite the database. Continue? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled.")
            sys.exit(0)
            
        success, message = db_backup.restore(backup_file)
        print(f"{'SUCCESS' if success else 'ERROR'}: {message}")
        sys.exit(0 if success else 1)
    
    elif args.command == 'list':
        backups = db_backup.list_backups()
        if not backups:
            print("No backup files found.")
            sys.exit(0)
            
        print(f"Found {len(backups)} backup{'s' if len(backups) > 1 else ''}:")
        for i, backup in enumerate(backups, 1):
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            size_mb = backup.stat().st_size / (1024 * 1024)
            print(f"{i}. {backup.name} ({mtime}, {size_mb:.2f} MB)")
    
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
