import React, {useState} from 'react';
import {generateStrand} from '../utils/api';

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

    // UI state
    const [isGenerating, setIsGenerating] = useState(false);
    const [error, setError] = useState(null);
    const [activeTab, setActiveTab] = useState('design'); // 'design' or 'library'

    // Global parameters - now used from frontend
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

    // Add domain to current strand
    const addDomain = () => {
        if (currentDomain.name) {
            setCurrentStrand(prev => ({
                ...prev,
                domains: [...prev.domains, {
                    id: Date.now(),
                    name: currentDomain.name,
                    length: currentDomain.length,
                    fixed_sequence: null,
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
            alert('Please add at least one domain before saving');
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
        } else {
            // Add new strand
            setStrandLibrary(prev => [...prev, strandToSave]);
        }

        // Reset current strand for new design
        const nextStrandNumber = strandLibrary.length + 2;
        setCurrentStrand({
            id: null,
            name: `Strand ${nextStrandNumber}`,
            domains: [],
            result: null
        });

        alert('Strand saved to library!');
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
                validation_settings: validationSettings  // Include validation settings
            };

            console.log('Sending request:', requestData);
            const response = await generateStrand(requestData);
            console.log('Got response:', response);

            setCurrentStrand(prev => ({...prev, result: response}));

        } catch (err) {
            console.error('Generation failed:', err);
            setError(`Failed to generate: ${err.message}`);
        }

        setIsGenerating(false);
    };

    const tabStyle = (isActive) => ({
        padding: '8px 16px',
        backgroundColor: isActive ? '#007bff' : '#f8f9fa',
        color: isActive ? 'white' : '#333',
        border: '1px solid #dee2e6',
        borderBottom: 'none',
        borderRadius: '4px 4px 0 0',
        cursor: 'pointer',
        marginRight: '2px'
    });

    return (
        <div style={{padding: '20px', maxWidth: '1000px', margin: '0 auto'}}>
            <h1>🧬 Multi-Strand Oligonucleotide Designer</h1>

            {/* Tabs */}
            <div style={{marginBottom: '20px'}}>
                <button
                    style={tabStyle(activeTab === 'design')}
                    onClick={() => setActiveTab('design')}
                >
                    Design ({currentStrand.domains.length} domains)
                </button>
                <button
                    style={tabStyle(activeTab === 'library')}
                    onClick={() => setActiveTab('library')}
                >
                    Library ({strandLibrary.length} strands)
                </button>
            </div>

            {/* Design Tab */}
            {activeTab === 'design' && (
                <div style={{
                    border: '1px solid #dee2e6',
                    borderTop: 'none',
                    padding: '20px',
                    borderRadius: '0 0 8px 8px',
                    backgroundColor: '#fff'
                }}>
                    {/* Strand Name */}
                    <div style={{marginBottom: '20px'}}>
                        <label style={{display: 'block', fontWeight: 'bold', marginBottom: '5px'}}>
                            Strand Name:
                        </label>
                        <input
                            type="text"
                            value={currentStrand.name}
                            onChange={(e) => setCurrentStrand(prev => ({...prev, name: e.target.value}))}
                            style={{
                                padding: '8px',
                                borderRadius: '4px',
                                border: '1px solid #ccc',
                                width: '300px'
                            }}
                        />
                    </div>

                    {/* Basic Temperature Setting */}
                    <div style={{
                        background: 'linear-gradient(135deg, #f8f9fa, #e9ecef)',
                        padding: '20px',
                        borderRadius: '8px',
                        marginBottom: '20px'
                    }}>
                        <div style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            marginBottom: '15px'
                        }}>
                            <h3 style={{margin: 0, color: '#333'}}>Reaction Conditions</h3>
                            <button
                                onClick={() => setShowAdvanced(!showAdvanced)}
                                style={{
                                    padding: '6px 12px',
                                    backgroundColor: '#6c757d',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: 'pointer',
                                    fontSize: '12px'
                                }}
                            >
                                {showAdvanced ? '🔼 Hide Advanced' : '🔽 Show Advanced'}
                            </button>
                        </div>

                        {/* Basic Settings - Always Visible */}
                        <div style={{marginBottom: showAdvanced ? '20px' : '0'}}>
                            <div style={{display: 'flex', gap: '15px', alignItems: 'end'}}>
                                <div>
                                    <label style={{
                                        display: 'block',
                                        fontWeight: 'bold',
                                        marginBottom: '5px',
                                        fontSize: '14px'
                                    }}>
                                        Reaction Temperature (°C):
                                    </label>
                                    <input
                                        type="number"
                                        value={globalParams.reaction_temp}
                                        onChange={(e) => setGlobalParams(prev => ({
                                            ...prev,
                                            reaction_temp: Number(e.target.value)
                                        }))}
                                        style={{
                                            padding: '8px',
                                            borderRadius: '4px',
                                            border: '1px solid #ccc',
                                            width: '120px'
                                        }}
                                    />
                                </div>
                                <div style={{
                                    fontSize: '12px',
                                    color: '#666',
                                    fontStyle: 'italic',
                                    paddingBottom: '8px'
                                }}>
                                    🌡️ Target
                                    Tm: {globalParams.reaction_temp + validationSettings.melting_temp.min_offset}°C
                                    - {globalParams.reaction_temp + validationSettings.melting_temp.max_offset}°C
                                </div>
                            </div>
                        </div>

                        {/* Advanced Settings - Collapsible */}
                        {showAdvanced && (
                            <>
                                <div style={{borderTop: '1px solid #ddd', paddingTop: '15px', marginBottom: '15px'}}>
                                    <h4 style={{margin: '0 0 10px 0', color: '#555'}}>Advanced Reaction Parameters</h4>
                                    <div style={{
                                        display: 'grid',
                                        gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                                        gap: '15px'
                                    }}>
                                        <div>
                                            <label style={{
                                                display: 'block',
                                                fontWeight: 'bold',
                                                marginBottom: '5px',
                                                fontSize: '13px'
                                            }}>
                                                Salt (mM):
                                            </label>
                                            <input
                                                type="number"
                                                value={globalParams.salt_conc}
                                                onChange={(e) => setGlobalParams(prev => ({
                                                    ...prev,
                                                    salt_conc: Number(e.target.value)
                                                }))}
                                                style={{
                                                    padding: '6px',
                                                    borderRadius: '4px',
                                                    border: '1px solid #ccc',
                                                    width: '100%',
                                                    fontSize: '13px'
                                                }}
                                            />
                                        </div>
                                        <div>
                                            <label style={{
                                                display: 'block',
                                                fontWeight: 'bold',
                                                marginBottom: '5px',
                                                fontSize: '13px'
                                            }}>
                                                Mg²⁺ (mM):
                                            </label>
                                            <input
                                                type="number"
                                                step="0.1"
                                                value={globalParams.mg_conc}
                                                onChange={(e) => setGlobalParams(prev => ({
                                                    ...prev,
                                                    mg_conc: Number(e.target.value)
                                                }))}
                                                style={{
                                                    padding: '6px',
                                                    borderRadius: '4px',
                                                    border: '1px solid #ccc',
                                                    width: '100%',
                                                    fontSize: '13px'
                                                }}
                                            />
                                        </div>
                                        <div>
                                            <label style={{
                                                display: 'block',
                                                fontWeight: 'bold',
                                                marginBottom: '5px',
                                                fontSize: '13px'
                                            }}>
                                                Oligo (nM):
                                            </label>
                                            <input
                                                type="number"
                                                value={globalParams.oligo_conc}
                                                onChange={(e) => setGlobalParams(prev => ({
                                                    ...prev,
                                                    oligo_conc: Number(e.target.value)
                                                }))}
                                                style={{
                                                    padding: '6px',
                                                    borderRadius: '4px',
                                                    border: '1px solid #ccc',
                                                    width: '100%',
                                                    fontSize: '13px'
                                                }}
                                            />
                                        </div>
                                    </div>
                                </div>

                                <div style={{borderTop: '1px solid #ddd', paddingTop: '15px'}}>
                                    <h4 style={{margin: '0 0 15px 0', color: '#555'}}>Validation Thresholds</h4>

                                    {/* Melting Temperature Settings */}
                                    <div style={{
                                        marginBottom: '15px',
                                        padding: '10px',
                                        backgroundColor: '#fff',
                                        borderRadius: '6px',
                                        border: '1px solid #e0e0e0'
                                    }}>
                                        <div style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '10px',
                                            marginBottom: '8px'
                                        }}>
                                            <input
                                                type="checkbox"
                                                checked={validationSettings.melting_temp.enabled}
                                                onChange={(e) => setValidationSettings(prev => ({
                                                    ...prev,
                                                    melting_temp: {...prev.melting_temp, enabled: e.target.checked}
                                                }))}
                                            />
                                            <label style={{fontWeight: 'bold', fontSize: '14px'}}>Melting Temperature
                                                Range</label>
                                        </div>
                                        {validationSettings.melting_temp.enabled && (
                                            <div style={{display: 'flex', gap: '10px', alignItems: 'center'}}>
                                                <span style={{fontSize: '12px'}}>Offset:</span>
                                                <input
                                                    type="number"
                                                    placeholder="Min"
                                                    value={validationSettings.melting_temp.min_offset}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        melting_temp: {
                                                            ...prev.melting_temp,
                                                            min_offset: Number(e.target.value)
                                                        }
                                                    }))}
                                                    style={{
                                                        padding: '4px',
                                                        borderRadius: '3px',
                                                        border: '1px solid #ccc',
                                                        width: '60px',
                                                        fontSize: '12px'
                                                    }}
                                                />
                                                <span style={{fontSize: '12px'}}>to</span>
                                                <input
                                                    type="number"
                                                    placeholder="Max"
                                                    value={validationSettings.melting_temp.max_offset}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        melting_temp: {
                                                            ...prev.melting_temp,
                                                            max_offset: Number(e.target.value)
                                                        }
                                                    }))}
                                                    style={{
                                                        padding: '4px',
                                                        borderRadius: '3px',
                                                        border: '1px solid #ccc',
                                                        width: '60px',
                                                        fontSize: '12px'
                                                    }}
                                                />
                                                <span style={{fontSize: '12px'}}>°C above reaction temp</span>
                                            </div>
                                        )}
                                    </div>

                                    {/* Hairpin Settings */}
                                    <div style={{
                                        marginBottom: '15px',
                                        padding: '10px',
                                        backgroundColor: '#fff',
                                        borderRadius: '6px',
                                        border: '1px solid #e0e0e0'
                                    }}>
                                        <div style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '10px',
                                            marginBottom: '8px'
                                        }}>
                                            <input
                                                type="checkbox"
                                                checked={validationSettings.hairpin.enabled}
                                                onChange={(e) => setValidationSettings(prev => ({
                                                    ...prev,
                                                    hairpin: {...prev.hairpin, enabled: e.target.checked}
                                                }))}
                                            />
                                            <label style={{fontWeight: 'bold', fontSize: '14px'}}>Hairpin
                                                Formation</label>
                                        </div>
                                        {validationSettings.hairpin.enabled && (
                                            <div style={{display: 'flex', gap: '10px', alignItems: 'center'}}>
                                                <span style={{fontSize: '12px'}}>Max ΔG:</span>
                                                <input
                                                    type="number"
                                                    step="0.1"
                                                    value={validationSettings.hairpin.max_dg}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        hairpin: {...prev.hairpin, max_dg: Number(e.target.value)}
                                                    }))}
                                                    style={{
                                                        padding: '4px',
                                                        borderRadius: '3px',
                                                        border: '1px solid #ccc',
                                                        width: '80px',
                                                        fontSize: '12px'
                                                    }}
                                                />
                                                <span style={{fontSize: '12px'}}>kcal/mol</span>
                                            </div>
                                        )}
                                    </div>

                                    {/* Self Dimerization Settings */}
                                    <div style={{
                                        marginBottom: '15px',
                                        padding: '10px',
                                        backgroundColor: '#fff',
                                        borderRadius: '6px',
                                        border: '1px solid #e0e0e0'
                                    }}>
                                        <div style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '10px',
                                            marginBottom: '8px'
                                        }}>
                                            <input
                                                type="checkbox"
                                                checked={validationSettings.self_dimer.enabled}
                                                onChange={(e) => setValidationSettings(prev => ({
                                                    ...prev,
                                                    self_dimer: {...prev.self_dimer, enabled: e.target.checked}
                                                }))}
                                            />
                                            <label style={{fontWeight: 'bold', fontSize: '14px'}}>Self
                                                Dimerization</label>
                                        </div>
                                        {validationSettings.self_dimer.enabled && (
                                            <div style={{display: 'flex', gap: '10px', alignItems: 'center'}}>
                                                <span style={{fontSize: '12px'}}>Max ΔG:</span>
                                                <input
                                                    type="number"
                                                    step="0.1"
                                                    value={validationSettings.self_dimer.max_dg}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        self_dimer: {...prev.self_dimer, max_dg: Number(e.target.value)}
                                                    }))}
                                                    style={{
                                                        padding: '4px',
                                                        borderRadius: '3px',
                                                        border: '1px solid #ccc',
                                                        width: '80px',
                                                        fontSize: '12px'
                                                    }}
                                                />
                                                <span style={{fontSize: '12px'}}>kcal/mol</span>
                                            </div>
                                        )}
                                    </div>

                                    {/* Cross Dimerization Settings */}
                                    <div style={{
                                        marginBottom: '15px',
                                        padding: '10px',
                                        backgroundColor: '#fff',
                                        borderRadius: '6px',
                                        border: '1px solid #e0e0e0'
                                    }}>
                                        <div style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '10px',
                                            marginBottom: '8px'
                                        }}>
                                            <input
                                                type="checkbox"
                                                checked={validationSettings.cross_dimer.enabled}
                                                onChange={(e) => setValidationSettings(prev => ({
                                                    ...prev,
                                                    cross_dimer: {...prev.cross_dimer, enabled: e.target.checked}
                                                }))}
                                            />
                                            <label style={{fontWeight: 'bold', fontSize: '14px'}}>Cross
                                                Dimerization</label>
                                        </div>
                                        {validationSettings.cross_dimer.enabled && (
                                            <div style={{display: 'flex', gap: '10px', alignItems: 'center'}}>
                                                <span style={{fontSize: '12px'}}>Max ΔG:</span>
                                                <input
                                                    type="number"
                                                    step="0.1"
                                                    value={validationSettings.cross_dimer.max_dg}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        cross_dimer: {
                                                            ...prev.cross_dimer,
                                                            max_dg: Number(e.target.value)
                                                        }
                                                    }))}
                                                    style={{
                                                        padding: '4px',
                                                        borderRadius: '3px',
                                                        border: '1px solid #ccc',
                                                        width: '80px',
                                                        fontSize: '12px'
                                                    }}
                                                />
                                                <span style={{fontSize: '12px'}}>kcal/mol</span>
                                            </div>
                                        )}
                                    </div>

                                    {/* GC Content Settings */}
                                    <div style={{
                                        marginBottom: '15px',
                                        padding: '10px',
                                        backgroundColor: '#fff',
                                        borderRadius: '6px',
                                        border: '1px solid #e0e0e0'
                                    }}>
                                        <div style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '10px',
                                            marginBottom: '8px'
                                        }}>
                                            <input
                                                type="checkbox"
                                                checked={validationSettings.gc_content.enabled}
                                                onChange={(e) => setValidationSettings(prev => ({
                                                    ...prev,
                                                    gc_content: {...prev.gc_content, enabled: e.target.checked}
                                                }))}
                                            />
                                            <label style={{fontWeight: 'bold', fontSize: '14px'}}>GC Content
                                                Range</label>
                                        </div>
                                        {validationSettings.gc_content.enabled && (
                                            <div style={{display: 'flex', gap: '10px', alignItems: 'center'}}>
                                                <input
                                                    type="number"
                                                    placeholder="Min"
                                                    value={validationSettings.gc_content.min_percent}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        gc_content: {
                                                            ...prev.gc_content,
                                                            min_percent: Number(e.target.value)
                                                        }
                                                    }))}
                                                    style={{
                                                        padding: '4px',
                                                        borderRadius: '3px',
                                                        border: '1px solid #ccc',
                                                        width: '60px',
                                                        fontSize: '12px'
                                                    }}
                                                />
                                                <span style={{fontSize: '12px'}}>to</span>
                                                <input
                                                    type="number"
                                                    placeholder="Max"
                                                    value={validationSettings.gc_content.max_percent}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        gc_content: {
                                                            ...prev.gc_content,
                                                            max_percent: Number(e.target.value)
                                                        }
                                                    }))}
                                                    style={{
                                                        padding: '4px',
                                                        borderRadius: '3px',
                                                        border: '1px solid #ccc',
                                                        width: '60px',
                                                        fontSize: '12px'
                                                    }}
                                                />
                                                <span style={{fontSize: '12px'}}>%</span>
                                            </div>
                                        )}
                                    </div>

                                    {/* Future Settings - Disabled for now but ready to enable */}
                                    <div style={{opacity: 0.6}}>
                                        <div style={{
                                            marginBottom: '10px',
                                            padding: '10px',
                                            backgroundColor: '#f8f9fa',
                                            borderRadius: '6px',
                                            border: '1px solid #e0e0e0'
                                        }}>
                                            <div style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                                                <input
                                                    type="checkbox"
                                                    checked={validationSettings.primer_3_end.enabled}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        primer_3_end: {...prev.primer_3_end, enabled: e.target.checked}
                                                    }))}
                                                />
                                                <label style={{fontWeight: 'bold', fontSize: '14px'}}>3′ End Stability
                                                    (Coming Soon)</label>
                                            </div>
                                        </div>

                                        <div style={{
                                            marginBottom: '10px',
                                            padding: '10px',
                                            backgroundColor: '#f8f9fa',
                                            borderRadius: '6px',
                                            border: '1px solid #e0e0e0'
                                        }}>
                                            <div style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                                                <input
                                                    type="checkbox"
                                                    checked={validationSettings.repeats.enabled}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        repeats: {...prev.repeats, enabled: e.target.checked}
                                                    }))}
                                                />
                                                <label style={{fontWeight: 'bold', fontSize: '14px'}}>Repeat Sequences
                                                    (Coming Soon)</label>
                                            </div>
                                        </div>

                                        <div style={{
                                            marginBottom: '10px',
                                            padding: '10px',
                                            backgroundColor: '#f8f9fa',
                                            borderRadius: '6px',
                                            border: '1px solid #e0e0e0'
                                        }}>
                                            <div style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                                                <input
                                                    type="checkbox"
                                                    checked={validationSettings.secondary_structure.enabled}
                                                    onChange={(e) => setValidationSettings(prev => ({
                                                        ...prev,
                                                        secondary_structure: {
                                                            ...prev.secondary_structure,
                                                            enabled: e.target.checked
                                                        }
                                                    }))}
                                                />
                                                <label style={{fontWeight: 'bold', fontSize: '14px'}}>Advanced Secondary
                                                    Structure (Coming Soon)</label>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}
                    </div>
                    {currentStrand.domains.length > 0 && (
                        <div style={{
                            background: '#f8f9fa',
                            padding: '15px',
                            borderRadius: '8px',
                            marginBottom: '20px'
                        }}>
                            <h3 style={{margin: '0 0 10px 0'}}>Current Strand (5′ → 3′)</h3>
                            <div style={{display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap'}}>
                                {currentStrand.domains.map((domain, index) => (
                                    <React.Fragment key={domain.id}>
                                        <div style={{
                                            background: 'linear-gradient(135deg, #007bff, #0056b3)',
                                            color: 'white',
                                            padding: '8px 12px',
                                            borderRadius: '6px',
                                            position: 'relative'
                                        }}>
                                            <div style={{fontWeight: 'bold'}}>{domain.name}</div>
                                            <div style={{fontSize: '12px', opacity: 0.9}}>{domain.length}bp</div>
                                            <button
                                                onClick={() => removeDomain(domain.id)}
                                                style={{
                                                    position: 'absolute',
                                                    top: '-8px',
                                                    right: '-8px',
                                                    background: '#dc3545',
                                                    color: 'white',
                                                    border: 'none',
                                                    borderRadius: '50%',
                                                    width: '20px',
                                                    height: '20px',
                                                    fontSize: '12px',
                                                    cursor: 'pointer'
                                                }}
                                            >
                                                ×
                                            </button>
                                        </div>
                                        {index < currentStrand.domains.length - 1 && <span>→</span>}
                                    </React.Fragment>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Add Domain */}
                    <div style={{
                        border: '2px dashed #ccc',
                        padding: '20px',
                        borderRadius: '8px',
                        marginBottom: '20px'
                    }}>
                        <h3>Add Domain</h3>
                        <div style={{display: 'flex', gap: '10px', alignItems: 'end', marginBottom: '10px'}}>
                            <div>
                                <label style={{display: 'block', fontWeight: 'bold', marginBottom: '5px'}}>
                                    Name:
                                </label>
                                <input
                                    type="text"
                                    value={currentDomain.name}
                                    onChange={(e) => setCurrentDomain(prev => ({...prev, name: e.target.value}))}
                                    placeholder="e.g., Primer, Spacer"
                                    style={{
                                        padding: '8px',
                                        borderRadius: '4px',
                                        border: '1px solid #ccc'
                                    }}
                                />
                            </div>
                            <div>
                                <label style={{display: 'block', fontWeight: 'bold', marginBottom: '5px'}}>
                                    Length (bp):
                                </label>
                                <input
                                    type="number"
                                    value={currentDomain.length}
                                    onChange={(e) => setCurrentDomain(prev => ({
                                        ...prev,
                                        length: Number(e.target.value)
                                    }))}
                                    style={{
                                        padding: '8px',
                                        borderRadius: '4px',
                                        border: '1px solid #ccc',
                                        width: '80px'
                                    }}
                                />
                            </div>
                            <button
                                onClick={addDomain}
                                disabled={!currentDomain.name}
                                style={{
                                    padding: '8px 16px',
                                    backgroundColor: !currentDomain.name ? '#ccc' : '#007bff',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '4px',
                                    cursor: !currentDomain.name ? 'not-allowed' : 'pointer'
                                }}
                            >
                                + Add Domain
                            </button>
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <div style={{display: 'flex', gap: '10px', marginBottom: '20px'}}>
                        <button
                            onClick={generateOligo}
                            disabled={isGenerating || currentStrand.domains.length === 0}
                            style={{
                                padding: '12px 24px',
                                backgroundColor: isGenerating || currentStrand.domains.length === 0 ? '#ccc' : '#28a745',
                                color: 'white',
                                border: 'none',
                                borderRadius: '6px',
                                fontSize: '16px',
                                cursor: isGenerating || currentStrand.domains.length === 0 ? 'not-allowed' : 'pointer',
                                flex: 1
                            }}
                        >
                            {isGenerating ? '🔄 Generating...' : '▶ Generate & Validate'}
                        </button>

                        <button
                            onClick={saveStrand}
                            disabled={currentStrand.domains.length === 0}
                            style={{
                                padding: '12px 24px',
                                backgroundColor: currentStrand.domains.length === 0 ? '#ccc' : '#007bff',
                                color: 'white',
                                border: 'none',
                                borderRadius: '6px',
                                fontSize: '16px',
                                cursor: currentStrand.domains.length === 0 ? 'not-allowed' : 'pointer'
                            }}
                        >
                            💾 Save to Library
                        </button>
                    </div>

                    {/* Error Display */}
                    {error && (
                        <div style={{
                            background: '#f8d7da',
                            color: '#721c24',
                            padding: '12px',
                            borderRadius: '6px',
                            marginBottom: '20px',
                            border: '1px solid #f5c6cb'
                        }}>
                            <strong>Error:</strong> {error}
                        </div>
                    )}

                    {/* Results */}
                    {currentStrand.result && currentStrand.result.success && (
                        <div style={{
                            background: '#f8f9fa',
                            padding: '20px',
                            borderRadius: '8px',
                            border: '1px solid #dee2e6'
                        }}>
                            <h2>Results: {currentStrand.result.strand.name}</h2>

                            <div style={{
                                background: currentStrand.result.validation.overall_pass ? '#d4edda' : '#f8d7da',
                                color: currentStrand.result.validation.overall_pass ? '#155724' : '#721c24',
                                padding: '8px 12px',
                                borderRadius: '4px',
                                marginBottom: '16px',
                                display: 'inline-block'
                            }}>
                                {currentStrand.result.validation.overall_pass ? '✅ All Checks Passed' : '❌ Some Checks Failed'}
                            </div>

                            <div style={{marginBottom: '16px'}}>
                                <strong>Length:</strong> {currentStrand.result.strand.total_length} bp |
                                <strong> Time:</strong> {currentStrand.result.generation_time.toFixed(2)}s
                            </div>

                            <div style={{marginBottom: '16px'}}>
                                <strong>Final Sequence (5′ → 3′):</strong>
                                <div style={{
                                    background: '#fff',
                                    padding: '12px',
                                    marginTop: '8px',
                                    borderRadius: '4px',
                                    fontFamily: 'monospace',
                                    fontSize: '14px',
                                    wordBreak: 'break-all',
                                    border: '1px solid #ccc'
                                }}>
                                    {currentStrand.result.strand.sequence}
                                </div>
                            </div>

                            <h3>Validation Results</h3>
                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                                gap: '12px'
                            }}>
                                {Object.entries(currentStrand.result.validation.checks).map(([checkName, check]) => (
                                    <div key={checkName} style={{
                                        background: check.pass_check ? '#d4edda' : '#f8d7da',
                                        padding: '12px',
                                        borderRadius: '6px',
                                        border: `1px solid ${check.pass_check ? '#c3e6cb' : '#f5c6cb'}`
                                    }}>
                                        <div style={{fontWeight: 'bold', marginBottom: '4px'}}>
                                            {check.pass_check ? '✅' : '❌'} {checkName.replace(/_/g, ' ')}
                                        </div>
                                        <div style={{fontSize: '14px'}}>{check.message}</div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Library Tab */}
            {activeTab === 'library' && (
                <div style={{
                    border: '1px solid #dee2e6',
                    borderTop: 'none',
                    padding: '20px',
                    borderRadius: '0 0 8px 8px',
                    backgroundColor: '#fff'
                }}>
                    {strandLibrary.length === 0 ? (
                        <div style={{textAlign: 'center', padding: '40px', color: '#6c757d'}}>
                            <div style={{fontSize: '48px', marginBottom: '16px'}}>🧬</div>
                            <h3>No strands saved yet</h3>
                            <p>Design and save strands to build your library</p>
                        </div>
                    ) : (
                        <>
                            <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                marginBottom: '20px'
                            }}>
                                <h2 style={{margin: 0}}>Strand Library</h2>
                                <span style={{color: '#6c757d'}}>
                  {strandLibrary.length} strand{strandLibrary.length !== 1 ? 's' : ''}
                </span>
                            </div>

                            <div style={{display: 'flex', flexDirection: 'column', gap: '16px'}}>
                                {strandLibrary.map(strand => (
                                    <div key={strand.id} style={{
                                        border: '1px solid #dee2e6',
                                        borderRadius: '8px',
                                        padding: '16px',
                                        backgroundColor: '#fff'
                                    }}>
                                        <div style={{
                                            display: 'flex',
                                            justifyContent: 'space-between',
                                            alignItems: 'start',
                                            marginBottom: '12px'
                                        }}>
                                            <div>
                                                <h4 style={{margin: '0 0 4px 0', color: '#333'}}>{strand.name}</h4>
                                                <p style={{margin: 0, color: '#6c757d', fontSize: '14px'}}>
                                                    {strand.domains.length} domains • Saved {strand.savedAt}
                                                </p>
                                            </div>
                                            <div style={{display: 'flex', gap: '8px'}}>
                                                <button
                                                    onClick={() => loadStrand(strand)}
                                                    style={{
                                                        padding: '4px 8px',
                                                        backgroundColor: '#007bff',
                                                        color: 'white',
                                                        border: 'none',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer',
                                                        fontSize: '12px'
                                                    }}
                                                    title="Edit strand"
                                                >
                                                    ✏️ Edit
                                                </button>
                                                <button
                                                    onClick={() => duplicateStrand(strand)}
                                                    style={{
                                                        padding: '4px 8px',
                                                        backgroundColor: '#6c757d',
                                                        color: 'white',
                                                        border: 'none',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer',
                                                        fontSize: '12px'
                                                    }}
                                                    title="Duplicate strand"
                                                >
                                                    📋 Copy
                                                </button>
                                                <button
                                                    onClick={() => deleteStrand(strand.id)}
                                                    style={{
                                                        padding: '4px 8px',
                                                        backgroundColor: '#dc3545',
                                                        color: 'white',
                                                        border: 'none',
                                                        borderRadius: '4px',
                                                        cursor: 'pointer',
                                                        fontSize: '12px'
                                                    }}
                                                    title="Delete strand"
                                                >
                                                    🗑️ Delete
                                                </button>
                                            </div>
                                        </div>

                                        {/* Domain Preview */}
                                        <div style={{
                                            display: 'flex',
                                            gap: '8px',
                                            alignItems: 'center',
                                            flexWrap: 'wrap'
                                        }}>
                                            {strand.domains.map((domain, index) => (
                                                <React.Fragment key={domain.id}>
                                                    <div style={{
                                                        background: '#e9ecef',
                                                        color: '#495057',
                                                        padding: '4px 8px',
                                                        borderRadius: '4px',
                                                        fontSize: '12px'
                                                    }}>
                                                        {domain.name} ({domain.length}bp)
                                                    </div>
                                                    {index < strand.domains.length - 1 &&
                                                        <span style={{color: '#6c757d'}}>→</span>}
                                                </React.Fragment>
                                            ))}
                                        </div>

                                        {/* Result Preview */}
                                        {strand.result && (
                                            <div style={{
                                                marginTop: '12px',
                                                paddingTop: '12px',
                                                borderTop: '1px solid #dee2e6'
                                            }}>
                                                <div style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '8px',
                                                    fontSize: '12px'
                                                }}>
                                                    <span style={{fontWeight: 'bold'}}>Last Result:</span>
                                                    <span style={{
                                                        padding: '2px 6px',
                                                        borderRadius: '4px',
                                                        backgroundColor: strand.result.validation?.overall_pass ? '#d4edda' : '#f8d7da',
                                                        color: strand.result.validation?.overall_pass ? '#155724' : '#721c24'
                                                    }}>
                            {strand.result.validation?.overall_pass ? 'Passed' : 'Failed'} Validation
                          </span>
                                                    <span style={{color: '#6c757d'}}>
                            {strand.result.strand?.total_length}bp
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