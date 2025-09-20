// OligoDesigner.jsx
import React, {useState, useEffect} from 'react';
import './OligoDesigner.css';

const OligoDesigner = () => {
    const [activeTab, setActiveTab] = useState('domains');
    const [domains, setDomains] = useState([]);
    const [strands, setStrands] = useState([]);
    const [selectedStrands, setSelectedStrands] = useState([]);
    const [results, setResults] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Domain cache - stores name and length pairs
    const [domainCache, setDomainCache] = useState(new Map());

    const [domainName, setDomainName] = useState('');
    const [domainLength, setDomainLength] = useState('20');
    const [strandName, setStrandName] = useState('');
    const [strandDomains, setStrandDomains] = useState('');

    const [settings, setSettings] = useState({
        temp: 37,
        gc_min: 30,
        gc_max: 70,
        tm_min: 40,
        tm_max: 80,
        hairpin_dg: -2.0,
        self_dimer_dg: -5.0,
        cross_dimer_dg: -8.0
    });

    const API_BASE = 'http://localhost:5000/api';

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const domainsResponse = await fetch(`${API_BASE}/domains`);
            const strandsResponse = await fetch(`${API_BASE}/strands`);
            const cacheResponse = await fetch(`${API_BASE}/domain-cache`);

            if (!domainsResponse.ok || !strandsResponse.ok || !cacheResponse.ok) {
                throw new Error('Server not responding');
            }

            const domainsData = await domainsResponse.json();
            const strandsData = await strandsResponse.json();
            const cacheData = await cacheResponse.json();

            setDomains(domainsData);
            setStrands(strandsData);

            // Convert cache array to Map
            const cacheMap = new Map();
            cacheData.forEach(item => {
                cacheMap.set(item.name, item.length);
            });
            setDomainCache(cacheMap);
            setError(''); // Clear any previous errors
        } catch (err) {
            console.log('Server not available, starting with empty state');
            // Start completely empty - no mock data
            setDomains([]);
            setStrands([]);
            setDomainCache(new Map());
            setError('Server not available. Please start the Flask backend.');
        }
    };

    const addDomain = async () => {
        if (!domainName.trim()) {
            setError('Domain name is required');
            return;
        }

        const baseName = domainName.trim().replace('*', '');
        const length = parseInt(domainLength);

        if (!length || length < 1 || length > 100) {
            setError('Domain length must be between 1 and 100');
            return;
        }

        // Check if domain is already in cache
        if (domainCache.has(baseName)) {
            setError(`Domain "${baseName}" already exists in cache with length ${domainCache.get(baseName)}`);
            return;
        }

        setError('');

        try {
            const response = await fetch(`${API_BASE}/domains`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    name: baseName,
                    length: length
                })
            });

            if (response.ok) {
                // Update domain cache
                setDomainCache(prev => new Map(prev.set(baseName, length)));
                setDomainName('');
                setDomainLength('20');
                loadData();
            } else {
                const result = await response.json();
                setError(result.error || 'Failed to add domain');
            }
        } catch (err) {
            setError('Network error: Unable to connect to server');
        }
    };

    const addStrand = async () => {
        if (!strandName.trim() || !strandDomains.trim()) {
            setError('Strand name and domains are required');
            return;
        }

        const domainList = strandDomains.split(',').map(d => d.trim()).filter(d => d);

        // Validate that all domains exist in cache
        const invalidDomains = [];
        domainList.forEach(domainName => {
            const baseName = domainName.replace('*', '');
            if (!domainCache.has(baseName)) {
                invalidDomains.push(baseName);
            }
        });

        if (invalidDomains.length > 0) {
            setError(`Unknown domains: ${invalidDomains.join(', ')}. Add them to the domain cache first.`);
            return;
        }

        try {
            const response = await fetch(`${API_BASE}/strands`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    name: strandName.trim(),
                    domains: domainList
                })
            });

            if (response.ok) {
                setStrandName('');
                setStrandDomains('');
                setError('');
                loadData();
            } else {
                const result = await response.json();
                setError(result.error || 'Failed to add strand');
            }
        } catch (err) {
            setError('Failed to add strand');
        }
    };

    const generateStrands = async () => {
        if (selectedStrands.length === 0) {
            setError('Select at least one strand to generate');
            return;
        }

        setLoading(true);
        setError('');

        try {
            const response = await fetch(`${API_BASE}/generate-strands`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    settings,
                    strand_ids: selectedStrands
                })
            });

            const result = await response.json();

            if (response.ok) {
                setResults(result);
                loadData();
            } else {
                setError(result.error || 'Generation failed');
            }
        } catch (err) {
            setError('Failed to generate strands');
        } finally {
            setLoading(false);
        }
    };

    const checkCrossDimers = async () => {
        if (selectedStrands.length < 2) {
            setError('Select at least 2 strands to check cross-dimers');
            return;
        }

        setLoading(true);
        setError('');

        try {
            const response = await fetch(`${API_BASE}/check-cross-dimers`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    settings,
                    strand_ids: selectedStrands
                })
            });

            const result = await response.json();

            if (response.ok) {
                setResults(result);
            } else {
                setError(result.error || 'Cross-dimer check failed');
            }
        } catch (err) {
            setError('Failed to check cross-dimers');
        } finally {
            setLoading(false);
        }
    };

    const deleteItem = async (type, id) => {
        try {
            const response = await fetch(`${API_BASE}/${type}/${id}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                loadData();
            } else {
                setError(`Failed to delete ${type}`);
            }
        } catch (err) {
            setError(`Failed to delete ${type}`);
        }
    };

    const removeDomainFromCache = async (domainName) => {
        try {
            const response = await fetch(`${API_BASE}/domain-cache/${domainName}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                setDomainCache(prev => {
                    const newCache = new Map(prev);
                    newCache.delete(domainName);
                    return newCache;
                });
                loadData(); // Reload to remove any actual domain instances
            } else {
                setError('Failed to remove domain from cache');
            }
        } catch (err) {
            setError('Failed to remove domain from cache');
        }
    };

    const toggleStrandSelection = (id) => {
        setSelectedStrands(prev =>
            prev.includes(id)
                ? prev.filter(item => item !== id)
                : [...prev, id]
        );
    };

    // Check if the current domain name exists in cache
    const isExistingDomain = domainCache.has(domainName.trim().replace('*', ''));
    const existingDomainLength = isExistingDomain ? domainCache.get(domainName.trim().replace('*', '')) : null;

    return (
        <div className="oligo-designer">
            <h1 className="header">OligoDesigner - Strand Design System</h1>

            {error && (
                <div className="error">
                    {error}
                </div>
            )}

            {/* Domain Cache Display */}
            {domainCache.size > 0 && (
                <div className="domain-cache">
                    <h3 className="domain-cache-title">Domain Cache
                        ({domainCache.size * 2} domains: {domainCache.size} base + {domainCache.size} complements)</h3>
                    <div className="domain-cache-list">
                        {Array.from(domainCache.entries()).map(([name, length]) => (
                            <React.Fragment key={name}>
                                <div className="cached-domain">
                                    {name} ({length}nt)
                                    <button
                                        onClick={() => removeDomainFromCache(name)}
                                        style={{
                                            marginLeft: '8px',
                                            background: 'none',
                                            border: 'none',
                                            color: '#dc2626',
                                            cursor: 'pointer'
                                        }}
                                    >
                                        ×
                                    </button>
                                </div>
                                <div className="cached-domain">
                                    {name}* ({length}nt)
                                    <span style={{marginLeft: '8px', fontSize: '0.75rem', color: '#6b7280'}}>
                                        complement
                                    </span>
                                </div>
                            </React.Fragment>
                        ))}
                    </div>
                </div>
            )}

            {/* Settings Panel */}
            <div className="settings-panel">
                <div className="settings-header">
                    <h3>Generation Settings</h3>
                </div>

                <div className="settings-grid">
                    <div className="form-group">
                        <label className="form-label">Temperature (°C)</label>
                        <input
                            type="number"
                            className="form-input"
                            value={settings.temp}
                            onChange={(e) => setSettings(prev => ({...prev, temp: parseInt(e.target.value)}))}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Min GC (%)</label>
                        <input
                            type="number"
                            className="form-input"
                            value={settings.gc_min}
                            onChange={(e) => setSettings(prev => ({...prev, gc_min: parseInt(e.target.value)}))}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Max GC (%)</label>
                        <input
                            type="number"
                            className="form-input"
                            value={settings.gc_max}
                            onChange={(e) => setSettings(prev => ({...prev, gc_max: parseInt(e.target.value)}))}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Min Tm (°C)</label>
                        <input
                            type="number"
                            className="form-input"
                            value={settings.tm_min}
                            onChange={(e) => setSettings(prev => ({...prev, tm_min: parseInt(e.target.value)}))}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Max Tm (°C)</label>
                        <input
                            type="number"
                            className="form-input"
                            value={settings.tm_max}
                            onChange={(e) => setSettings(prev => ({...prev, tm_max: parseInt(e.target.value)}))}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Cross-dimer ΔG</label>
                        <input
                            type="number"
                            step="0.1"
                            className="form-input"
                            value={settings.cross_dimer_dg}
                            onChange={(e) => setSettings(prev => ({
                                ...prev,
                                cross_dimer_dg: parseFloat(e.target.value)
                            }))}
                        />
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="tabs">
                <div className="tabs-nav">
                    {['domains', 'strands'].map(tab => (
                        <button
                            key={tab}
                            className={`tab-button ${activeTab === tab ? 'active' : 'inactive'}`}
                            onClick={() => setActiveTab(tab)}
                        >
                            {tab.charAt(0).toUpperCase() + tab.slice(1)}
                        </button>
                    ))}
                </div>
            </div>

            {/* Domains Tab */}
            {activeTab === 'domains' && (
                <div className="tab-content">
                    <div className="add-form">
                        <h3 className="add-form-title">Add Domain to Cache</h3>
                        <div className="add-form-grid">
                            <div className="form-group">
                                <label className="form-label">Domain Name</label>
                                <input
                                    type="text"
                                    className="form-input"
                                    value={domainName}
                                    onChange={(e) => setDomainName(e.target.value)}
                                    placeholder="e.g., a, b, c"
                                />
                                {isExistingDomain && (
                                    <div className="add-form-note" style={{color: '#059669'}}>
                                        Domain exists in cache with length {existingDomainLength}nt
                                    </div>
                                )}
                            </div>
                            <div className="form-group">
                                <label className="form-label">Length (nt)</label>
                                <input
                                    type="number"
                                    className="form-input"
                                    value={isExistingDomain ? existingDomainLength : domainLength}
                                    onChange={(e) => setDomainLength(e.target.value)}
                                    min="10"
                                    max="50"
                                    disabled={isExistingDomain}
                                />
                            </div>
                            <button
                                className="btn btn-primary"
                                onClick={addDomain}
                                disabled={isExistingDomain}
                            >
                                {isExistingDomain ? 'Already in Cache' : 'Add to Cache'}
                            </button>
                        </div>
                        <div className="add-form-note">
                            Domains are added to cache first. Use "Generate Domain Sequences" to create sequences for
                            all cached domains.
                            Individual domains are not validated - only complete strand sequences are validated.
                        </div>
                    </div>

                    {/*<div className="library-header">*/}
                    {/*    <h2 className="library-title">Domain Instances</h2>*/}
                    {/*    <span className="library-count">{domains.length} instances</span>*/}
                    {/*</div>*/}

                    {domains.length === 0 ? (
                        <div className="library-empty">
                            <div className="library-empty-icon">🧬</div>
                            <p>No domain instances created yet</p>
                            <p>Add domains to cache and generate strands to create instances</p>
                        </div>
                    ) : (
                        <div className="library-list">
                            {domains.map(domain => (
                                <div key={domain.id} className="library-item">
                                    <div className="library-item-header">
                                        <div className="library-item-info">
                                            <h4>
                                                {domain.name}
                                                {domain.name.endsWith('*') && (
                                                    <span className="complement-badge">(complement)</span>
                                                )}
                                            </h4>
                                            <p className="library-item-meta">Length: {domain.length}nt</p>
                                        </div>
                                        <div className="library-actions">
                                            <button
                                                className="btn btn-danger"
                                                onClick={() => deleteItem('domains', domain.id)}
                                            >
                                                Delete
                                            </button>
                                        </div>
                                    </div>
                                    {domain.sequence && (
                                        <div className="library-sequence">
                                            <strong>Sequence:</strong>
                                            <div className="sequence-box">{domain.sequence}</div>
                                        </div>
                                    )}
                                    {domain.sequence && (
                                        <div className="library-result">
                                            <span className="status-badge status-valid">
                                                Generated
                                            </span>
                                            <span className="result-meta">
                                                Length: {domain.sequence.length}nt
                                            </span>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Strands Tab */}
            {activeTab === 'strands' && (
                <div className="tab-content">
                    <div className="add-form">
                        <h3 className="add-form-title">Add Strand</h3>
                        <div className="add-form-grid add-form-grid-strands">
                            <div className="form-group">
                                <label className="form-label">Strand Name</label>
                                <input
                                    type="text"
                                    className="form-input"
                                    value={strandName}
                                    onChange={(e) => setStrandName(e.target.value)}
                                    placeholder="e.g., S1, Reporter"
                                />
                            </div>
                            <div className="form-group">
                                <label className="form-label">Domains (comma-separated)</label>
                                <input
                                    type="text"
                                    className="form-input"
                                    value={strandDomains}
                                    onChange={(e) => setStrandDomains(e.target.value)}
                                    placeholder="e.g., a, b*, c"
                                />
                            </div>
                            <button
                                className="btn btn-primary"
                                onClick={addStrand}
                            >
                                Add Strand
                            </button>
                        </div>
                        <div className="add-form-note">
                            Use * to indicate complement domains (e.g., a*). All domains must exist in cache.
                        </div>
                    </div>

                    <div className="library-header">
                        <h2 className="library-title">Strand Library</h2>
                        <span className="library-count">{strands.length} strands</span>
                    </div>

                    {strands.length === 0 ? (
                        <div className="library-empty">
                            <div className="library-empty-icon">🧬</div>
                            <p>No strands defined yet</p>
                        </div>
                    ) : (
                        <div className="library-list">
                            {strands.map(strand => (
                                <div key={strand.id} className="library-item">
                                    <div className="library-item-header">
                                        <div className="library-item-info">
                                            <div className="library-item-name">
                                                <input
                                                    type="checkbox"
                                                    checked={selectedStrands.includes(strand.id)}
                                                    onChange={() => toggleStrandSelection(strand.id)}
                                                    className="library-item-checkbox"
                                                />
                                                <h4>{strand.name}</h4>
                                            </div>
                                            <p className="library-item-meta">
                                                Domains: {strand.domains ? strand.domains.join(' → ') : 'No domains'}
                                            </p>
                                        </div>
                                        <div className="library-actions">
                                            <button
                                                className="btn btn-danger"
                                                onClick={() => deleteItem('strands', strand.id)}
                                            >
                                                Delete
                                            </button>
                                        </div>
                                    </div>
                                    <div className="library-domains">
                                        {strand.domains && strand.domains.map((domain, idx) => (
                                            <span key={idx} className="domain-tag">{domain}</span>
                                        ))}
                                    </div>
                                    {strand.sequence && (
                                        <div className="library-sequence">
                                            <strong>Sequence:</strong>
                                            <div className="sequence-box">{strand.sequence}</div>
                                        </div>
                                    )}
                                    {strand.validation_results && strand.validation_results.overall_valid !== undefined && (
                                        <div className="library-result">
                                            <span className={`status-badge ${
                                                strand.validation_results.overall_valid ? 'status-valid' : 'status-invalid'
                                            }`}>
                                                {strand.validation_results.overall_valid ? 'Valid' : 'Invalid'}
                                            </span>
                                            <span className="result-meta">
                                                Length: {strand.sequence ? strand.sequence.length : 0}nt
                                            </span>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}

                    {strands.length > 0 && (
                        <div className="action-buttons">
                            <button
                                className="btn btn-success"
                                onClick={generateStrands}
                                disabled={loading || selectedStrands.length === 0}
                            >
                                {loading ? 'Building...' : `Build Strands (${selectedStrands.length})`}
                            </button>
                            <button
                                className="btn btn-primary"
                                onClick={checkCrossDimers}
                                disabled={loading || selectedStrands.length < 2}
                            >
                                {loading ? 'Checking...' : 'Check Cross-Dimers'}
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* Results Section */}
            {results && (
                <div className="results">
                    <h2 className="results-title">
                        {results.type === 'cross-dimer' ? 'Cross-Dimer Analysis' : 'Strand Generation Results'}
                    </h2>

                    <div className={`results-status ${results.success ? 'success' : 'fail'}`}>
                        {results.success ? 'Analysis Complete' : 'Analysis Failed'}
                    </div>

                    {results.message && (
                        <div className="results-message">
                            <strong>Status:</strong> {results.message}
                        </div>
                    )}

                    {results.cross_dimer_results && (
                        <div className="results-section">
                            <h3 className="results-section-title">Cross-Dimer Interactions</h3>
                            <div className="results-list">
                                {results.cross_dimer_results.map((interaction, idx) => (
                                    <div key={idx} className="result-item">
                                        <div className="result-item-header">
                                            <span className="result-item-name">
                                                {interaction.strand1} ↔ {interaction.strand2}
                                            </span>
                                            <div className="result-item-info">
                                                <span className="result-meta">
                                                    ΔG: {interaction.dg?.toFixed(2) || 'N/A'} kcal/mol
                                                </span>
                                                <span className={`status-badge ${
                                                    interaction.problematic ? 'status-invalid' : 'status-valid'
                                                }`}>
                                                    {interaction.problematic ? 'Problematic' : 'OK'}
                                                </span>
                                            </div>
                                        </div>
                                        {interaction.problematic && interaction.reason && (
                                            <div className="validation-messages">
                                                <strong>Issue:</strong>
                                                <div style={{fontSize: '0.875rem', color: '#dc2626', marginTop: '4px'}}>
                                                    {interaction.reason}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {results.generated_strands && (
                        <div className="results-section">
                            <h3 className="results-section-title">Generated Strands</h3>
                            <div className="results-list">
                                {results.generated_strands.map((strand, idx) => (
                                    <div key={idx} className="result-item">
                                        <div className="result-item-header">
                                            <span className="result-item-name">{strand.name}</span>
                                            <div className="result-item-info">
                                                <span className="result-meta">{strand.length}nt</span>
                                                <span className={`status-badge ${
                                                    strand.valid ? 'status-valid' : 'status-invalid'
                                                }`}>
                                                    {strand.valid ? 'Valid' : 'Invalid'}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="result-item-sequence">{strand.sequence}</div>
                                        {!strand.valid && strand.validation_messages && strand.validation_messages.length > 0 && (
                                            <div className="validation-messages">
                                                <strong>Validation Issues:</strong>
                                                <ul style={{margin: '4px 0', paddingLeft: '20px'}}>
                                                    {strand.validation_messages.map((message, i) => (
                                                        <li key={i} style={{fontSize: '0.875rem', color: '#dc2626'}}>
                                                            {message}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {results.errors && results.errors.length > 0 && (
                        <div className="results-section">
                            <h3 className="results-section-title">Errors</h3>
                            {results.errors.map((error, idx) => (
                                <div key={idx} className="error">
                                    {error}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default OligoDesigner;