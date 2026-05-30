#!/bin/bash
set -e

echo "Initializing Android Native Port Environment..."

# Verify Python existence for the harmonizer
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 is required to generate the C++ asset dictionary."
    exit 1
fi

# Scaffolding the Android project structure
echo "Creating Android project directories..."
mkdir -p app/src/main/cpp
mkdir -p app/src/main/java/com/pret/pokepinball
mkdir -p app/src/main/res/values

# Initialize the Gradle Wrapper locally if it does not exist
if [ ! -f "gradlew" ]; then
    echo "Gradle wrapper missing. Generating via local gradle installation..."
    if command -v gradle &> /dev/null; then
        gradle wrapper --gradle-version 8.4
    else
        echo "WARNING: Local gradle installation not found. The GitHub Action will generate the wrapper automatically during CI."
    fi
fi

if [ -f "gradlew" ]; then
    chmod +x gradlew
    echo "Gradle wrapper configured."
fi

echo "Environment initialized. Ready for 'make' -> 'tools/harmonizer.py' -> './gradlew assembleDebug'."
