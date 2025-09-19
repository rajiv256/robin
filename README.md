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

## Complete Project Structure

```
oligonucleotide-designer/
├── README.md
├── requirements.txt
├── package.json
├── setup.sh
├── .env.example
├── .gitignore
│
├── backend/
│   ├── __init__.py
│   ├── app.py                          # Flask application entry point
│   ├── config.py                       # Configuration management
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py                   # Data classes (Domain, GlobalParams, ValidationSettings)
│   │   ├── repository.py               # OrthogonalRepository class for sequence management
│   │   ├── thermodynamics.py           # ThermodynamicCalculator class (nearest neighbor)
│   │   ├── validator.py                # SequenceValidator class (hairpins, dimers, GC content)
│   │   └── designer.py                 # Main OligonucleotideDesigner orchestration class
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py                   # API route definitions (/generate-oligonucleotide)
│   │   └── utils.py                    # API utility functions and error handling
│   │
│   ├── data/
│   │   ├── orthogonal_sequences.json   # Repository of pre-validated orthogonal sequences
│   │   ├── thermodynamic_params.json   # Nearest neighbor thermodynamic parameters
│   │   └── validation_config.json      # Default validation thresholds and settings
│   │
│   └── tests/
│       ├── __init__.py
│       ├── test_thermodynamics.py      # Unit tests for melting temperature calculations
│       ├── test_validator.py           # Unit tests for sequence validation
│       ├── test_designer.py            # Integration tests for design workflow
│       └── test_api.py                 # API endpoint tests
│
├── frontend/
│   ├── public/
│   │   ├── index.html                  # Main HTML template
│   │   └── favicon.ico                 # Application icon
│   │
│   ├── src/
│   │   ├── components/
│   │   │   ├── OligoDesigner.jsx       # Main application component
│   │   │   └── OligoDesigner.css       # Component-specific styling
│   │   │
│   │   ├── utils/
│   │   │   └── api.js                  # API client functions for backend communication
│   │   │
│   │   ├── App.js                      # Root React component
│   │   ├── App.css                     # Global application styles
│   │   └── index.js                    # React application entry point
│   │
│   └── package.json                    # Frontend dependencies and scripts
│
└── scripts/
    ├── setup.sh                        # Automated project setup script
    ├── start_backend.sh                # Backend startup script
    └── start_frontend.sh               # Frontend startup script
```

## File Descriptions

### Backend Files

#### **`backend/app.py`**

Flask application entry point that:

- Initializes the Flask app with CORS support
- Registers API blueprints from routes.py
- Configures logging and error handling
- Sets up the development server

#### **`backend/core/models.py`**

Data classes and structures including:

- `Domain`: Represents individual oligonucleotide domains with name, length, and sequence
- `GlobalParams`: Reaction conditions (temperature, salt, Mg2+, oligo concentration)
- `ValidationSettings`: Thresholds for hairpins, dimers, GC content, melting temperature
- `StrandRequest`: Input data structure for API requests
- `ValidationResult`: Output structure for validation results

#### **`backend/core/repository.py`**

`OrthogonalRepository` class that:

- Manages a database of pre-validated orthogonal sequences
- Loads sequences from JSON files with metadata
- Provides sequence selection based on length and orthogonality requirements
- Handles sequence filtering and quality scoring

#### **`backend/core/thermodynamics.py`**

`ThermodynamicCalculator` class implementing:

- Nearest neighbor thermodynamic calculations
- Melting temperature (Tm) predictions using salt correction
- Free energy calculations for secondary structures
- Temperature-dependent stability analysis

#### **`backend/core/validator.py`**

`SequenceValidator` class providing:

- Hairpin formation detection and ΔG calculation
- Self-dimerization analysis
- Cross-dimerization between multiple sequences
- GC content validation
- Repeat sequence detection
- 3' end stability analysis

#### **`backend/core/designer.py`**

`OligonucleotideDesigner` orchestration class that:

- Coordinates the entire design workflow
- Integrates repository, thermodynamics, and validation
- Generates multi-domain oligonucleotides
- Optimizes sequences for specified criteria
- Returns comprehensive results with validation feedback

#### **`backend/api/routes.py`**

Flask Blueprint defining:

- `POST /api/generate-oligonucleotide`: Main design endpoint
- Request validation and error handling
- Response formatting with detailed validation results
- CORS headers for frontend integration

#### **`backend/config.py`**

Configuration management with:

- Environment variable handling
- Development/production settings
- File paths for data resources
- Logging configuration

### Frontend Files

#### **`frontend/src/components/OligoDesigner.jsx`**

Main React component featuring:

- **Multi-domain strand design**: Interactive domain builder with add/remove functionality
- **Tabbed interface**: Design view and strand library management
- **Advanced settings panel**: Collapsible reaction conditions and validation parameters
- **Real-time validation**: Color-coded results showing pass/fail status
- **Strand library**: Save, edit, duplicate, and delete designed strands
- **Results visualization**: Sequence display with domain breakdown and validation feedback

#### **`frontend/src/components/OligoDesigner.css`**

Comprehensive stylesheet including:

- **Layout components**: Responsive grid and flexbox designs
- **Interactive elements**: Buttons, forms, tabs with hover states
- **Domain visualization**: Gradient badges and directional arrows
- **Settings panels**: Collapsible sections with advanced parameter controls
- **Validation displays**: Color-coded results (green=pass, red=fail)
- **Library interface**: Card-based layouts for saved strands
- **Scientific styling**: Monospace fonts for DNA sequences

#### **`frontend/src/utils/api.js`**

API client providing:

- `generateStrand()`: POST requests to backend design endpoint
- Error handling and response parsing
- Base URL configuration for different environments
- Request/response data transformation

#### **`frontend/src/App.js`**

Root React component that:

- Imports and renders the main OligoDesigner component
- Provides global application structure
- Handles routing (if expanded)

### Configuration Files

#### **`requirements.txt`**

Python dependencies:

- Flask 2.3.3: Web framework
- Flask-CORS 4.0.0: Cross-origin resource sharing
- numpy 1.24.3: Numerical calculations
- python-dotenv 1.0.0: Environment variable management
- pytest 7.4.0: Testing framework

#### **`frontend/package.json`**

Node.js dependencies:

- react ^18.2.0: Frontend framework
- react-dom ^18.2.0: DOM rendering
- lucide-react ^0.263.1: Icon library
- react-scripts: Build and development tools

#### **`setup.sh`**

Automated setup script that:

- Creates complete project directory structure
- Sets up Python virtual environment
- Installs backend dependencies
- Initializes React frontend
- Configures development environment

#### **`.env.example`**

Environment configuration template:

- Flask development settings
- API endpoints and URLs
- File paths for data resources
- Logging levels and debug flags

### Data Files

#### **`backend/data/orthogonal_sequences.json`**

Repository containing:

- Pre-validated orthogonal DNA sequences
- Sequence metadata (length, GC content, Tm)
- Orthogonality scores and cross-reactivity data
- Quality ratings and usage statistics

#### **`backend/data/thermodynamic_params.json`**

Thermodynamic parameters including:

- Nearest neighbor enthalpy and entropy values
- Salt correction factors
- Temperature-dependent coefficients
- Secondary structure parameters

#### **`backend/data/validation_config.json`**

Default validation settings:

- Threshold values for each validation type
- Enabled/disabled validation rules
- Scoring weights and priorities
- User-customizable parameters

## Key Features by Component

### Backend Capabilities

- **Orthogonal sequence design**: Generate sequences that don't cross-react
- **Thermodynamic validation**: Accurate melting temperature predictions
- **Comprehensive validation**: Hairpins, dimers, GC content, repeats
- **Multi-domain support**: Complex oligonucleotide architectures
- **RESTful API**: Clean integration with frontend applications

### Frontend Features

- **Interactive design interface**: Drag-and-drop domain building
- **Real-time validation feedback**: Immediate pass/fail indicators
- **Advanced parameter control**: Fine-tune reaction conditions
- **Strand library management**: Save and organize designs
- **Responsive design**: Works on desktop and mobile devices
- **Scientific visualization**: Clear display of sequences and validation results

## Installation & Usage

1. **Setup**: Run `./setup.sh` to initialize the complete environment
2. **Backend**: `cd backend && source venv/bin/activate && python app.py`
3. **Frontend**: `cd frontend && npm start`
4. **Access**: Frontend at http://localhost:3000, API at http://localhost:5000

## Technical Architecture

- **Backend**: Python Flask with modular architecture
- **Frontend**: React with functional components and hooks
- **API**: RESTful design with JSON data exchange
- **Database**: JSON file storage (easily upgradeable to SQL)
- **Testing**: Comprehensive unit and integration tests
- **Deployment**: Docker-ready with environment configuration

The system validates melting temperature, hairpin formation, and dimerization automatically.