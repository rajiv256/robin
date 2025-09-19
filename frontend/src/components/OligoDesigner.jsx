import React, {useState} from 'react';
import './OligoDesigner.css';

// Real API function that connects to Redis database
const generateStrand = async (requestData) => {
    try {
        const response = await fetch('http://localhost:5000/api/generate-oligonucleotide', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || 'Generation failed');
        }

        return result;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
};

const OligoDesigner = () => {
    // Strand library - stores all saved strands
    const [strandLibrary, setStrandLibrary] = useState([]);

    // Current strand being designed
    const [currentStrand, setCurrentStrand] = useState({
        id: null,
        name: 'Strand 1',
        domains: [],
        result: null
    });

    // Current domain being added
    const [currentDomain, setCurrentDomain] = useState({
        name: '',
        length: 20
    });

    // Domain registry - tracks all domains and their sequences
    const [domainRegistry, setDomainRegistry] = useState({});

    // UI state
    const [isGenerating, setIsGenerating] = useState(false);
    const [error, setError] = useState(null);
    const [saveMessage, setSaveMessage] = useState(null);
    const [activeTab, setActiveTab] = useState('design'); // 'design' or 'library'

    // Global parameters
    const [globalParams, setGlobalParams] = useState({
        reaction_temp: 37,
        salt_conc: 50,
        mg_conc: 2,
        oligo_conc: 250
    });

    // Advanced validation settings
    const [validationSettings, setValidationSettings] = useState({
        melting_temp: {
            enabled: true,
            min_offset: 5,
            max_offset: 25
        },
        hairpin: {
            enabled: true,
            max_dg: -3.0
        },
        self_dimer: {
            enabled: true,
            max_dg: -6.0
        },
        cross_dimer: {
            enabled: true,
            max_dg: -6.0
        },
        gc_content: {
            enabled: true,
            min_percent: 40,
            max_percent: 60
        },
        primer_3_end: {
            enabled: false,
            max_dg: -3.0
        },
        repeats: {
            enabled: false,
            max_length: 4
        },
        secondary_structure: {
            enabled: false,
            max_dg: -2.0
        }
    });

    const [showAdvanced, setShowAdvanced] = useState(false);

    // Helper functions for complement handling
    const getComplementName = (domainName) => {
        if (domainName.endsWith('*')) {
            return domainName.slice(0, -1); // Remove *
        } else {
            return domainName + '*'; // Add *
        }
    };

    const getComplementSequence = (sequence) => {
        const complementMap = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'};
        return sequence.split('').reverse().map(base =>
            complementMap[base.toUpperCase()] || base
        ).join('');
    };


    const findComplementInRegistry = (domainName, length) => {
        const complementName = getComplementName(domainName);
        const domain = domainRegistry[complementName];
        return domain && domain.length === length ? domain : null;
    };

    // Check if current domain name exists in registry OR if its complement exists
    const isDomainInRegistry = (domainName) => {
        if (!domainName) return false;
        // Check if domain itself exists
        if (domainRegistry.hasOwnProperty(domainName)) return true;
        // Check if its complement exists (which means we can generate this domain)
        const complementName = getComplementName(domainName);
        return domainRegistry.hasOwnProperty(complementName);
    };

    // Get the length of a domain - either from itself or from its complement
    const getDomainLength = (domainName) => {
        if (!domainName) return null;
        // Check if domain itself exists
        if (domainRegistry[domainName]) {
            return domainRegistry[domainName].length;
        }
        // Check if its complement exists
        const complementName = getComplementName(domainName);
        if (domainRegistry[complementName]) {
            return domainRegistry[complementName].length;
        }
        return null;
    };

    // Update domain registry with generated sequences and auto-create complements
    const updateDomainRegistry = (domains) => {
        setDomainRegistry(prev => {
            const updated = {...prev};

            domains.forEach(domain => {
                if (domain.sequence) {
                    // Add the domain itself
                    updated[domain.name] = {
                        name: domain.name,
                        length: domain.length,
                        sequence: domain.sequence
                    };

                    // Auto-create reverse complement only if it's not already a complement
                    if (!domain.name.endsWith('*')) {
                        const complementName = getComplementName(domain.name);
                        const complementSequence = getComplementSequence(domain.sequence);

                        updated[complementName] = {
                            name: complementName,
                            length: domain.length,
                            sequence: complementSequence
                        };
                    }
                }
            });
            return updated;
        });
    };

    // Add domain to current strand with complement handling
    const addDomain = () => {
        if (currentDomain.name) {
            const existingDomain = domainRegistry[currentDomain.name];
            let domainToAdd;

            if (existingDomain) {
                // Use existing domain from registry
                domainToAdd = {
                    id: Date.now(),
                    name: currentDomain.name,
                    length: existingDomain.length,
                    fixed_sequence: existingDomain.sequence,
                    target_gc_content: 50
                };
            } else {
                // Check if this is a complement of an existing domain
                const baseName = currentDomain.name.endsWith('*')
                    ? currentDomain.name.slice(0, -1)
                    : currentDomain.name + '*';
                const baseDomain = domainRegistry[baseName];

                if (baseDomain) {
                    // This is a complement - generate sequence from base domain
                    const complementSequence = getComplementSequence(baseDomain.sequence);
                    domainToAdd = {
                        id: Date.now(),
                        name: currentDomain.name,
                        length: baseDomain.length,
                        fixed_sequence: complementSequence,
                        target_gc_content: 50
                    };

                    // Also add this complement to the registry
                    setDomainRegistry(prev => ({
                        ...prev,
                        [currentDomain.name]: {
                            name: currentDomain.name,
                            length: baseDomain.length,
                            sequence: complementSequence
                        }
                    }));
                } else {
                    // Completely new domain - will be generated
                    domainToAdd = {
                        id: Date.now(),
                        name: currentDomain.name,
                        length: currentDomain.length,
                        fixed_sequence: null,
                        target_gc_content: 50
                    };
                }
            }

            setCurrentStrand(prev => ({
                ...prev,
                domains: [...prev.domains, domainToAdd]
            }));
            setCurrentDomain({name: '', length: 20});
        }
    };

    // Add complement domain
    const addComplementDomain = () => {
        const complementName = getComplementName(currentDomain.name);
        const complement = findComplementInRegistry(currentDomain.name, currentDomain.length);

        if (complement) {
            setCurrentStrand(prev => ({
                ...prev,
                domains: [...prev.domains, {
                    id: Date.now(),
                    name: complementName,
                    length: currentDomain.length,
                    fixed_sequence: complement.sequence,
                    target_gc_content: 50
                }]
            }));
            setCurrentDomain({name: '', length: 20});
        }
    };

    // Remove domain from current strand
    const removeDomain = (id) => {
        setCurrentStrand(prev => ({
            ...prev,
            domains: prev.domains.filter(d => d.id !== id)
        }));
    };

    // Save current strand to library
    const saveStrand = () => {
        if (currentStrand.domains.length === 0) {
            setSaveMessage({type: 'error', text: 'Please add at least one domain before saving'});
            setTimeout(() => setSaveMessage(null), 3000);
            return;
        }

        const strandToSave = {
            ...currentStrand,
            id: currentStrand.id || Date.now(),
            savedAt: new Date().toLocaleString()
        };

        if (currentStrand.id) {
            // Update existing strand
            setStrandLibrary(prev =>
                prev.map(s => s.id === currentStrand.id ? strandToSave : s)
            );
            setSaveMessage({type: 'success', text: 'Strand updated successfully!'});
        } else {
            // Add new strand
            setStrandLibrary(prev => [...prev, strandToSave]);
            setSaveMessage({type: 'success', text: 'Strand saved to library!'});
        }

        // Clear message after 3 seconds
        setTimeout(() => setSaveMessage(null), 3000);

        // Reset current strand for new design
        const nextStrandNumber = strandLibrary.length + 2;
        setCurrentStrand({
            id: null,
            name: `Strand ${nextStrandNumber}`,
            domains: [],
            result: null
        });
    };

    // Load strand from library for editing
    const loadStrand = (strand) => {
        setCurrentStrand({
            ...strand,
            result: null // Clear previous results when editing
        });
        setActiveTab('design');
    };

    // Delete strand from library
    const deleteStrand = (strandId) => {
        if (window.confirm('Are you sure you want to delete this strand?')) {
            setStrandLibrary(prev => prev.filter(s => s.id !== strandId));
        }
    };

    // Duplicate strand in library
    const duplicateStrand = (strand) => {
        const duplicated = {
            ...strand,
            id: Date.now(),
            name: `${strand.name} (Copy)`,
            result: null,
            savedAt: new Date().toLocaleString()
        };
        setStrandLibrary(prev => [...prev, duplicated]);
    };

    // Generate oligonucleotide
    const generateOligo = async () => {
        if (currentStrand.domains.length === 0) {
            alert('Please add at least one domain');
            return;
        }

        setIsGenerating(true);
        setError(null);

        try {
            const requestData = {
                strand_name: currentStrand.name,
                domains: currentStrand.domains,
                global_params: globalParams,
                validation_settings: validationSettings
            };

            console.log('Sending request:', requestData);
            const response = await generateStrand(requestData);
            console.log('Got response:', response);

            // Update domain registry with generated sequences
            if (response.success && response.domains) {
                updateDomainRegistry(response.domains);
            }

            setCurrentStrand(prev => ({...prev, result: response}));

        } catch (err) {
            console.error('Generation failed:', err);
            setError(`Failed to generate: ${err.message}`);
        }

        setIsGenerating(false);
    };


    return (
        <div className="oligo-designer">
            <h1>🧬 Multi-Strand Oligonucleotide Designer</h1>

            {/* Tabs */}
            <div className="tabs">
                <button
                    className={`tab-button ${activeTab === 'design' ? 'active' : 'inactive'}`}
                    onClick={() => setActiveTab('design')}
                >
                    Design ({currentStrand.domains.length} domains)
                </button>
                <button
                    className={`tab-button ${activeTab === 'library' ? 'active' : 'inactive'}`}
                    onClick={() => setActiveTab('library')}
                >
                    Library ({strandLibrary.length} strands)
                </button>
            </div>

            {/* Design Tab */}
            {activeTab === 'design' && (
                <div className="tab-content">
                    {/* Strand Name */}
                    <div className="form-group">
                        <label className="form-label">Strand Name:</label>
                        <input
                            type="text"
                            className="form-input strand-name"
                            value={currentStrand.name}
                            onChange={(e) => setCurrentStrand(prev => ({...prev, name: e.target.value}))}
                        />
                    </div>

                    {/* Current Domains */}
                    {currentStrand.domains.length > 0 && (
                        <div className="domain-status">
                            <h3>Current Strand (5′ → 3′)</h3>
                            <div className="domain-list">
                                {currentStrand.domains.map((domain, index) => (
                                    <React.Fragment key={domain.id}>
                                        <div className="domain-badge">
                                            <div className="domain-name">{domain.name}</div>
                                            <div className="domain-length">{domain.length}bp</div>
                                            {domain.fixed_sequence && (
                                                <div className="domain-complement-indicator">🧬</div>
                                            )}
                                            <button
                                                onClick={() => removeDomain(domain.id)}
                                                className="domain-remove"
                                            >
                                                ×
                                            </button>
                                        </div>
                                        {index < currentStrand.domains.length - 1 &&
                                            <span className="domain-arrow">→</span>
                                        }
                                    </React.Fragment>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Settings Panel */}
                    <div className="settings-panel">
                        <div className="settings-header">
                            <h3>Reaction Conditions</h3>
                            <button
                                onClick={() => setShowAdvanced(!showAdvanced)}
                                className="advanced-toggle"
                            >
                                {showAdvanced ? '🔼 Hide Advanced' : '🔽 Show Advanced'}
                            </button>
                        </div>

                        {/* Basic Settings */}
                        <div className="basic-settings">
                            <div>
                                <label className="form-label">Reaction Temperature (°C):</label>
                                <input
                                    type="number"
                                    className="form-input"
                                    value={globalParams.reaction_temp}
                                    onChange={(e) => setGlobalParams(prev => ({
                                        ...prev,
                                        reaction_temp: Number(e.target.value)
                                    }))}
                                />
                            </div>
                            <div className="temp-target">
                                🌡️ Target Tm: {globalParams.reaction_temp + validationSettings.melting_temp.min_offset}°C
                                - {globalParams.reaction_temp + validationSettings.melting_temp.max_offset}°C
                            </div>
                        </div>

                        {/* Advanced Settings */}
                        {showAdvanced && (
                            <div className="advanced-settings">
                                <div className="advanced-section">
                                    <h4>Advanced Reaction Parameters</h4>
                                    <div className="advanced-grid">
                                        <div>
                                            <label className="form-label">Salt (mM):</label>
                                            <input
                                                type="number"
                                                className="advanced-input"
                                                value={globalParams.salt_conc}
                                                onChange={(e) => setGlobalParams(prev => ({
                                                    ...prev,
                                                    salt_conc: Number(e.target.value)
                                                }))}
                                            />
                                        </div>
                                        <div>
                                            <label className="form-label">Mg²⁺ (mM):</label>
                                            <input
                                                type="number"
                                                step="0.1"
                                                className="advanced-input"
                                                value={globalParams.mg_conc}
                                                onChange={(e) => setGlobalParams(prev => ({
                                                    ...prev,
                                                    mg_conc: Number(e.target.value)
                                                }))}
                                            />
                                        </div>
                                        <div>
                                            <label className="form-label">Oligo (nM):</label>
                                            <input
                                                type="number"
                                                className="advanced-input"
                                                value={globalParams.oligo_conc}
                                                onChange={(e) => setGlobalParams(prev => ({
                                                    ...prev,
                                                    oligo_conc: Number(e.target.value)
                                                }))}
                                            />
                                        </div>
                                    </div>
                                </div>

                                <div className="advanced-section">
                                    <h4>Validation Thresholds</h4>

                                    {/* Melting Temperature Settings */}
                                    <div className="validation-group">
                                        <div className="validation-header">
                                            <input
                                                type="checkbox"
                                                checked={validationSettings.melting_temp.enabled}
                                                onChange={(e) => setValidationSettings(prev => ({
                                                    ...prev,
                                                    melting_temp: {...prev.melting_temp, enabled: e.target.checked}
                                                }))}
                                            />
                                            <label>Melting Temperature Range</label>
                                        </div>
                                        {validationSettings.melting_temp.enabled && (
                                            <div className="validation-controls">
                                                <span>Offset:</span>
                                                <input
                                                    type="number"
                                                    className="validation-input"
                                                    placeholder="Min"
                                                    value={validationSettings.melting_temp.min_offset}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        melting_temp: {
                                                            ...prev.melting_temp,
                                                            min_offset: Number(e.target.value)
                                                        }
                                                    }))}
                                                />
                                                <span>to</span>
                                                <input
                                                    type="number"
                                                    className="validation-input"
                                                    placeholder="Max"
                                                    value={validationSettings.melting_temp.max_offset}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        melting_temp: {
                                                            ...prev.melting_temp,
                                                            max_offset: Number(e.target.value)
                                                        }
                                                    }))}
                                                />
                                                <span>°C above reaction temp</span>
                                            </div>
                                        )}
                                    </div>

                                    {/* Hairpin Settings */}
                                    <div className="validation-group">
                                        <div className="validation-header">
                                            <input
                                                type="checkbox"
                                                checked={validationSettings.hairpin.enabled}
                                                onChange={(e) => setValidationSettings(prev => ({
                                                    ...prev,
                                                    hairpin: {...prev.hairpin, enabled: e.target.checked}
                                                }))}
                                            />
                                            <label>Hairpin Formation</label>
                                        </div>
                                        {validationSettings.hairpin.enabled && (
                                            <div className="validation-controls">
                                                <span>Max ΔG:</span>
                                                <input
                                                    type="number"
                                                    step="0.1"
                                                    className="validation-input dg-input"
                                                    value={validationSettings.hairpin.max_dg}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        hairpin: {...prev.hairpin, max_dg: Number(e.target.value)}
                                                    }))}
                                                />
                                                <span>kcal/mol</span>
                                            </div>
                                        )}
                                    </div>

                                    {/* Self Dimerization Settings */}
                                    <div className="validation-group">
                                        <div className="validation-header">
                                            <input
                                                type="checkbox"
                                                checked={validationSettings.self_dimer.enabled}
                                                onChange={(e) => setValidationSettings(prev => ({
                                                    ...prev,
                                                    self_dimer: {...prev.self_dimer, enabled: e.target.checked}
                                                }))}
                                            />
                                            <label>Self Dimerization</label>
                                        </div>
                                        {validationSettings.self_dimer.enabled && (
                                            <div className="validation-controls">
                                                <span>Max ΔG:</span>
                                                <input
                                                    type="number"
                                                    step="0.1"
                                                    className="validation-input dg-input"
                                                    value={validationSettings.self_dimer.max_dg}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        self_dimer: {...prev.self_dimer, max_dg: Number(e.target.value)}
                                                    }))}
                                                />
                                                <span>kcal/mol</span>
                                            </div>
                                        )}
                                    </div>

                                    {/* Cross Dimerization Settings */}
                                    <div className="validation-group">
                                        <div className="validation-header">
                                            <input
                                                type="checkbox"
                                                checked={validationSettings.cross_dimer.enabled}
                                                onChange={(e) => setValidationSettings(prev => ({
                                                    ...prev,
                                                    cross_dimer: {...prev.cross_dimer, enabled: e.target.checked}
                                                }))}
                                            />
                                            <label>Cross Dimerization</label>
                                        </div>
                                        {validationSettings.cross_dimer.enabled && (
                                            <div className="validation-controls">
                                                <span>Max ΔG:</span>
                                                <input
                                                    type="number"
                                                    step="0.1"
                                                    className="validation-input dg-input"
                                                    value={validationSettings.cross_dimer.max_dg}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        cross_dimer: {
                                                            ...prev.cross_dimer,
                                                            max_dg: Number(e.target.value)
                                                        }
                                                    }))}
                                                />
                                                <span>kcal/mol</span>
                                            </div>
                                        )}
                                    </div>

                                    {/* GC Content Settings */}
                                    <div className="validation-group">
                                        <div className="validation-header">
                                            <input
                                                type="checkbox"
                                                checked={validationSettings.gc_content.enabled}
                                                onChange={(e) => setValidationSettings(prev => ({
                                                    ...prev,
                                                    gc_content: {...prev.gc_content, enabled: e.target.checked}
                                                }))}
                                            />
                                            <label>GC Content Range</label>
                                        </div>
                                        {validationSettings.gc_content.enabled && (
                                            <div className="validation-controls">
                                                <input
                                                    type="number"
                                                    className="validation-input"
                                                    placeholder="Min"
                                                    value={validationSettings.gc_content.min_percent}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        gc_content: {
                                                            ...prev.gc_content,
                                                            min_percent: Number(e.target.value)
                                                        }
                                                    }))}
                                                />
                                                <span>to</span>
                                                <input
                                                    type="number"
                                                    className="validation-input"
                                                    placeholder="Max"
                                                    value={validationSettings.gc_content.max_percent}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        gc_content: {
                                                            ...prev.gc_content,
                                                            max_percent: Number(e.target.value)
                                                        }
                                                    }))}
                                                />
                                                <span>%</span>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Add Domain Section */}
                    <div className="add-domain">
                        <h3>Add Domain</h3>
                        <div className="domain-inputs">
                            <div>
                                <label className="form-label">Name:</label>
                                <input
                                    type="text"
                                    className="form-input"
                                    value={currentDomain.name}
                                    onChange={(e) => {
                                        const newName = e.target.value;
                                        setCurrentDomain(prev => ({
                                            ...prev,
                                            name: newName,
                                            // Auto-update length if this domain exists in registry
                                            length: isDomainInRegistry(newName)
                                                ? getDomainLength(newName) || prev.length
                                                : prev.length
                                        }));
                                    }}
                                    placeholder="e.g., a, b, a*"
                                />
                            </div>
                            <div>
                                <label className="form-label">
                                    Length (bp):
                                    {isDomainInRegistry(currentDomain.name) &&
                                        <span className="disabled-indicator"> (auto-set from registry)</span>}
                                </label>
                                <input
                                    type="number"
                                    className={`form-input domain-length ${isDomainInRegistry(currentDomain.name) ? 'disabled' : ''}`}
                                    value={isDomainInRegistry(currentDomain.name) ? getDomainLength(currentDomain.name) : currentDomain.length}
                                    onChange={(e) => !isDomainInRegistry(currentDomain.name) && setCurrentDomain(prev => ({
                                        ...prev,
                                        length: Number(e.target.value)
                                    }))}
                                    disabled={isDomainInRegistry(currentDomain.name)}
                                />
                            </div>
                            <button
                                onClick={addDomain}
                                disabled={!currentDomain.name}
                                className="btn btn-primary"
                            >
                                + Add Domain
                                {isDomainInRegistry(currentDomain.name) && <span className="complement-badge">📋</span>}
                            </button>

                            {/* Show complement suggestion */}
                            {currentDomain.name && (() => {
                                const complement = findComplementInRegistry(currentDomain.name, currentDomain.length);
                                return complement && !isDomainInRegistry(currentDomain.name) ? (
                                    <button
                                        onClick={addComplementDomain}
                                        className="btn btn-complement"
                                    >
                                        + Add Complement ({getComplementName(currentDomain.name)})
                                    </button>
                                ) : null;
                            })()}
                        </div>

                        {/* Show domain registry */}
                        {Object.keys(domainRegistry).length > 0 && (
                            <div className="domain-registry">
                                <h4>Available Domains:</h4>
                                <div className="domain-registry-list">
                                    {Object.values(domainRegistry).map(domain => (
                                        <span
                                            key={domain.name}
                                            className={`domain-registry-item ${domain.name.endsWith('*') ? 'complement-domain' : ''}`}
                                            onClick={() => setCurrentDomain({
                                                name: domain.name,
                                                length: domain.length
                                            })}
                                            title={`Click to use: ${domain.sequence}`}
                                        >
                                            {domain.name} ({domain.length}bp)
                                            {domain.name.endsWith('*') && <span className="complement-star">🧬</span>}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Action Buttons */}
                    <div className="action-buttons">
                        <button
                            onClick={generateOligo}
                            disabled={isGenerating || currentStrand.domains.length === 0}
                            className="btn btn-success"
                        >
                            {isGenerating ? '🔄 Generating...' : '▶ Generate & Validate'}
                        </button>

                        <button
                            onClick={saveStrand}
                            disabled={currentStrand.domains.length === 0}
                            className="btn btn-secondary"
                        >
                            💾 Save to Library
                        </button>
                    </div>

                    {/* Save Message Display */}
                    {saveMessage && (
                        <div className={`error ${saveMessage.type === 'success' ? 'success-message' : ''}`}>
                            {saveMessage.text}
                        </div>
                    )}

                    {/* Error Display */}
                    {error && (
                        <div className="error">
                            <strong>Error:</strong> {error}
                        </div>
                    )}

                    {/* Results */}
                    {currentStrand.result && currentStrand.result.success && (
                        <div className="results">
                            <h2>Results: {currentStrand.result.strand.name}</h2>

                            <div
                                className={`status-badge ${currentStrand.result.validation.overall_pass ? 'status-success' : 'status-fail'}`}>
                                {currentStrand.result.validation.overall_pass ? '✅ All Checks Passed' : '❌ Some Checks Failed'}
                            </div>

                            <div className="result-stats">
                                <strong>Length:</strong> {currentStrand.result.strand.total_length} bp |
                                <strong> Time:</strong> {currentStrand.result.generation_time.toFixed(2)}s
                            </div>

                            <div className="sequence-display">
                                <strong>Final Sequence (5′ → 3′):</strong>
                                <div className="sequence-box">
                                    {currentStrand.result.strand.sequence}
                                </div>
                            </div>

                            {/* Domain Breakdown with Complement Validation */}
                            {currentStrand.result.domains && (
                                <div className="domain-breakdown">
                                    <h3>Domain Breakdown</h3>
                                    <div className="domain-results">
                                        {currentStrand.result.domains.map((domain, index) => {
                                            const complement = findComplementInRegistry(domain.name, domain.length);
                                            const isValidComplement = complement &&
                                                getComplementSequence(domain.sequence) === complement.sequence;

                                            return (
                                                <div key={index} className="domain-result">
                                                    <div className="domain-result-header">
                                                        <span className="domain-result-name">{domain.name}</span>
                                                        <div className="domain-result-info">
                                                            <span
                                                                className="domain-result-length">{domain.length}bp</span>
                                                            {complement && (
                                                                <span
                                                                    className={`domain-status-badge ${isValidComplement ? 'domain-status-valid' : 'domain-status-invalid'}`}>
                                                                    {isValidComplement ? 'Complement OK' : 'Complement Mismatch'}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                    <div className="domain-sequence">{domain.sequence}</div>
                                                    {complement && (
                                                        <div className="complement-info">
                                                            Complement
                                                            ({getComplementName(domain.name)}): {complement.sequence}
                                                        </div>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}

                            {/* Validation Results */}
                            <div className="validation-results">
                                {currentStrand.result.validation.results.map((result, index) => (
                                    <div key={index} className={`validation-result ${result.pass ? 'pass' : 'fail'}`}>
                                        <div className="validation-result-header">{result.name}</div>
                                        <div className="validation-result-message">{result.message}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Library Tab */}
            {activeTab === 'library' && (
                <div className="tab-content">
                    {strandLibrary.length === 0 ? (
                        <div className="library-empty">
                            <div className="library-empty-icon">📚</div>
                            <p>No strands saved yet. Design and save strands to build your library!</p>
                        </div>
                    ) : (
                        <>
                            <div className="library-header">
                                <h2>Strand Library</h2>
                                <span className="library-count">{strandLibrary.length} saved strands</span>
                            </div>

                            <div className="library-list">
                                {strandLibrary.map((strand) => (
                                    <div key={strand.id} className="library-item">
                                        <div className="library-item-header">
                                            <div className="library-item-info">
                                                <h4>{strand.name}</h4>
                                                <p className="library-item-meta">Saved: {strand.savedAt}</p>
                                            </div>
                                            <div className="library-actions">
                                                <button
                                                    onClick={() => loadStrand(strand)}
                                                    className="library-action edit"
                                                >
                                                    Edit
                                                </button>
                                                <button
                                                    onClick={() => duplicateStrand(strand)}
                                                    className="library-action copy"
                                                >
                                                    Copy
                                                </button>
                                                <button
                                                    onClick={() => deleteStrand(strand.id)}
                                                    className="library-action delete"
                                                >
                                                    Delete
                                                </button>
                                            </div>
                                        </div>

                                        <div className="library-domains">
                                            {strand.domains.map((domain, index) => (
                                                <React.Fragment key={domain.id}>
                                                    <span className="library-domain">
                                                        {domain.name} ({domain.length}bp)
                                                    </span>
                                                    {index < strand.domains.length - 1 && <span>→</span>}
                                                </React.Fragment>
                                            ))}
                                        </div>

                                        {strand.result && strand.result.strand && (
                                            <div className="library-sequence">
                                                <strong>Sequence (5′ → 3′):</strong>
                                                <div className="sequence-box">
                                                    {strand.result.strand.sequence}
                                                </div>
                                            </div>
                                        )}

                                        {strand.result && (
                                            <div className="library-result">
                                                <div className="library-result-info">
                                                    <span
                                                        className={`library-result-status ${strand.result.validation.overall_pass ? 'library-result-pass' : 'library-result-fail'}`}>
                                                        {strand.result.validation.overall_pass ? 'Valid' : 'Failed'}
                                                    </span>
                                                    <span className="library-result-length">
                                                        {strand.result.strand.total_length}bp
                                                    </span>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
};

export default OligoDesigner;