document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const fileInfo = document.getElementById('fileInfo');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const fileSizeDisplay = document.getElementById('fileSizeDisplay');
    const btnRemoveFile = document.getElementById('btnRemoveFile');
    const btnUpload = document.getElementById('btnUpload');

    const statusCard = document.getElementById('statusCard');
    const jobStatusBadge = document.getElementById('jobStatusBadge');
    const jobIdText = document.getElementById('jobIdText');
    const progressBar = document.getElementById('progressBar');
    const statusMessageText = document.getElementById('statusMessageText');
    const timeElapsed = document.getElementById('timeElapsed');
    const fileFormatBadge = document.getElementById('fileFormatBadge');

    const emptyResultState = document.getElementById('emptyResultState');
    const metadataGrid = document.getElementById('metadataGrid');
    const metaWords = document.getElementById('metaWords');
    const metaLang = document.getElementById('metaLang');
    const metaReadTime = document.getElementById('metaReadTime');
    const metaParser = document.getElementById('metaParser');

    const textContainer = document.getElementById('textContainer');
    const extractedTextarea = document.getElementById('extractedTextarea');
    const resultActions = document.getElementById('resultActions');
    const btnCopyText = document.getElementById('btnCopyText');
    const btnDownloadText = document.getElementById('btnDownloadText');

    const btnRunBenchmark = document.getElementById('btnRunBenchmark');
    const benchmarkContainer = document.getElementById('benchmarkContainer');
    const benchmarkContent = document.getElementById('benchmarkContent');
    const btnRefreshHistory = document.getElementById('btnRefreshHistory');
    const historyTableBody = document.getElementById('historyTableBody');

    let selectedFile = null;
    let currentJobId = null;
    let pollInterval = null;
    let startTime = null;

    // --- Drag & Drop Event Handlers ---
    dropZone.addEventListener('click', () => fileInput.click());

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    function handleFileSelect(file) {
        selectedFile = file;
        fileNameDisplay.textContent = file.name;
        fileSizeDisplay.textContent = `(${(file.size / (1024 * 1024)).toFixed(2)} MB)`;
        
        dropZone.querySelector('.drop-zone-content').classList.add('hidden');
        fileInfo.classList.remove('hidden');
        btnUpload.disabled = false;
    }

    btnRemoveFile.addEventListener('click', (e) => {
        e.stopPropagation();
        selectedFile = null;
        fileInput.value = '';
        dropZone.querySelector('.drop-zone-content').classList.remove('hidden');
        fileInfo.classList.add('hidden');
        btnUpload.disabled = true;
    });

    // --- Upload & Processing Flow ---
    btnUpload.addEventListener('click', async () => {
        if (!selectedFile) return;

        const formData = new FormData();
        formData.append('file', selectedFile);

        btnUpload.disabled = true;
        btnUpload.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Subiendo...';

        try {
            const response = await fetch('/api/v1/documents/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'Error en la subida del archivo');
            }

            const data = await response.json();
            currentJobId = data.job_id;
            
            // Iniciar UI de seguimiento
            showStatusCard(data);
            startPollingStatus(currentJobId);
            fetchJobHistory();

        } catch (err) {
            alert(`Error: ${err.message}`);
        } finally {
            btnUpload.disabled = false;
            btnUpload.innerHTML = '<i class="fa-solid fa-bolt"></i> Procesar Documento';
        }
    });

    function showStatusCard(data) {
        statusCard.classList.remove('hidden');
        jobIdText.textContent = `ID: ${data.job_id}`;
        fileFormatBadge.textContent = data.file_format.toUpperCase();
        updateBadge(data.status);
        progressBar.style.width = '10%';
        statusMessageText.textContent = data.status_message;

        emptyResultState.classList.remove('hidden');
        metadataGrid.classList.add('hidden');
        textContainer.classList.add('hidden');
        resultActions.classList.add('hidden');
        benchmarkContainer.classList.add('hidden');
        btnRunBenchmark.classList.add('hidden');

        startTime = Date.now();
    }

    function startPollingStatus(jobId) {
        if (pollInterval) clearInterval(pollInterval);

        pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/v1/jobs/${jobId}`);
                if (!res.ok) return;

                const job = await res.json();
                updateJobUI(job);

                // Actualizar cronómetro
                if (startTime) {
                    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                    timeElapsed.textContent = `${elapsed}s`;
                }

                if (job.status === 'COMPLETED') {
                    clearInterval(pollInterval);
                    if (job.processing_duration_sec) {
                        timeElapsed.textContent = `${job.processing_duration_sec}s`;
                    }
                    fetchJobResult(jobId);
                    fetchJobHistory();
                } else if (job.status === 'FAILED') {
                    clearInterval(pollInterval);
                    statusMessageText.textContent = `Error: ${job.error_message || 'Fallo en el procesamiento'}`;
                    fetchJobHistory();
                }
            } catch (e) {
                console.error('Error durante polling:', e);
            }
        }, 1000);
    }

    function updateJobUI(job) {
        updateBadge(job.status);
        progressBar.style.width = `${job.progress_percent}%`;
        statusMessageText.textContent = job.status_message;
    }

    function updateBadge(statusStr) {
        jobStatusBadge.className = 'badge';
        jobStatusBadge.textContent = statusStr;

        if (statusStr === 'PENDING') jobStatusBadge.classList.add('badge-pending');
        else if (statusStr === 'PROCESSING') jobStatusBadge.classList.add('badge-processing');
        else if (statusStr === 'COMPLETED') jobStatusBadge.classList.add('badge-completed');
        else if (statusStr === 'FAILED') jobStatusBadge.classList.add('badge-failed');
    }

    async function fetchJobResult(jobId) {
        try {
            const res = await fetch(`/api/v1/jobs/${jobId}/result`);
            if (!res.ok) return;

            const data = await res.json();

            // Ocultar estado vacío y mostrar resultados
            emptyResultState.classList.add('hidden');
            metadataGrid.classList.remove('hidden');
            textContainer.classList.remove('hidden');
            resultActions.classList.remove('hidden');

            extractedTextarea.value = data.extracted_text || 'Sin contenido de texto detectado.';

            const meta = data.extracted_metadata || {};
            metaWords.textContent = meta.word_count || 0;
            metaLang.textContent = (meta.detected_language || 'N/A').toUpperCase();
            metaReadTime.textContent = `${meta.estimated_reading_time_min || 0} min`;
            metaParser.textContent = meta.parser_used || 'General';

            btnRunBenchmark.classList.remove('hidden');

        } catch (e) {
            console.error('Error obteniendo resultado:', e);
        }
    }

    // --- Actions: Copy & Download ---
    btnCopyText.addEventListener('click', () => {
        extractedTextarea.select();
        navigator.clipboard.writeText(extractedTextarea.value);
        btnCopyText.innerHTML = '<i class="fa-solid fa-check"></i> ¡Copiado!';
        setTimeout(() => {
            btnCopyText.innerHTML = '<i class="fa-solid fa-copy"></i> Copiar';
        }, 2000);
    });

    btnDownloadText.addEventListener('click', () => {
        const text = extractedTextarea.value;
        const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `extraido_${currentJobId || 'documento'}.txt`;
        a.click();
        URL.revokeObjectURL(url);
    });

    // --- Benchmark Runner ---
    btnRunBenchmark.addEventListener('click', async () => {
        if (!currentJobId) return;

        btnRunBenchmark.disabled = true;
        btnRunBenchmark.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Evaluando Parseadores...';

        try {
            const res = await fetch(`/api/v1/jobs/${currentJobId}/benchmark`);
            if (!res.ok) throw new Error('Error ejecutando benchmark');

            const benchData = await res.json();
            renderBenchmarkResults(benchData);

        } catch (e) {
            alert(`Benchmark Error: ${e.message}`);
        } finally {
            btnRunBenchmark.disabled = false;
            btnRunBenchmark.innerHTML = '<i class="fa-solid fa-stopwatch"></i> Ejecutar Benchmark de Parseadores';
        }
    });

    function renderBenchmarkResults(benchData) {
        benchmarkContainer.classList.remove('hidden');
        benchmarkContent.innerHTML = '';

        benchData.results.forEach(res => {
            const div = document.createElement('div');
            div.className = 'bench-item';
            div.innerHTML = `
                <div>
                    <strong>${res.parser_name}</strong>
                    <div style="font-size:0.75rem; color:var(--text-muted);">${res.notes}</div>
                </div>
                <div style="text-align:right;">
                    <span style="font-weight:700; color:var(--accent-cyan);">${res.extraction_time_sec}s</span>
                    <div style="font-size:0.75rem;">${res.words_extracted} palabras</div>
                </div>
            `;
            benchmarkContent.appendChild(div);
        });
    }

    // --- History Table Loading ---
    async function fetchJobHistory() {
        try {
            const res = await fetch('/api/v1/jobs?limit=15');
            if (!res.ok) return;

            const data = await res.json();
            renderHistoryTable(data.jobs);
        } catch (e) {
            console.error('Error cargando historial:', e);
        }
    }

    function renderHistoryTable(jobs) {
        if (jobs.length === 0) {
            historyTableBody.innerHTML = '<tr><td colspan="8" class="text-center">No hay trabajos registrados.</td></tr>';
            return;
        }

        historyTableBody.innerHTML = jobs.map(j => `
            <tr>
                <td style="font-family:monospace; font-size:0.8rem;">${j.job_id.substring(0, 8)}...</td>
                <td><strong>${j.filename}</strong></td>
                <td><span class="badge" style="background:rgba(255,255,255,0.08);">${j.file_format.toUpperCase()}</span></td>
                <td>${(j.file_size_bytes / 1024).toFixed(1)} KB</td>
                <td><span class="badge badge-${j.status.toLowerCase()}">${j.status}</span></td>
                <td>${j.processing_duration_sec ? j.processing_duration_sec + 's' : '-'}</td>
                <td>${new Date(j.created_at).toLocaleTimeString()}</td>
                <td>
                    <button onclick="inspectJob('${j.job_id}')" class="btn-secondary" style="padding:0.2rem 0.5rem; font-size:0.75rem;">
                        <i class="fa-solid fa-eye"></i> Ver
                    </button>
                </td>
            </tr>
        `).join('');
    }

    window.inspectJob = (jobId) => {
        currentJobId = jobId;
        startPollingStatus(jobId);
        fetchJobResult(jobId);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    };

    btnRefreshHistory.addEventListener('click', fetchJobHistory);

    // Cargar historial al iniciar
    fetchJobHistory();
});
