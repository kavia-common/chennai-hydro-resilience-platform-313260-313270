#!/bin/bash
# Make all shell scripts executable

chmod +x start.sh
chmod +x run_tests.sh
chmod +x test_endpoints.sh
chmod +x verify_startup.py
chmod +x make_executable.sh

echo "✓ All scripts are now executable"
echo ""
echo "Available scripts:"
echo "  ./verify_startup.py    - Verify backend configuration"
echo "  ./start.sh             - Start the backend server"
echo "  ./test_endpoints.sh    - Test all API endpoints"
echo "  ./run_tests.sh         - Run unit tests"
