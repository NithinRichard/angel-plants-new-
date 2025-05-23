#!/usr/bin/env python
"""
Run the test suite for the Angel Plants project.

This script runs all tests or a subset of tests with various options.
"""
import os
import sys
import argparse
import django
from django.test.utils import get_runner
from django.conf import settings


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run the test suite for Angel Plants.')
    parser.add_argument(
        'test_labels',
        nargs='*',
        default=['payment.tests'],
        help='Test labels to run (e.g., payment.tests.test_utils).',
    )
    parser.add_argument(
        '--noinput',
        '--no-input',
        action='store_false',
        dest='interactive',
        help='Do not prompt the user for input of any kind.',
    )
    parser.add_argument(
        '--failfast',
        action='store_true',
        help='Stop running tests after first failure.',
    )
    parser.add_argument(
        '--keepdb',
        action='store_true',
        help='Preserves the test DB between runs.',
    )
    parser.add_argument(
        '--parallel',
        nargs='?',
        const='auto',
        type=int,
        help='Run tests in parallel processes.',
    )
    parser.add_argument(
        '-v', '--verbosity',
        type=int,
        default=2,
        help='Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, 3=very verbose output.',
    )
    return parser.parse_args()


def run_tests():
    """Run the test suite."""
    args = parse_arguments()
    
    # Set up Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'angels_plants.settings_test')
    django.setup()
    
    # Get test runner
    TestRunner = get_runner(settings)
    
    # Configure test runner
    test_runner_kwargs = {
        'verbosity': args.verbosity,
        'interactive': args.interactive,
        'failfast': args.failfast,
        'keepdb': args.keepdb,
    }
    
    # Only add parallel if specified to avoid None comparison issues
    if args.parallel is not None:
        test_runner_kwargs['parallel'] = args.parallel
    
    test_runner = TestRunner(**test_runner_kwargs)
    
    # Run tests
    failures = test_runner.run_tests(args.test_labels)
    
    # Exit with appropriate status code
    sys.exit(bool(failures))


if __name__ == '__main__':
    run_tests()
