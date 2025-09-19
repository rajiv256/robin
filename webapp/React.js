import React, {useState} from 'react';
import {Plus, Play, X, ArrowRight, Copy, Trash2, Edit3, Upload} from 'lucide-react';

const OligoDesigner = () => {
    const [strands, setStrands] = useState([]);
    const [currentStrand, setCurrentStrand] = useState({
        id: null,
        name: 'Strand 1',
        domains: [],
        result: null
    });

    const [currentDomain, setCurrentDomain] = useState({
        name: '',
        length: 20,
        sequence: '',
        gcContent: 50
    });

    const [globalParams, setGlobalParams] = useState({
        reactionTemp: 37,
        saltConc: 50,
        mgConc: 2,
        oligoConc: 250
    });

    const [isGenerating, setIsGenerating] = useState(false);
    const [activeTab, setActiveTab] = useState('design');

    const addDomain = () => {
        if (currentDomain.name) {
            const newDomain = {
                ...currentDomain,
                id: Date.now()
            };
            setCurrentStrand(prev => ({
                ...prev,
                domains: [...prev.domains, newDomain]
            }));
            setCurrentDomain({
                name: '',
                length: 20,
                sequence: '',
                gcContent: 50
            });
        }
    };

    const removeDomain = (id) => {
        setCurrentStrand(prev => ({
            ...prev,
            domains: prev.domains.filter(d => d.id !== id)
        }));
    };

    const saveStrand = () => {
        if (currentStrand.domains.length === 0) return;

        const strandToSave = {
            ...currentStrand,
            id: currentStrand.id || Date.now(),
            savedAt: new Date().toLocaleString()
        };

        if (currentStrand.id) {
            setStrands(prev => prev.map(s => s.id === currentStrand.id ? strandToSave : s));
        } else {
            setStrands(prev => [...prev, strandToSave]);
        }

        const nextStrandNumber = strands.length + 2;
        setCurrentStrand({
            id: null,
            name: `Strand ${nextStrandNumber}`,
            domains: [],
            result: null
        });
    };

    const loadStrand = (strand) => {
        setCurrentStrand({
            ...strand,
            result: null
        });
        setActiveTab('design');
    };

    const deleteStrand = (strandId) => {
        setStrands(prev => prev.filter(s => s.id !== strandId));
    };

    const duplicateStrand = (strand) => {
        const duplicated = {
            ...strand,
            id: Date.now(),
            name: `${strand.name} (Copy)`,
            result: null,
            savedAt: new Date().toLocaleString()
        };
        setStrands(prev => [...prev, duplicated]);
    };

    const generateStrand = async () => {
        if (currentStrand.domains.length === 0) return;

        setIsGenerating(true);

        try {
            // Prepare request payload for Python backend
            const requestData = {
                strand_name: currentStrand.name,
                domains: currentStrand.domains.map(domain => ({
                    name: domain.name,
                    length: domain.length,
                    fixed_sequence: domain.sequence || null,
                    target_gc_content: domain.gcContent
                })),
                global_params: {
                    reaction_temp: globalParams.reactionTemp,
                    salt_conc: globalParams.saltConc,
                    mg_conc: globalParams.mgConc,
                    oligo_conc: globalParams.oligoConc
                }
            };

            // This would be your actual API call to Python backend
            const response = await fetch('/api/generate-oligonucleotide', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                throw new Error(`API request failed: ${response.status}`);
            }

            const result = await response.json();

            // Mock response for demo - replace with actual backend response
            const mockResult = {
                success: true,
                strand: {
                    name: currentStrand.name,
                    total_length: 60,
                    sequence: "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",
                    domains: currentStrand.domains.map(domain => ({
                        ...domain,
                        generated_sequence: generateMockSequence(domain.length, domain.gcContent),
                        validation_passed: Math.random() > 0.3
                    }))
                },
                validation: {
                    overall_pass: Math.random() > 0.2,
                    checks: {
                        melting_temperature: {
                            pass: Math.random() > 0.2,
                            value: 55.2,
                            target_range: [42, 62],
                            message: "Within acceptable range"
                        },
                        hairpin_formation: {
                            pass: Math.random() > 0.3,
                            delta_g: -1.8,
                            threshold: -3.0,
                            message: "No significant hairpin structures"
                        },
                        self_dimerization: {
                            pass: Math.random() > 0.25,
                            delta_g: -4.2,
                            threshold: -6.0,
                            message: "Low self-dimerization risk"
                        },
                        cross_dimerization: {
                            pass: Math.random() > 0.3,
                            delta_g: -3.1,
                            threshold: -6.0,
                            message: "Compatible with other strands"
                        },
                        gc_content: {
                            pass: Math.random() > 0.15,
                            value: 52.3,
                            target_range: [40, 60],
                            message: "Optimal GC content"
                        },
                        primer_3_end: {
                            pass: Math.random() > 0.2,
                            delta_g: -2.1,
                            threshold: -3.0,
                            message: "Appropriate 3' end stability"
                        }
                    }
                },
                generation_time: 1.24,
                generated_at: new Date().toISOString()
            };

            setCurrentStrand(prev => ({...prev, result: mockResult}));
            setActiveTab('results');

        } catch (error) {
            console.error('Generation failed:', error);
            alert('Failed to generate strand. Please check your backend connection.');
        }

        setIsGenerating(false);
    };

    const generateMockSequence = (length, gcTarget) => {
        const gcBases = ['G', 'C'];
        const atBases = ['A', 'T'];
        const gcCount = Math.round((gcTarget / 100) * length);
        const atCount = length - gcCount;

        const bases = [
            ...Array(gcCount).fill().map(() => gcBases[Math.floor(Math.random() * 2)]),
            ...Array(atCount).fill().map(() => atBases[Math.floor(Math.random() * 2)])
        ];

        for (let i = bases.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [bases[i], bases[j]] = [bases[j], bases[i]];
        }

        return bases.join('');
    };

    const CheckResult = ({check, label}) => (
        <div className={`p-4 rounded-lg border ${
            check.pass
                ? 'bg-emerald-50 border-emerald-200'
                : 'bg-rose-50 border-rose-200'
        }`}>
            <div className="flex items-center gap-2 mb-2">
                <div className={`w-3 h-3 rounded-full ${check.pass ? 'bg-emerald-500' : 'bg-rose-500'}`}></div>
                <span className="font-medium text-gray-900">{label}</span>
            </div>
            <div className="text-sm text-gray-600">
                {check.message}
            </div>
            <div className="text-xs text-gray-500 mt-1">
                {check.value !== undefined && `Value: ${check.value}`}
                {check.delta_g !== undefined && `ΔG: ${check.delta_g.toFixed(1)} kcal/mol`}
                {check.threshold !== undefined && ` (threshold: ${check.threshold})`}
                {check.target_range && ` (target: ${check.target_range[0]}-${check.target_range[1]})`}
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
            <div className="max-w-6xl mx-auto p-6 space-y-6">

                <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="p-3 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl">
                            <div className="w-6 h-6 text-white font-bold flex items-center justify-center text-lg">◉
                            </div>
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold text-slate-800">Oligonucleotide Designer</h1>
                            <p className="text-slate-600">Design orthogonal DNA strands with backend validation</p>
                        </div>
                    </div>

                    <div className="flex gap-2 mb-6">
                        <button
                            onClick={() => setActiveTab('design')}
                            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                                activeTab === 'design'
                                    ? 'bg-blue-500 text-white'
                                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                            }`}
                        >
                            Design ({currentStrand.domains.length} domains)
                        </button>
                        <button
                            onClick={() => setActiveTab('library')}
                            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                                activeTab === 'library'
                                    ? 'bg-blue-500 text-white'
                                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                            }`}
                        >
                            Strand Library ({strands.length})
                        </button>
                        {currentStrand.result && (
                            <button
                                onClick={() => setActiveTab('results')}
                                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                                    activeTab === 'results'
                                        ? 'bg-blue-500 text-white'
                                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                                }`}
                            >
                                Results
                            </button>
                        )}
                    </div>

                    {activeTab === 'design' && (
                        <>
                            <div className="mb-6">
                                <label className="block text-sm font-medium text-slate-700 mb-2">Strand Name</label>
                                <input
                                    type="text"
                                    value={currentStrand.name}
                                    onChange={(e) => setCurrentStrand(prev => ({...prev, name: e.target.value}))}
                                    className="w-full max-w-md p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                />
                            </div>

                            {currentStrand.domains.length > 0 && (
                                <div className="bg-slate-50 rounded-xl p-4 mb-6">
                                    <div className="flex items-center gap-2 mb-3">
                                        <span
                                            className="text-sm font-medium text-slate-700">Current Strand (5′ → 3′):</span>
                                        <span className="text-xs bg-slate-200 text-slate-600 px-2 py-1 rounded">
                      {currentStrand.domains.length} domain{currentStrand.domains.length !== 1 ? 's' : ''}
                    </span>
                                    </div>
                                    <div className="flex items-center gap-2 flex-wrap">
                                        {currentStrand.domains.map((domain, index) => (
                                            <React.Fragment key={domain.id}>
                                                <div className="group relative">
                                                    <div
                                                        className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white px-3 py-2 rounded-lg text-sm font-medium shadow-sm">
                                                        {domain.name}
                                                        <div className="text-xs opacity-90">{domain.length}bp</div>
                                                        {domain.sequence &&
                                                            <div className="text-xs opacity-75">Fixed</div>}
                                                    </div>
                                                    <button
                                                        onClick={() => removeDomain(domain.id)}
                                                        className="absolute -top-2 -right-2 w-5 h-5 bg-rose-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                                                    >
                                                        <X className="w-3 h-3"/>
                                                    </button>
                                                </div>
                                                {index < currentStrand.domains.length - 1 && (
                                                    <ArrowRight className="w-4 h-4 text-slate-400"/>
                                                )}
                                            </React.Fragment>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div className="bg-gradient-to-r from-slate-50 to-blue-50 rounded-xl p-6 mb-6">
                                <h3 className="font-semibold text-slate-800 mb-4">Reaction Conditions</h3>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 mb-2">Temperature
                                            (°C)</label>
                                        <input
                                            type="number"
                                            value={globalParams.reactionTemp}
                                            onChange={(e) => setGlobalParams(prev => ({
                                                ...prev,
                                                reactionTemp: Number(e.target.value)
                                            }))}
                                            className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 mb-2">Salt
                                            (mM)</label>
                                        <input
                                            type="number"
                                            value={globalParams.saltConc}
                                            onChange={(e) => setGlobalParams(prev => ({
                                                ...prev,
                                                saltConc: Number(e.target.value)
                                            }))}
                                            className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 mb-2">Mg²⁺
                                            (mM)</label>
                                        <input
                                            type="number"
                                            step="0.1"
                                            value={globalParams.mgConc}
                                            onChange={(e) => setGlobalParams(prev => ({
                                                ...prev,
                                                mgConc: Number(e.target.value)
                                            }))}
                                            className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 mb-2">Oligo
                                            (nM)</label>
                                        <input
                                            type="number"
                                            value={globalParams.oligoConc}
                                            onChange={(e) => setGlobalParams(prev => ({
                                                ...prev,
                                                oligoConc: Number(e.target.value)
                                            }))}
                                            className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="border-2 border-dashed border-slate-300 rounded-xl p-6 mb-6">
                                <h3 className="font-semibold text-slate-800 mb-4">Add Domain</h3>
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 mb-2">Domain
                                            Name</label>
                                        <input
                                            type="text"
                                            value={currentDomain.name}
                                            onChange={(e) => setCurrentDomain(prev => ({
                                                ...prev,
                                                name: e.target.value
                                            }))}
                                            placeholder="e.g., Primer, Spacer, Recognition"
                                            className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 mb-2">Length
                                            (bp)</label>
                                        <input
                                            type="number"
                                            value={currentDomain.length}
                                            onChange={(e) => setCurrentDomain(prev => ({
                                                ...prev,
                                                length: Number(e.target.value)
                                            }))}
                                            className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 mb-2">Target
                                            GC%</label>
                                        <input
                                            type="number"
                                            min="0"
                                            max="100"
                                            value={currentDomain.gcContent}
                                            onChange={(e) => setCurrentDomain(prev => ({
                                                ...prev,
                                                gcContent: Number(e.target.value)
                                            }))}
                                            className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-slate-700 mb-2">Action</label>
                                        <button
                                            onClick={addDomain}
                                            disabled={!currentDomain.name}
                                            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-lg hover:from-blue-600 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                                        >
                                            <Plus className="w-4 h-4"/>
                                            Add Domain
                                        </button>
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-2">Fixed Sequence
                                        (optional)</label>
                                    <input
                                        type="text"
                                        value={currentDomain.sequence}
                                        onChange={(e) => setCurrentDomain(prev => ({
                                            ...prev,
                                            sequence: e.target.value.toUpperCase()
                                        }))}
                                        placeholder="Leave blank to generate from orthogonal repository"
                                        className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono"
                                    />
                                    <p className="text-xs text-slate-500 mt-1">
                                        Backend will select from repository of orthogonal sequences if left blank
                                    </p>
                                </div>
                            </div>

                            <div className="flex gap-4">
                                <button
                                    onClick={generateStrand}
                                    disabled={isGenerating || currentStrand.domains.length === 0}
                                    className="flex-1 flex items-center justify-center gap-3 px-6 py-4 bg-gradient-to-r from-emerald-500 to-teal-600 text-white rounded-xl hover:from-emerald-600 hover:to-teal-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                                >
                                    <Play className="w-5 h-5"/>
                                    {isGenerating ? 'Generating & Validating...' : 'Generate Strand'}
                                </button>

                                <button
                                    onClick={saveStrand}
                                    disabled={currentStrand.domains.length === 0}
                                    className="px-6 py-4 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-xl hover:from-blue-600 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                                >
                                    Save to Library
                                </button>
                            </div>
                        </>
                    )}

                    {activeTab === 'library' && (
                        <div className="space-y-4">
                            {strands.length === 0 ? (
                                <div className="text-center py-12">
                                    <div className="text-slate-400 mb-4">
                                        <div
                                            className="w-16 h-16 mx-auto bg-slate-100 rounded-full flex items-center justify-center text-2xl">◉
                                        </div>
                                    </div>
                                    <h3 className="text-lg font-medium text-slate-600 mb-2">No strands saved yet</h3>
                                    <p className="text-slate-500">Design and save strands to build your library</p>
                                </div>
                            ) : (
                                <>
                                    <div className="flex justify-between items-center mb-4">
                                        <h3 className="text-lg font-semibold text-slate-800">Saved Strands</h3>
                                        <span
                                            className="text-sm text-slate-500">{strands.length} strand{strands.length !== 1 ? 's' : ''}</span>
                                    </div>
                                    {strands.map(strand => (
                                        <div key={strand.id}
                                             className="bg-white border border-slate-200 rounded-lg p-4">
                                            <div className="flex justify-between items-start mb-3">
                                                <div>
                                                    <h4 className="font-medium text-slate-800">{strand.name}</h4>
                                                    <p className="text-sm text-slate-500">
                                                        {strand.domains.length} domains • Saved {strand.savedAt}
                                                    </p>
                                                </div>
                                                <div className="flex gap-2">
                                                    <button
                                                        onClick={() => loadStrand(strand)}
                                                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                                                        title="Edit strand"
                                                    >
                                                        <Edit3 className="w-4 h-4"/>
                                                    </button>
                                                    <button
                                                        onClick={() => duplicateStrand(strand)}
                                                        className="p-2 text-slate-600 hover:bg-slate-50 rounded-lg transition-colors"
                                                        title="Duplicate strand"
                                                    >
                                                        <Copy className="w-4 h-4"/>
                                                    </button>
                                                    <button
                                                        onClick={() => deleteStrand(strand.id)}
                                                        className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                                        title="Delete strand"
                                                    >
                                                        <Trash2 className="w-4 h-4"/>
                                                    </button>
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-2 flex-wrap">
                                                {strand.domains.map((domain, index) => (
                                                    <React.Fragment key={domain.id}>
                                                        <div
                                                            className="bg-slate-100 text-slate-700 px-2 py-1 rounded text-xs">
                                                            {domain.name} ({domain.length}bp)
                                                            {domain.sequence &&
                                                                <span className="text-blue-600"> •Fixed</span>}
                                                        </div>
                                                        {index < strand.domains.length - 1 && (
                                                            <ArrowRight className="w-3 h-3 text-slate-400"/>
                                                        )}
                                                    </React.Fragment>
                                                ))}
                                            </div>

                                            {strand.result && (
                                                <div className="mt-3 pt-3 border-t border-slate-200">
                                                    <div className="flex items-center gap-2 mb-2">
                                                        <span className="text-xs font-medium text-slate-600">Last Result:</span>
                                                        <span className={`text-xs px-2 py-1 rounded ${
                                                            strand.result.validation.overall_pass
                                                                ? 'bg-emerald-100 text-emerald-700'
                                                                : 'bg-rose-100 text-rose-700'
                                                        }`}>
                              {strand.result.validation.overall_pass ? 'Passed' : 'Failed'} Validation
                            </span>
                                                        <span className="text-xs text-slate-500">
                              {strand.result.strand.total_length}bp
                            </span>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </>
                            )}
                        </div>
                    )}

                    {activeTab === 'results' && currentStrand.result && (
                        <div className="space-y-6">
                            <div className="flex items-center justify-between">
                                <h2 className="text-xl font-bold text-slate-800">Results: {currentStrand.result.strand.name}</h2>
                                <div className={`px-4 py-2 rounded-full text-sm font-medium ${
                                    currentStrand.result.validation.overall_pass
                                        ? 'bg-emerald-100 text-emerald-800'
                                        : 'bg-rose-100 text-rose-800'
                                }`}>
                                    {currentStrand.result.validation.overall_pass ? 'All Checks Passed' : 'Some Checks Failed'}
                                </div>
                            </div>

                            <div className="bg-gradient-to-r from-slate-50 to-blue-50 rounded-xl p-6">
                                <div className="flex items-center gap-4 mb-4">
                                    <div className="text-sm text-slate-600">
                                        <span
                                            className="font-medium">Total Length:</span> {currentStrand.result.strand.total_length} bp
                                    </div>
                                    <div className="text-sm text-slate-600">
                                        <span
                                            className="font-medium">Domains:</span> {currentStrand.result.strand.domains.length}
                                    </div>
                                    <div className="text-sm text-slate-600">
                                        <span
                                            className="font-medium">Generation Time:</span> {currentStrand.result.generation_time}s
                                    </div>
                                </div>

                                <div className="bg-white rounded-lg p-4 border border-slate-200">
                                    <div className="text-xs text-slate-500 mb-2">5′ → 3′ Final Sequence:</div>
                                    <div className="font-mono text-sm bg-slate-50 p-3 rounded border break-all">
                                        {currentStrand.result.strand.sequence}
                                    </div>
                                </div>
                            </div>

                            <div>
                                <h3 className="font-semibold text-slate-800 mb-4">Domain Breakdown</h3>
                                <div className="space-y-3">
                                    {currentStrand.result.strand.domains.map((domain, index) => (
                                        <div key={domain.id} className="border border-slate-200 rounded-lg p-4">
                                            <div className="flex justify-between items-center mb-2">
                                                <span className="font-medium text-slate-800">{domain.name}</span>
                                                <div className="flex items-center gap-2">
                                                    <span
                                                        className="text-sm text-slate-600">{domain.generated_sequence.length} bp</span>
                                                    <span className={`text-xs px-2 py-1 rounded ${
                                                        domain.validation_passed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                                    }`}>
                            {domain.validation_passed ? 'Valid' : 'Issues'}
                          </span>
                                                </div>
                                            </div>
                                            <div className="font-mono text-sm bg-slate-50 p-2 rounded break-all">
                                                {domain.generated_sequence}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <h3 className="font-semibold text-slate-800 mb-4">Validation Results</h3>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {Object.entries(currentStrand.result.validation.checks).map(([checkName, check]) => {
                                        const labels = {
                                            melting_temperature: 'Melting Temperature',
                                            hairpin_formation: 'Hairpin Formation',
                                            self_dimerization: 'Self Dimerization',
                                            cross_dimerization: 'Cross Dimerization',
                                            gc_content: 'GC Content',
                                            primer_3_end: '3′ End Stability'
                                        };
                                        return (
                                            <CheckResult
                                                key={checkName}
                                                check={check}
                                                label={labels[checkName] || checkName.replace(/_/g, ' ')}
                                            />
                                        );
                                    })}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default OligoDesigner;