const API_BASE_URL = 'http://localhost:5000/api';

export const generateStrand = async (strandData) => {
    try {
        const response = await fetch(`${API_BASE_URL}/generate-oligonucleotide`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(strandData)
        });
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
};