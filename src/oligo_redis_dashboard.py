#!/usr/bin/env python3
"""
Simple web dashboard for visualizing oligonucleotide Redis database
"""

from flask import Flask, render_template_string, jsonify, request
import redis
import json
import numpy as np
from collections import defaultdict, Counter

app = Flask(__name__)

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Oligonucleotide Database Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .card { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }
        .stat-number { font-size: 2em; font-weight: bold; }
        .stat-label { font-size: 0.9em; opacity: 0.9; }
        .search-box { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; }
        .oligo-item { border: 1px solid #eee; padding: 15px; margin: 10px 0; border-radius: 6px; background: #fafafa; }
        .sequence { font-family: 'Courier New', monospace; background: #e8f4f8; padding: 8px; border-radius: 4px; font-weight: bold; }
        .properties { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 10px; }
        .property { background: white; padding: 8px; border-radius: 4px; text-align: center; }
        .chart-container { height: 400px; }
        h1, h2 { color: #333; }
        .filter-controls { display: flex; gap: 10px; margin: 10px 0; flex-wrap: wrap; }
        .filter-input { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
        .btn { padding: 10px 20px; background: #667eea; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .btn:hover { background: #5a6fd8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧬 Oligonucleotide Database Dashboard</h1>

        <!-- Statistics Overview -->
        <div class="card">
            <h2>Database Statistics</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" id="total-oligos">-</div>
                    <div class="stat-label">Total Oligonucleotides</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="avg-length">-</div>
                    <div class="stat-label">Average Length (bp)</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="avg-gc">-</div>
                    <div class="stat-label">Average GC% Content</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="avg-tm">-</div>
                    <div class="stat-label">Average Tm (°C)</div>
                </div>
            </div>
        </div>

        <!-- Charts -->
        <div class="card">
            <h2>Data Visualizations</h2>
            <div class="chart-container" id="length-distribution"></div>
        </div>

        <div class="card">
            <div class="chart-container" id="gc-distribution"></div>
        </div>

        <div class="card">
            <div class="chart-container" id="tm-distribution"></div>
        </div>

        <!-- Search and Filter -->
        <div class="card">
            <h2>Search Oligonucleotides</h2>
            <div class="filter-controls">
                <input type="text" class="filter-input" id="sequence-search" placeholder="Search by sequence...">
                <input type="number" class="filter-input" id="min-length" placeholder="Min length">
                <input type="number" class="filter-input" id="max-length" placeholder="Max length">
                <input type="number" class="filter-input" id="min-gc" placeholder="Min GC%">
                <input type="number" class="filter-input" id="max-gc" placeholder="Max GC%">
                <button class="btn" onclick="searchOligos()">Search</button>
                <button class="btn" onclick="showRandomSample()">Random Sample</button>
            </div>
            <div id="search-results"></div>
        </div>
    </div>

    <script>
        // Load dashboard data on page load
        window.onload = function() {
            loadDashboardData();
            showRandomSample();
        };

        async function loadDashboardData() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();

                // Update statistics
                document.getElementById('total-oligos').textContent = data.total_oligos;
                document.getElementById('avg-length').textContent = data.avg_length.toFixed(1);
                document.getElementById('avg-gc').textContent = data.avg_gc.toFixed(1) + '%';
                document.getElementById('avg-tm').textContent = data.avg_tm.toFixed(1);

                // Create charts
                createLengthChart(data.length_distribution);
                createGCChart(data.gc_distribution);
                createTmChart(data.tm_distribution);

            } catch (error) {
                console.error('Error loading dashboard data:', error);
            }
        }

        function createLengthChart(lengthData) {
            const lengths = Object.keys(lengthData).map(Number).sort((a,b) => a-b);
            const counts = lengths.map(len => lengthData[len]);

            const trace = {
                x: lengths,
                y: counts,
                type: 'bar',
                marker: { color: '#667eea' }
            };

            const layout = {
                title: 'Length Distribution',
                xaxis: { title: 'Length (bp)' },
                yaxis: { title: 'Count' }
            };

            Plotly.newPlot('length-distribution', [trace], layout);
        }

        function createGCChart(gcData) {
            const trace = {
                x: gcData.values,
                type: 'histogram',
                nbinsx: 20,
                marker: { color: '#764ba2' }
            };

            const layout = {
                title: 'GC Content Distribution',
                xaxis: { title: 'GC Content (%)' },
                yaxis: { title: 'Count' }
            };

            Plotly.newPlot('gc-distribution', [trace], layout);
        }

        function createTmChart(tmData) {
            const trace = {
                x: tmData.values,
                type: 'histogram',
                nbinsx: 20,
                marker: { color: '#f093fb' }
            };

            const layout = {
                title: 'Melting Temperature Distribution',
                xaxis: { title: 'Melting Temperature (°C)' },
                yaxis: { title: 'Count' }
            };

            Plotly.newPlot('tm-distribution', [trace], layout);
        }

        async function searchOligos() {
            const filters = {
                sequence: document.getElementById('sequence-search').value,
                min_length: document.getElementById('min-length').value,
                max_length: document.getElementById('max-length').value,
                min_gc: document.getElementById('min-gc').value,
                max_gc: document.getElementById('max-gc').value
            };

            const queryString = new URLSearchParams(filters).toString();
            const response = await fetch(`/api/search?${queryString}`);
            const results = await response.json();

            displayOligos(results.oligos);
        }

        async function showRandomSample() {
            const response = await fetch('/api/sample');
            const results = await response.json();
            displayOligos(results.oligos);
        }

        function displayOligos(oligos) {
            const container = document.getElementById('search-results');

            if (oligos.length === 0) {
                container.innerHTML = '<p>No oligonucleotides found matching your criteria.</p>';
                return;
            }

            const html = oligos.map(oligo => `
                <div class="oligo-item">
                    <div class="sequence">${oligo.sequence}</div>
                    <div class="properties">
                        <div class="property">
                            <strong>Length</strong><br>${oligo.length} bp
                        </div>
                        <div class="property">
                            <strong>GC Content</strong><br>${oligo.gc_content}%
                        </div>
                        <div class="property">
                            <strong>Tm</strong><br>${oligo.melting_temp}°C
                        </div>
                        <div class="property">
                            <strong>Hairpin ΔG</strong><br>${oligo.hairpin_dg} kcal/mol
                        </div>
                        <div class="property">
                            <strong>Homodimer ΔG</strong><br>${oligo.homodimer_dg} kcal/mol
                        </div>
                        <div class="property">
                            <strong>Complexity</strong><br>${oligo.complexity}
                        </div>
                    </div>
                </div>
            `).join('');

            container.innerHTML = html;
        }
    </script>
</body>
</html>
"""


@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/stats')
def get_stats():
    """Get database statistics"""
    try:
        # Get all oligo IDs
        oligo_ids = list(redis_client.smembers('oligo:all'))

        if not oligo_ids:
            return jsonify({'error': 'No oligonucleotides found'})

        # Sample oligonucleotides for statistics
        sample_size = min(1000, len(oligo_ids))
        sample_ids = np.random.choice(oligo_ids, sample_size, replace=False)

        lengths = []
        gc_contents = []
        tms = []
        length_dist = defaultdict(int)

        for oligo_id in sample_ids:
            data = redis_client.hget(f"oligo:{oligo_id}", 'data')
            if data:
                oligo_data = json.loads(data)
                lengths.append(oligo_data['length'])
                gc_contents.append(oligo_data['gc_content'])
                tms.append(oligo_data['melting_temp'])
                length_dist[oligo_data['length']] += 1

        return jsonify({
            'total_oligos': len(oligo_ids),
            'avg_length': np.mean(lengths),
            'avg_gc': np.mean(gc_contents),
            'avg_tm': np.mean(tms),
            'length_distribution': dict(length_dist),
            'gc_distribution': {'values': gc_contents},
            'tm_distribution': {'values': tms}
        })

    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/search')
def search_oligos():
    """Search oligonucleotides with filters"""
    try:
        # Get filter parameters
        sequence_filter = request.args.get('sequence', '').upper()
        min_length = request.args.get('min_length', type=int)
        max_length = request.args.get('max_length', type=int)
        min_gc = request.args.get('min_gc', type=float)
        max_gc = request.args.get('max_gc', type=float)

        # Get all oligo IDs
        oligo_ids = list(redis_client.smembers('oligo:all'))
        matching_oligos = []

        for oligo_id in oligo_ids[:100]:  # Limit to 100 for performance
            data = redis_client.hget(f"oligo:{oligo_id}", 'data')
            if data:
                oligo_data = json.loads(data)

                # Apply filters
                if sequence_filter and sequence_filter not in oligo_data['sequence']:
                    continue
                if min_length and oligo_data['length'] < min_length:
                    continue
                if max_length and oligo_data['length'] > max_length:
                    continue
                if min_gc and oligo_data['gc_content'] < min_gc:
                    continue
                if max_gc and oligo_data['gc_content'] > max_gc:
                    continue

                matching_oligos.append(oligo_data)

        return jsonify({'oligos': matching_oligos[:20]})  # Return top 20 matches

    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/sample')
def get_sample():
    """Get random sample of oligonucleotides"""
    try:
        oligo_ids = list(redis_client.smembers('oligo:all'))

        if not oligo_ids:
            return jsonify({'oligos': []})

        # Get random sample
        sample_size = min(10, len(oligo_ids))
        sample_ids = np.random.choice(oligo_ids, sample_size, replace=False)

        oligos = []
        for oligo_id in sample_ids:
            data = redis_client.hget(f"oligo:{oligo_id}", 'data')
            if data:
                oligos.append(json.loads(data))

        return jsonify({'oligos': oligos})

    except Exception as e:
        return jsonify({'error': str(e)})


if __name__ == '__main__':
    print("Starting Oligonucleotide Dashboard...")
    print("Open http://localhost:5010 in your browser")
    app.run(debug=True, host='localhost', port=5010)