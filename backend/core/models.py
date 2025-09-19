from dataclasses import dataclass
from typing import List, Optional, Dict


@dataclass
class Domain:
    """Domain specification for oligonucleotide design"""
    name: str
    length: int
    fixed_sequence: Optional[str] = None
    target_gc_content: float = 50.0
    generated_sequence: Optional[str] = None
    validation_passed: bool = False


@dataclass
class GlobalParams:
    """Global reaction parameters"""
    reaction_temp: float = 37.0  # °C
    salt_conc: float = 50.0  # mM
    mg_conc: float = 2.0  # mM
    oligo_conc: float = 250.0  # nM


@dataclass
class ValidationCheck:
    """Individual validation check result"""
    pass_check: bool
    value: Optional[float] = None
    delta_g: Optional[float] = None
    threshold: Optional[float] = None
    target_range: Optional[List[float]] = None
    message: str = ""


@dataclass
class ValidationResult:
    """Complete validation result for a strand"""
    overall_pass: bool
    checks: Dict[str, ValidationCheck]


@dataclass
class GeneratedStrand:
    """Final generated strand with all information"""
    name: str
    total_length: int
    sequence: str
    domains: List[Domain]


@dataclass
class DesignResult:
    """Complete design result"""
    success: bool
    strand: Optional[GeneratedStrand] = None
    validation: Optional[ValidationResult] = None
    generation_time: float = 0.0
    generated_at: str = ""
    error_message: str = ""