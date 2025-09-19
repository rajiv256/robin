# Oligonucleotide Designer

Design orthogonal DNA strands with thermodynamic validation. Build multi-domain sequences and validate them for
hairpins, dimerization, and melting temperatures.

## Setup

### Requirements

- Python 3.10
- Node.js and npm

### Backend Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements


# Create __init__.py files
touch __init__.py core/__init__.py api/__init__.py
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install
```

## Running

Start backend:

```bash
cd backend
source venv/bin/activate
python app.py
```

Start frontend (in another terminal):

```bash
cd frontend
npm start
```

Open http://localhost:3000

## Usage

1. Add domains with name and length
2. Click "Generate & Validate" to create sequences
3. Save strands to your library
4. Edit/duplicate saved strands as needed

The system validates melting temperature, hairpin formation, and dimerization automatically.