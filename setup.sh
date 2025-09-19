#!/bin/bash

echo "🧬 Setting up Oligonucleotide Designer..."

# Create project structure
echo "📁 Creating project structure..."
mkdir -p oligonucleotide-designer
cd oligonucleotide-designer

# Backend structure
mkdir -p backend/{core,api,data,tests}
mkdir -p backend/core
mkdir -p backend/api

# Create __init__.py files for Python packages
touch backend/__init__.py
touch backend/core/__init__.py
touch backend/api/__init__.py

echo "🐍 Setting up Python backend..."
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install Flask==2.3.3 Flask-CORS==4.0.0 python-dotenv==1.0.0

cd ..

echo "⚛️ Setting up React frontend..."

# Create React app
npx create-react-app frontend
cd frontend

# Install additional dependencies
npm install lucide-react

echo "📝 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy the provided backend code files to: backend/"
echo "2. Copy the provided frontend code files to: frontend/src/"
echo "3. Update frontend/src/App.js to import OligoDesigner"
echo ""
echo "To run the application:"
echo "Backend: cd backend && source venv/bin/activate && python app.py"
echo "Frontend: cd frontend && npm start"
echo ""
echo "The backend will run on http://localhost:5000"
echo "The frontend will run on http://localhost:3000"