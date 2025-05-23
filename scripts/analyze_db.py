"""
Database analysis and optimization script.
"""
import os
import sys
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import django
from django.conf import settings
from django.db import connection, connections
from django.core.management import call_command

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('db_analysis.log')
    ]
)
logger = logging.getLogger(__name__)

class DatabaseAnalyzer:
    """Database analysis and optimization utilities."""
    
    def __init__(self, database: str = 'default'):
        """Initialize with database connection."""
        self.database = database
        self.connection = connections[database]
        self.vendor = self.connection.vendor
        self.results: Dict[str, Any] = {
            'timestamp': datetime.now().isoformat(),
            'database': {
                'vendor': self.vendor,
                'name': self.connection.settings_dict['NAME']
            },
            'analysis': {}
        }
    
    def analyze_tables(self) -> Dict[str, Any]:
        """Analyze database tables and indexes."""
        logger.info('Analyzing database tables...')
        results = {
            'tables': [],
            'indexes': [],
            'missing_indexes': []
        }
        
        with self.connection.cursor() as cursor:
            # Get table sizes and row counts
            if self.vendor == 'postgresql':
                cursor.execute("""
                    SELECT 
                        table_name, 
                        pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as total_size,
                        pg_table_size(quote_ident(table_name)) as table_size,
                        pg_indexes_size(quote_ident(table_name)) as index_size,
                        (SELECT reltuples::bigint FROM pg_class WHERE oid = quote_ident(table_name)::regclass) as row_count
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC;
                """)
                
                for row in cursor.fetchall():
                    results['tables'].append({
                        'name': row[0],
                        'total_size': row[1],
                        'table_size': row[2],
                        'index_size': row[3],
                        'row_count': row[4]
                    })
                
                # Find unused indexes
                cursor.execute("""
                    SELECT 
                        indexrelid::regclass as index_name,
                        relid::regclass as table_name,
                        pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
                        idx_scan as index_scans,
                        idx_tup_read as tuples_read,
                        idx_tup_fetch as tuples_fetched
                    FROM pg_stat_user_indexes 
                    JOIN pg_statio_user_indexes USING (indexrelid)
                    WHERE idx_scan = 0
                    ORDER BY pg_relation_size(indexrelid) DESC;
                """)
                
                for row in cursor.fetchall():
                    results['indexes'].append({
                        'name': row[0],
                        'table': row[1],
                        'size': row[2],
                        'scans': row[3],
                        'tuples_read': row[4],
                        'tuples_fetched': row[5]
                    })
                
                # Find missing indexes
                cursor.execute("""
                    SELECT 
                        relname AS table_name,
                        seq_scan - idx_scan AS too_many_seq_scans,
                        CASE WHEN seq_scan > 0 
                            THEN ROUND(100.0 * idx_scan / (seq_scan + idx_scan), 2)
                            ELSE 0 
                        END AS percent_of_times_index_used,
                        n_live_tup rows_in_table
                    FROM pg_stat_user_tables
                    WHERE seq_scan > 0
                    ORDER BY too_many_seq_scans DESC;
                """)
                
                for row in cursor.fetchall():
                    if row[2] < 90:  # Less than 90% index usage
                        results['missing_indexes'].append({
                            'table': row[0],
                            'seq_scans': row[1],
                            'index_usage_percent': row[2],
                            'row_count': row[3]
                        })
            
            elif self.vendor == 'sqlite':
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall() if not row[0].startswith('sqlite_')]
                
                for table in tables:
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    row_count = cursor.fetchone()[0]
                    
                    # Get table size (approximate)
                    cursor.execute(f"PRAGMA page_count;")
                    page_count = cursor.fetchone()[0]
                    cursor.execute(f"PRAGMA page_size;")
                    page_size = cursor.fetchone()[0]
                    table_size = page_count * page_size
                    
                    results['tables'].append({
                        'name': table,
                        'total_size': f"{table_size} bytes",
                        'row_count': row_count
                    })
                
                # Get index info
                cursor.execute("""
                    SELECT name, tbl_name, sql 
                    FROM sqlite_master 
                    WHERE type = 'index' 
                    AND tbl_name NOT LIKE 'sqlite_%';
                """)
                
                for row in cursor.fetchall():
                    results['indexes'].append({
                        'name': row[0],
                        'table': row[1],
                        'definition': row[2]
                    })
        
        self.results['analysis']['tables'] = results
        return results
    
    def analyze_queries(self, top_n: int = 10) -> Dict[str, Any]:
        """Analyze slow and frequent queries."""
        logger.info('Analyzing query performance...')
        results = {
            'slow_queries': [],
            'frequent_queries': []
        }
        
        if self.vendor == 'postgresql':
            with self.connection.cursor() as cursor:
                # Get slow queries
                cursor.execute("""
                    SELECT 
                        query,
                        calls,
                        total_exec_time,
                        mean_exec_time,
                        rows,
                        100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                    FROM pg_stat_statements 
                    ORDER BY mean_exec_time DESC 
                    LIMIT %s;
                """, [top_n])
                
                for row in cursor.fetchall():
                    results['slow_queries'].append({
                        'query': row[0],
                        'calls': row[1],
                        'total_time_ms': row[2],
                        'avg_time_ms': row[3],
                        'rows': row[4],
                        'cache_hit_percent': row[5]
                    })
                
                # Get frequent queries
                cursor.execute("""
                    SELECT 
                        query,
                        calls,
                        total_exec_time,
                        mean_exec_time,
                        rows
                    FROM pg_stat_statements 
                    ORDER BY calls DESC 
                    LIMIT %s;
                """, [top_n])
                
                for row in cursor.fetchall():
                    results['frequent_queries'].append({
                        'query': row[0],
                        'calls': row[1],
                        'total_time_ms': row[2],
                        'avg_time_ms': row[3],
                        'rows': row[4]
                    })
        
        self.results['analysis']['queries'] = results
        return results
    
    def generate_report(self, output_file: Optional[str] = None) -> str:
        """Generate a human-readable report."""
        report = [
            "=" * 80,
            f"Database Analysis Report - {self.results['timestamp']}",
            "=" * 80,
            f"Database: {self.results['database']['name']} ({self.results['database']['vendor']})\n"
        ]
        
        # Table analysis
        if 'tables' in self.results['analysis']:
            report.extend([
                "\n" + "=" * 40,
                "Table Analysis",
                "=" * 40,
                "\nLargest Tables by Size:",
                "-" * 30
            ])
            
            for table in self.results['analysis']['tables']['tables'][:10]:
                if self.vendor == 'postgresql':
                    report.append(f"{table['name']}: {table['row_count']:,} rows, {table['total_size']} total")
                else:
                    report.append(f"{table['name']}: {table['row_count']:,} rows, {table['total_size']}")
            
            # Unused indexes
            if self.vendor == 'postgresql' and self.results['analysis']['tables']['indexes']:
                report.extend([
                    "\nUnused Indexes (consider removing):",
                    "-" * 30
                ])
                for idx in self.results['analysis']['tables']['indexes'][:10]:
                    report.append(f"{idx['name']} on {idx['table']}: {idx['size']}, 0 scans")
            
            # Missing indexes
            if self.vendor == 'postgresql' and self.results['analysis']['tables']['missing_indexes']:
                report.extend([
                    "\nTables That Might Need Indexes:",
                    "-" * 30
                ])
                for table in self.results['analysis']['tables']['missing_indexes'][:10]:
                    report.append(
                        f"{table['table']}: {table['seq_scans']} seq scans, "
                        f"{table['index_usage_percent']}% index usage, {table['row_count']:,} rows"
                    )
        
        # Query analysis
        if 'queries' in self.results['analysis']:
            report.extend([
                "\n" + "=" * 40,
                "Query Analysis",
                "=" * 40,
                "\nSlowest Queries:",
                "-" * 30
            ])
            
            for i, query in enumerate(self.results['analysis']['queries']['slow_queries'][:5], 1):
                report.append(
                    f"{i}. {query['query'][:100]}...\n"
                    f"   Avg: {query['avg_time_ms']:.2f}ms, Calls: {query['calls']}, "
                    f"Rows: {query['rows']}"
                )
            
            report.extend([
                "\nMost Frequent Queries:",
                "-" * 30
            ])
            
            for i, query in enumerate(self.results['analysis']['queries']['frequent_queries'][:5], 1):
                report.append(
                    f"{i}. {query['query'][:100]}...\n"
                    f"   Calls: {query['calls']}, Avg: {query['avg_time_ms']:.2f}ms, "
                    f"Total: {query['total_time_ms']:.2f}ms"
                )
        
        report_text = "\n".join(report)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            logger.info(f"Report saved to {output_file}")
        
        return report_text

def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description='Analyze database performance.')
    parser.add_argument('--output', '-o', help='Output file for the report')
    parser.add_argument('--database', '-d', default='default', help='Database connection name')
    parser.add_argument('--top', type=int, default=10, help='Number of top items to show')
    args = parser.parse_args()
    
    # Setup Django environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings')
    django.setup()
    
    # Run analysis
    analyzer = DatabaseAnalyzer(database=args.database)
    analyzer.analyze_tables()
    analyzer.analyze_queries(top_n=args.top)
    
    # Generate and print report
    report = analyzer.generate_report(args.output)
    print(report)

if __name__ == '__main__':
    main()
