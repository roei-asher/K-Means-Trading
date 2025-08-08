const socket = new WebSocket('ws://localhost:8765');

socket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'historical_data') {
        processHistoricalData(data);
    }
};

document.getElementById('dataForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const tickers = document.getElementById('tickers').value.split(',').map(t => t.trim());
    const barSize = document.getElementById('barSize').value;
    const duration = document.getElementById('duration').value;
    const rth = document.getElementById('rth').checked;

    socket.send(JSON.stringify({
        type: 'get_historical_data',
        tickers: tickers,
        barSize: barSize,
        duration: duration,
        rth: rth
    }));
});

// function processHistoricalData(data) {
//     const resultsDiv = document.getElementById('results');
//     resultsDiv.innerHTML = '';

//     data.tickers.forEach(ticker => {
//         const tickerDiv = document.createElement('div');
//         tickerDiv.className = 'ticker-section';
//         tickerDiv.innerHTML = `
//             <h2>${ticker}</h2>
//             <div id="price-chart-${ticker}" class="chart"></div>
//             <div id="kde-chart-${ticker}" class="chart"></div>
//             <div id="gains-chart-${ticker}" class="chart"></div>
//             <div id="losses-chart-${ticker}" class="chart"></div>
//         `;
//         resultsDiv.appendChild(tickerDiv);
//     });

//     // After creating all elements, render the charts
//     data.tickers.forEach(ticker => {
//         if (data[ticker].error) {
//             document.getElementById(`price-chart-${ticker}`).innerHTML = `<p class="error">Error: ${data[ticker].error}</p>`;
//         } else {
//             createPriceChart(ticker, data[ticker]);
//             createKDEChart(ticker, data[ticker]);
//             createGainsLossesCharts(ticker, data[ticker]);
//             createStatsTable(ticker, data[ticker]);
//         }
//     });
// }
function processHistoricalData(data) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '';

    data.tickers.forEach(ticker => {
        const tickerDiv = document.createElement('div');
        tickerDiv.className = 'ticker-section';
        tickerDiv.innerHTML = `
            <h2>${ticker} - Recommended Action: ${data[ticker].action}</h2>
            <select id="chart-type-${ticker}">
                <option value="candlestick">Candlestick</option>
                <option value="line">Closing Price</option>
                <option value="scatter">All Prices Scatter</option>
            </select>
            <label><input type="checkbox" id="show-boundaries-${ticker}" checked> Show Boundaries</label>
            <label><input type="checkbox" id="show-current-sector-${ticker}"> Current Sector</label>
            <div id="price-chart-${ticker}" class="chart full-width"></div>
            <div id="kde-chart-${ticker}" class="chart full-width"></div>
            <div id="gains-losses-chart-${ticker}" class="chart full-width"></div>
            <div id="stats-tables-${ticker}" class="stats-tables"></div>
        `;
        resultsDiv.appendChild(tickerDiv);

        if (data[ticker].error) {
            document.getElementById(`price-chart-${ticker}`).innerHTML = `<p class="error">Error: ${data[ticker].error}</p>`;
        } else {
            createPriceChart(ticker, data[ticker]);
            createKDEChart(ticker, data[ticker]);
            createGainsLossesChart(ticker, data[ticker]);
            createStatsTables(ticker, data[ticker]);

            document.getElementById(`chart-type-${ticker}`).addEventListener('change', (event) => {
                createPriceChart(ticker, data[ticker], event.target.value);
            });

            document.getElementById(`show-boundaries-${ticker}`).addEventListener('change', (event) => {
                updateBoundaryVisibility(ticker, event.target.checked);
            });

            document.getElementById(`show-current-sector-${ticker}`).addEventListener('change', (event) => {
                updateCurrentSectorView(ticker, data[ticker], event.target.checked);
            });
        }
    });
}


// function createPriceChart(ticker, data) {
//     const trace = {
//         x: data.dates,
//         close: data.close,
//         high: data.high,
//         low: data.low,
//         open: data.open,
//         type: 'candlestick',
//         xaxis: 'x',
//         yaxis: 'y'
//     };

//     const layout = {
//         dragmode: 'zoom',
//         showlegend: false,
//         title: `${ticker} Price Chart`,
//         xaxis: {
//             rangeslider: {visible: false},
//             title: 'Date'
//         },
//         yaxis: {
//             title: 'Price'
//         }
//     };

//     Plotly.newPlot(`price-chart-${ticker}`, [trace], layout);
// }

function createPriceChart(ticker, data, chartType = 'candlestick') {
    let traces = [];
    const sectorBoundaries = data.sectors.map(sector => sector.max_bound);
    const clusterColors = generateClusterColors(data.sectors.length);

    if (chartType === 'candlestick') {
        traces.push({
            x: data.dates,
            close: data.close,
            high: data.high,
            low: data.low,
            open: data.open,
            type: 'candlestick',
            xaxis: 'x',
            yaxis: 'y'
        });
    } else if (chartType === 'line') {
        // Create a single trace for the entire line
        const trace = {
            x: data.dates,
            y: data.close,
            type: 'scatter',
            mode: 'lines',
            line: {width: 2},
            name: 'Closing Price'
        };

        // Color the line segments based on sectors
        let colors = [];
        let segments = [];

        for (let i = 0; i < data.close.length; i++) {
            const price = data.close[i];
            let sectorIndex = data.sectors.findIndex(sector => price < sector.max_bound);
            if (sectorIndex === -1) sectorIndex = data.sectors.length - 1;

            colors.push(clusterColors[sectorIndex]);
            segments.push(i);
        }

        trace.line.color = colors;
        trace.line.shape = 'hv';
        trace.x = [data.dates[0]].concat(data.dates);
        trace.y = [data.close[0]].concat(data.close);
        trace.line.smoothing = 1.3;

        traces.push(trace);
    } else if (chartType === 'scatter') {
        traces.push({
            x: data.dates,
            y: data.close,
            type: 'scatter',
            mode: 'markers',
            marker: {
                color: data.close.map(price => {
                    for (let i = 0; i < data.sectors.length; i++) {
                        if (price < data.sectors[i].max_bound) {
                            return clusterColors[i];
                        }
                    }
                    return clusterColors[clusterColors.length - 1];
                })
            },
            name: 'Closing Prices'
        });
    }

    // Add sector areas
    data.sectors.forEach((sector, index) => {
        traces.push({
            x: [data.dates[0], data.dates[data.dates.length - 1]],
            y: [sector.min_bound, sector.min_bound],
            fill: 'tonexty',
            fillcolor: `rgba(${index * 50}, ${index * 50}, ${index * 50}, 0.1)`,
            line: {width: 0},
            name: `Sector ${index + 1}`,
            showlegend: false
        });
    });

    // Add sector boundary lines
    sectorBoundaries.forEach((boundary, index) => {
        traces.push({
            x: [data.dates[0], data.dates[data.dates.length - 1]],
            y: [boundary, boundary],
            type: 'scatter',
            mode: 'lines',
            line: {
                color: 'red',
                width: 1,
                dash: 'dash'
            },
            name: `Sector ${index + 1} Boundary: ${boundary.toFixed(2)}`,
            visible: true
        });
    });

    // Add current price cursor
    const currentPrice = data.close[data.close.length - 1];
    traces.push({
        x: [data.dates[data.dates.length - 1], data.dates[data.dates.length - 1]],
        y: [currentPrice.toFixed(2), currentPrice.toFixed(2)],
        type: 'scatter',
        mode: 'lines',
        line: {
            color: 'blue',
            width: 2
        },
        name: `Current Price: ${currentPrice.toFixed(2)}`
    });

    const layout = {
        dragmode: 'zoom',
        showlegend: true,
        title: {
            text: `${ticker} Price Chart`,
            font: { size: 24, weight: 'bold' }
        },
        xaxis: {
            rangeslider: {visible: false},
            title: 'Date'
        },
        yaxis: {
            title: 'Price',
            range: [Math.min(...data.low), Math.max(...data.high)]
        },
        width: document.getElementById(`price-chart-${ticker}`).offsetWidth,
        height: 600
    };

    Plotly.newPlot(`price-chart-${ticker}`, traces, layout);

    // Call addSectorStatisticsTable only if the table doesn't exist
    if (!document.getElementById(`sector-stats-table-${ticker}`)) {
        addSectorStatisticsTable(ticker, data);
    }
}

function updateCurrentSectorView(ticker, data, showCurrentSector) {
    const chart = document.getElementById(`price-chart-${ticker}`);
    const currentPrice = data.close[data.close.length - 1];
    const currentSector = data.sectors.find(sector => currentPrice >= sector.min_bound && currentPrice < sector.max_bound);

    if (showCurrentSector && currentSector) {
        Plotly.relayout(chart, {
            'yaxis.range': [currentSector.min_bound, currentSector.max_bound]
        });
    } else {
        Plotly.relayout(chart, {
            'yaxis.range': [Math.min(...data.low), Math.max(...data.high)]
        });
    }
}

function addSectorStatisticsTable(ticker, data) {
    const totalPoints = data.close.length;
    const sectorStats = data.sectors.map((sector, index) => {
        const pointsInSector = data.close.filter(price =>
            price >= (index > 0 ? data.sectors[index-1].max_bound : -Infinity) &&
            price < sector.max_bound
        ).length;
        const percentage = (pointsInSector / totalPoints * 100).toFixed(2);
        return { sector: index + 1, points: pointsInSector, percentage: percentage };
    });

    const table = document.createElement('table');
    table.innerHTML = `
        <tr>
            <th>Sector</th>
            <th>Data Points</th>
            <th>Percentage</th>
        </tr>
        ${sectorStats.map(stat => `
            <tr>
                <td>${stat.sector}</td>
                <td>${stat.points}</td>
                <td>${stat.percentage}%</td>
            </tr>
        `).join('')}
    `;

    table.id = `sector-stats-table-${ticker}`;

    const chartDiv = document.getElementById(`price-chart-${ticker}`);
    chartDiv.parentNode.insertBefore(table, chartDiv.nextSibling);
}


// function createKDEChart(ticker, data) {
//     const traces = data.sectors.map((sector, i) => ({
//         x: sector.kdeX,
//         y: sector.kdeY,
//         type: 'scatter',
//         mode: 'lines',
//         name: `Sector ${i + 1}`
//     }));

//     const layout = {
//         title: `${ticker} KDE by Sector`,
//         xaxis: {title: 'Price'},
//         yaxis: {title: 'Density'},
//         showlegend: true
//     };

//     Plotly.newPlot(`kde-chart-${ticker}`, traces, layout);
// }

function createKDEChart(ticker, data) {
    const chartDiv = document.getElementById(`kde-chart-${ticker}`);
    const width = chartDiv.offsetWidth;
    const height = 400;
    const margin = {top: 20, right: 30, bottom: 30, left: 40};

    // Clear previous chart
    chartDiv.innerHTML = '';

    const svg = d3.select(chartDiv)
        .append("svg")
        .attr("width", width)
        .attr("height", height)
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    const x = d3.scaleLinear()
        .domain([d3.min(data.sectors, s => s.min_bound), d3.max(data.sectors, s => s.max_bound)])
        .range([0, width - margin.left - margin.right]);

    const y = d3.scaleLinear()
        .domain([0, d3.max(data.sectors, s => d3.max(s.kdeY))])
        .range([height - margin.top - margin.bottom, 0]);

    // Add X axis
    svg.append("g")
        .attr("transform", `translate(0,${height - margin.top - margin.bottom})`)
        .call(d3.axisBottom(x));

    // Add Y axis
    svg.append("g")
        .call(d3.axisLeft(y));

    // Color scale for sectors
    const color = d3.scaleOrdinal(d3.schemeCategory10);

    // Draw KDE for each sector
    data.sectors.forEach((sector, i) => {
        const area = d3.area()
            .x(d => x(d[0]))
            .y0(y(0))
            .y1(d => y(d[1]));

        svg.append("path")
            .datum(d3.zip(sector.kdeX, sector.kdeY))
            .attr("fill", color(i))
            .attr("fill-opacity", 0.3)
            .attr("stroke", color(i))
            .attr("stroke-width", 2)
            .attr("d", area);

        // Add vertical line for expected value
        svg.append("line")
            .attr("x1", x(sector.expected_value))
            .attr("x2", x(sector.expected_value))
            .attr("y1", y(0))
            .attr("y2", y(d3.max(sector.kdeY)))
            .attr("stroke", color(i))
            .attr("stroke-dasharray", "4")
            .attr("stroke-width", 2);
    });

    // Add vertical line for current price
    const currentPrice = data.close[data.close.length - 1];
    svg.append("line")
        .attr("x1", x(currentPrice))
        .attr("x2", x(currentPrice))
        .attr("y1", y(0))
        .attr("y2", y(d3.max(data.sectors, s => d3.max(s.kdeY))))
        .attr("stroke", "blue")
        .attr("stroke-width", 2);

    // Add legend
    const legend = svg.append("g")
        .attr("font-family", "sans-serif")
        .attr("font-size", 10)
        .attr("text-anchor", "end")
        .selectAll("g")
        .data(data.sectors.map((_, i) => `Sector ${i + 1}`))
        .enter().append("g")
        .attr("transform", (d, i) => `translate(0,${i * 20})`);

    legend.append("rect")
        .attr("x", width - margin.right - 19)
        .attr("width", 19)
        .attr("height", 19)
        .attr("fill", (d, i) => color(i));

    legend.append("text")
        .attr("x", width - margin.right - 24)
        .attr("y", 9.5)
        .attr("dy", "0.32em")
        .text(d => d);
}

function integrate(x, y) {
    let sum = 0;
    for (let i = 1; i < x.length; i++) {
        sum += (x[i] - x[i-1]) * (y[i] + y[i-1]) / 2;
    }
    return sum;
}


// function createGainsLossesCharts(ticker, data) {
//     const gains = data.close.map((close, i) => i > 0 ? Math.max(0, close - data.close[i-1]) : 0);
//     const losses = data.close.map((close, i) => i > 0 ? Math.min(0, close - data.close[i-1]) : 0);

//     const gainsTrace = {
//         x: data.dates,
//         y: gains,
//         type: 'bar',
//         name: 'Gains',
//         marker: {color: 'greenyellow'}
//     };

//     const lossesTrace = {
//         x: data.dates,
//         y: losses,
//         type: 'bar',
//         name: 'Losses',
//         marker: {color: 'red'}
//     };

//     const gainsLayout = {
//         title: `${ticker} Gains`,
//         xaxis: {title: 'Date'},
//         yaxis: {title: 'Gain'}
//     };

//     const lossesLayout = {
//         title: `${ticker} Losses`,
//         xaxis: {title: 'Date'},
//         yaxis: {title: 'Loss'}
//     };

//     Plotly.newPlot(`gains-chart-${ticker}`, [gainsTrace], gainsLayout);
//     Plotly.newPlot(`losses-chart-${ticker}`, [lossesTrace], lossesLayout);
// }

function createGainsLossesChart(ticker, data) {
    const changes = data.close.map((close, i) => i > 0 ? close - data.close[i-1] : 0);

    const trace = {
        x: data.dates.slice(1),
        y: changes.slice(1),
        type: 'bar',
        name: 'Price Change',
        marker: {
            color: changes.slice(1).map(change => change >= 0 ? 'green' : 'red')
        }
    };

    const layout = {
        title: {
            text: `${ticker} Price Changes`,
            font: {size: 24, weight: 'bold'}
        },
        xaxis: {title: 'Date'},
        yaxis: {title: 'Price Change'},
        width: document.getElementById(`gains-losses-chart-${ticker}`).offsetWidth,
        height: 800,
        bargap: 0.25  // Adjust this value to change the width of the bars
    };

    Plotly.newPlot(`gains-losses-chart-${ticker}`, [trace], layout);
}

// function updateBoundaryVisibility(ticker, visible) {
//     Plotly.restyle(`price-chart-${ticker}`, {
//         visible: visible
//     }, Array.from({length: data.sectors.length}, (_, i) => i + data.sectors.length + 1));
// }
function updateBoundaryVisibility(ticker, visible) {
    const chart = document.getElementById(`price-chart-${ticker}`);
    const data = chart.data;
    const boundaryTraces = data.filter(trace => trace.name && trace.name.includes('Boundary'));

    Plotly.restyle(chart, {
        visible: visible
    }, boundaryTraces.map((_, i) => data.indexOf(boundaryTraces[i])));
}

function generateClusterColors(numClusters) {
    return Array.from({length: numClusters}, (_, i) =>
        `hsl(${(i * 360 / numClusters) % 360}, 70%, 50%)`
    );
}

// function createStatsTable(ticker, data) {
//     const stats = calculateStats(data);
//     const table = document.createElement('table');
//     table.className = 'stats-table';

//     const headers = ['Statistic', 'Value'];
//     const headerRow = table.insertRow();
//     headers.forEach(header => {
//         const th = document.createElement('th');
//         th.textContent = header;
//         headerRow.appendChild(th);
//     });

//     Object.entries(stats).forEach(([key, value]) => {
//         const row = table.insertRow();
//         const keyCell = row.insertCell();
//         const valueCell = row.insertCell();
//         keyCell.textContent = key;
//         valueCell.textContent = typeof value === 'number' ? value.toFixed(2) : value;
//     });

//     // Find the correct ticker section
//     const tickerSections = document.querySelectorAll('.ticker-section');
//     let tickerSection;
//     for (let section of tickerSections) {
//         if (section.querySelector('h2').textContent === ticker) {
//             tickerSection = section;
//             break;
//         }
//     }

//     if (tickerSection) {
//         tickerSection.appendChild(table);
//     } else {
//         console.error(`Ticker section for ${ticker} not found`);
//     }
// }

function createStatsTables(ticker, data) {
    const stats = calculateStats(data);
    const tablesContainer = document.getElementById(`stats-tables-${ticker}`);

    const basicStatsTable = createTable('Basic Statistics', [
        'Minimum', 'Mean', 'Median', 'Mode', 'Maximum',
        '1 Std Dev Range', '2 Std Dev Range', '3 Std Dev Range'
    ], stats);

    const advancedStatsTable = createTable('Advanced Statistics', [
        'Weighted Average', 'Min Volume', 'Avg Volume', 'Max Volume',
        'Average Gain [%]', 'Average Loss [%]', 'Max Gain [%]', 'Max Loss [%]', 'Buy and Hold Return [%]'
    ], stats);

    tablesContainer.appendChild(basicStatsTable);
    tablesContainer.appendChild(advancedStatsTable);
}

function createTable(title, rows, stats) {
    const table = document.createElement('table');
    table.className = 'stats-table';
    table.innerHTML = `<caption>${title}</caption>`;

    rows.forEach(row => {
        const tr = table.insertRow();
        tr.insertCell().textContent = row;
        const value = stats[row];
        tr.insertCell().textContent = typeof value === 'number' ? value.toFixed(2) : value;
    });

    return table;
}

// function calculateStats(data) {
//     const close = data.close;
//     const volume = data.volume;
//     const returns = close.map((price, i) => i > 0 ? (price - close[i-1]) / close[i-1] : 0);

//     return {
//         'Mean': mean(close),
//         'Min': Math.min(...close),
//         'Max': Math.max(...close),
//         'Mode': mode(close),
//         'Median': median(close),
//         'Standard Deviation': standardDeviation(close),
//         'Weighted Average': weightedAverage(close),
//         'Avg Volume': mean(volume),
//         'Min Volume': Math.min(...volume),
//         'Max Volume': Math.max(...volume),
//         'Average Gain': mean(returns.filter(r => r > 0)),
//         'Average Loss': mean(returns.filter(r => r < 0)),
//         'Max Gain': Math.max(...returns),
//         'Max Loss': Math.min(...returns),
//         'Buy and Hold Return': (close[close.length - 1] - close[0]) / close[0]
//     };
// }

function calculateStats(data) {
    const close = data.close;
    const volume = data.volume;
    const changes = close.slice(1).map((price, i) => (price - close[i]) / close[i] * 100);
    const gains = changes.filter(change => change > 0);
    const losses = changes.filter(change => change < 0);

    const mean = close.reduce((a, b) => a + b) / close.length;
    const stdDev = Math.sqrt(close.reduce((sq, n) => sq + Math.pow(n - mean, 2), 0) / close.length);

    return {
        'Minimum': Math.min(...close).toFixed(2),
        'Mean': mean.toFixed(2),
        'Median': median(close).toFixed(2),
        'Mode': mode(close).toFixed(2),
        'Maximum': Math.max(...close).toFixed(2),
        '1 Std Dev Range': `${(mean - stdDev).toFixed(2)} - ${(mean + stdDev).toFixed(2)}`,
        '2 Std Dev Range': `${(mean - 2*stdDev).toFixed(2)} - ${(mean + 2*stdDev).toFixed(2)}`,
        '3 Std Dev Range': `${(mean - 3*stdDev).toFixed(2)} - ${(mean + 3*stdDev).toFixed(2)}`,
        'Weighted Average': weightedAverage(close).toFixed(2),
        'Min Volume': Math.min(...volume).toFixed(0),
        'Avg Volume': (volume.reduce((a, b) => a + b) / volume.length).toFixed(0),
        'Max Volume': Math.max(...volume).toFixed(0),
        'Average Gain [%]': (gains.reduce((a, b) => a + b, 0) / gains.length || 0).toFixed(2),
        'Average Loss [%]': (Math.abs(losses.reduce((a, b) => a + b, 0) / losses.length) || 0).toFixed(2),
        'Max Gain [%]': Math.max(...gains, 0).toFixed(2),
        'Max Loss [%]': Math.abs(Math.min(...losses, 0)).toFixed(2),
        'Buy and Hold Return [%]': ((close[close.length - 1] - close[0]) / close[0] * 100).toFixed(2)
    };
}

// Helper functions for statistics calculations
function mean(arr) {
    return arr.reduce((a, b) => a + b) / arr.length;
}

function median(arr) {
    const sorted = arr.slice().sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function mode(arr) {
    const counts = {};
    let maxCount = 0;
    let mode;
    for (const num of arr) {
        counts[num] = (counts[num] || 0) + 1;
        if (counts[num] > maxCount) {
            maxCount = counts[num];
            mode = num;
        }
    }
    return mode;
}

function standardDeviation(arr) {
    const avg = mean(arr);
    const squareDiffs = arr.map(value => Math.pow(value - avg, 2));
    return Math.sqrt(mean(squareDiffs));
}

function weightedAverage(arr) {
    const weights = arr.map((_, i) => i + 1);
    const weightedSum = arr.reduce((sum, value, i) => sum + value * weights[i], 0);
    const weightSum = weights.reduce((a, b) => a + b);
    return weightedSum / weightSum;
}