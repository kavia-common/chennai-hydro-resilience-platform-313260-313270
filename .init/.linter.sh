#!/bin/bash
cd /home/kavia/workspace/code-generation/chennai-hydro-resilience-platform-313260-313270/chris_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

