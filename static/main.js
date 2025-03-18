async function analyzeLog() {
    const fileInput = document.getElementById('logFile');
    const file = fileInput.files[0];
    
    if (!file) {
        alert('Please select a file first');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        displayResults(data);
    } catch (error) {
        console.error('Error:', error);
        alert('Error analyzing log file');
    }
}

function displayResults(data) {
    // Display process analysis
    const processes = data.processes;
    const processNames = Object.keys(processes);
    
    // Create process chart
    const chartData = [{
        x: processNames,
        y: processNames.map(p => processes[p].total_time),
        type: 'bar',
        name: 'Execution Time (s)'
    }];

    Plotly.newPlot('processChart', chartData, {
        title: 'Process Execution Times',
        xaxis: { title: 'Process' },
        yaxis: { title: 'Time (seconds)' }
    });

    // Display process table
    const tableHTML = `
        <table class="min-w-full">
            <thead>
                <tr>
                    <th class="px-4 py-2">Process</th>
                    <th class="px-4 py-2">Count</th>
                    <th class="px-4 py-2">Total Time (s)</th>
                    <th class="px-4 py-2">Records</th>
                </tr>
            </thead>
            <tbody>
                ${processNames.map(name => `
                    <tr>
                        <td class="border px-4 py-2">${name}</td>
                        <td class="border px-4 py-2">${processes[name].count}</td>
                        <td class="border px-4 py-2">${processes[name].total_time.toFixed(2)}</td>
                        <td class="border px-4 py-2">${processes[name].records_processed}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
    document.getElementById('processTable').innerHTML = tableHTML;

    // Display errors
    const errorHTML = data.errors.length > 0 
        ? data.errors.map(error => `
            <div class="bg-red-100 border-l-4 border-red-500 p-4 mb-4">
                <p class="font-bold">Process: ${error.process}</p>
                <p>Time: ${error.timestamp}</p>
                <p>Message: ${error.message}</p>
            </div>
        `).join('')
        : '<p class="text-green-600">No errors found</p>';
    
    document.getElementById('errorList').innerHTML = errorHTML;
}

async function downloadResults(format) {
    try {
        const response = await fetch(`/download/${format}`);
        if (!response.ok) throw new Error('Download failed');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `analysis_results.${format}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        console.error('Error:', error);
        alert('Error downloading results');
    }
}