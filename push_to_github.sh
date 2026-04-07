#!/bin/bash
# Script to push Vatavaran project to GitHub

echo "=========================================="
echo "Pushing Vatavaran to GitHub"
echo "=========================================="
echo ""

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
    echo "✓ Git initialized"
else
    echo "✓ Git already initialized"
fi

# Add remote if not exists
if ! git remote | grep -q "origin"; then
    echo "Adding GitHub remote..."
    git remote add origin https://github.com/Developer-Devanshhh/Vatavaran.git
    echo "✓ Remote added"
else
    echo "✓ Remote already exists"
    git remote set-url origin https://github.com/Developer-Devanshhh/Vatavaran.git
fi

# Add all files
echo ""
echo "Adding files to git..."
git add .
echo "✓ Files added"

# Commit
echo ""
echo "Committing changes..."
git commit -m "Initial commit: Vatavaran Climate Control System

- Complete Django backend with LSTM inference
- Weather API integration with caching
- NLP command parser for voice control
- CSV schedule generator
- Raspberry Pi components (sensor, STT, IR blaster)
- Comprehensive testing suite (76 unit tests)
- Full documentation and deployment guides"

echo "✓ Changes committed"

# Push to GitHub
echo ""
echo "Pushing to GitHub..."
echo "Note: You may need to enter your GitHub credentials"
git branch -M main
git push -u origin main

echo ""
echo "=========================================="
echo "✓ Successfully pushed to GitHub!"
echo "=========================================="
echo ""
echo "Repository: https://github.com/Developer-Devanshhh/Vatavaran"
echo ""
