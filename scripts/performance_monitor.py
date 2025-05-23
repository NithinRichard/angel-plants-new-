"""
Performance monitoring and optimization script.
"""
import os
import sys
import time
import logging
import psutil
import subprocess
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('performance_monitor.log')
    ]
)
logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """
    Monitor system and application performance metrics.
    """
    def __init__(self, pid=None):
        self.pid = pid or os.getpid()
        self.process = psutil.Process(self.pid)
        self.start_time = time.time()
        self.metrics = {
            'cpu_percent': [],
            'memory_percent': [],
            'memory_rss': [],
            'memory_vms': [],
            'disk_io_read': [],
            'disk_io_write': [],
            'network_sent': [],
            'network_recv': [],
        }
    
    def collect_metrics(self, duration=60, interval=1):
        """
        Collect performance metrics for the specified duration.
        
        Args:
            duration: Total duration to collect metrics in seconds
            interval: Interval between metric collections in seconds
        """
        logger.info(f'Starting performance monitoring for PID {self.pid}...')
        
        end_time = time.time() + duration
        iteration = 0
        
        try:
            while time.time() < end_time:
                iteration += 1
                metrics = self._get_metrics()
                
                # Log metrics
                logger.info(
                    f'Iteration {iteration}: CPU={metrics["cpu_percent"]}% | '
                    f'Memory={metrics["memory_rss"]/1024/1024:.2f}MB | '
                    f'Disk IO (R/W)={metrics["disk_io_read"]/1024:.2f}KB/{metrics["disk_io_write"]/1024:.2f}KB | '
                    f'Network (S/R)={metrics["network_sent"]/1024:.2f}KB/{metrics["network_recv"]/1024:.2f}KB'
                )
                
                # Store metrics
                for key in self.metrics:
                    self.metrics[key].append(metrics[key])
                
                # Sleep for the interval
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info('Performance monitoring stopped by user')
        except Exception as e:
            logger.error(f'Error during performance monitoring: {e}')
        finally:
            self._generate_report()
    
    def _get_metrics(self):
        """Collect current metrics."""
        # Get process metrics
        with self.process.oneshot():
            cpu_percent = self.process.cpu_percent()
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            
            # Get disk I/O counters
            io_counters = self.process.io_counters()
            
            # Get network I/O counters
            net_io = psutil.net_io_counters()
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'memory_rss': memory_info.rss,
                'memory_vms': memory_info.vms,
                'disk_io_read': io_counters.read_bytes,
                'disk_io_write': io_counters.write_bytes,
                'network_sent': net_io.bytes_sent,
                'network_recv': net_io.bytes_recv,
            }
    
    def _generate_report(self):
        """Generate a performance report."""
        if not any(len(v) > 0 for v in self.metrics.values()):
            logger.warning('No metrics collected for report')
            return
        
        report = ['\n===== PERFORMANCE REPORT =====']
        report.append(f'Monitoring Duration: {time.time() - self.start_time:.2f} seconds')
        
        # Calculate statistics for each metric
        for metric, values in self.metrics.items():
            if not values:
                continue
                
            avg = sum(values) / len(values)
            min_val = min(values)
            max_val = max(values)
            
            # Format values based on metric type
            if 'memory' in metric or 'io' in metric or 'network' in metric:
                # Convert bytes to KB/MB/GB for readability
                for val in [avg, min_val, max_val]:
                    if val > 1024 * 1024 * 1024:
                        val = f'{val/1024/1024/1024:.2f}GB'
                    elif val > 1024 * 1024:
                        val = f'{val/1024/1024:.2f}MB'
                    elif val > 1024:
                        val = f'{val/1024:.2f}KB'
                    else:
                        val = f'{val:.2f}B'
                
                report.append(
                    f'{metric}: avg={avg}, min={min_val}, max={max_val}'
                )
            else:
                report.append(
                    f'{metric}: avg={avg:.2f}, min={min_val:.2f}, max={max_val:.2f}'
                )
        
        # Add system-wide metrics
        report.append('\nSystem-wide Metrics:')
        report.append(f'CPU Cores: {psutil.cpu_count()}')
        report.append(f'CPU Usage: {psutil.cpu_percent()}%')
        report.append(f'Memory Usage: {psutil.virtual_memory().percent}%')
        report.append(f'Disk Usage: {psutil.disk_usage("/").percent}%')
        
        # Save report to file
        report_path = 'performance_report.txt'
        with open(report_path, 'w') as f:
            f.write('\n'.join(report))
        
        logger.info(f'Performance report saved to {report_path}')
        logger.info('\n'.join(report[:10]))  # Print first 10 lines to console


def optimize_django():
    """Run Django optimization commands."""
    logger.info('Running Django optimizations...')
    
    # Run database optimizations
    try:
        logger.info('Optimizing database...')
        subprocess.run(['python', 'manage.py', 'optimize_db', '--all'], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f'Error optimizing database: {e}')
    
    # Clear cache
    try:
        logger.info('Clearing cache...')
        subprocess.run(['python', 'manage.py', 'clear_cache'], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f'Error clearing cache: {e}')
    
    # Collect static files
    try:
        logger.info('Collecting static files...')
        subprocess.run(['python', 'manage.py', 'collectstatic', '--noinput'], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f'Error collecting static files: {e}')
    
    # Compress static files
    try:
        logger.info('Compressing static files...')
        subprocess.run(['python', 'manage.py', 'compress', '--force'], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f'Error compressing static files: {e}')


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor and optimize application performance')
    parser.add_argument('--monitor', action='store_true', help='Monitor performance metrics')
    parser.add_argument('--duration', type=int, default=60, help='Monitoring duration in seconds')
    parser.add_argument('--interval', type=float, default=1.0, help='Monitoring interval in seconds')
    parser.add_argument('--optimize', action='store_true', help='Run optimization tasks')
    parser.add_argument('--pid', type=int, help='Process ID to monitor (default: current process)')
    
    args = parser.parse_args()
    
    if not (args.monitor or args.optimize):
        parser.print_help()
        return
    
    if args.optimize:
        optimize_django()
    
    if args.monitor:
        monitor = PerformanceMonitor(pid=args.pid)
        monitor.collect_metrics(duration=args.duration, interval=args.interval)


if __name__ == '__main__':
    # Create scripts directory if it doesn't exist
    Path('scripts').mkdir(exist_ok=True)
    
    # Run the main function
    main()
