#!/bin/bash
set -e

# CHRIS Backend Test Runner
# Runs the complete test suite with coverage reporting

echo "=== CHRIS Backend Test Suite ==="
echo ""

# Activate virtual environment
source venv/bin/activate

# Run tests with coverage
echo "Running tests with coverage..."
python -m pytest tests/ \
    -v \
    --tb=short \
    --disable-warnings \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-report=json

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All tests passed!"
    echo ""
    echo "Coverage report generated:"
    echo "  - HTML: htmlcov/index.html"
    echo "  - JSON: coverage.json"
else
    echo ""
    echo "❌ Some tests failed. Please review the output above."
    exit 1
fi
