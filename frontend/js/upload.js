// State Management
const UPLOAD_CONFIG = {
    ALLOWED_EXTENSIONS: ['.jpg', '.jpeg', '.png', '.pdf'],
    MAX_FILE_SIZE_MB: 10,
    MAX_BATCH_SIZE: 10
};

let queuedFiles = [];

document.addEventListener('DOMContentLoaded', () => {
    initUploadEvents();

    // Listen to Auth State changes broadcasted by auth.js
    window.addEventListener('app:authenticated', (e) => {
        const { isGuest } = e.detail;
        setupGuestSidebar(isGuest);
    });
});

// 1. Guest-Aware Sidebar Control
function setupGuestSidebar(isGuest) {
    const historyWrapper = document.getElementById('history-nav-wrapper');
    const historyBtn = document.getElementById('nav-history-btn');
    const lockBadge = document.getElementById('history-lock-badge');

    if (isGuest) {
        historyWrapper.classList.add('is-guest');
        historyBtn.classList.add('disabled');
        lockBadge.classList.remove('hidden');
    } else {
        historyWrapper.classList.remove('is-guest');
        historyBtn.classList.remove('disabled');
        lockBadge.classList.add('hidden');
    }
}

// Tab Switcher
function switchMainTab(tabName) {
    const isGuest = localStorage.getItem('isGuest') === 'true';

    if (tabName === 'history' && isGuest) {
        showUploadAlert(
            'Document history is unavailable in Guest Mode.',
            'error'
        );
        return;
    }

    document.querySelectorAll('.tab-page').forEach(el => {
        el.classList.remove('active');
        el.classList.add('hidden');
    });

    document.querySelectorAll('.nav-item').forEach(el => {
        el.classList.remove('active');
    });

    const targetTab = document.getElementById(`tab-${tabName}`);
    const targetNav = document.querySelector(
        `.nav-item[data-tab="${tabName}"]`
    );

    if (targetTab) {
        targetTab.classList.remove('hidden');
        targetTab.classList.add('active');

        // Some tabs, such as preprocessing, don't have
        // a sidebar navigation item.
        if (targetNav) {
            targetNav.classList.add('active');
        }
    }
}

// Global event prevention to stop the browser from opening dropped files in a new tab
['dragover', 'drop'].forEach(eventName => {
    window.addEventListener(eventName, (e) => e.preventDefault(), false);
});

function initUploadEvents() {
    const dropzone = document.getElementById('dropzoneContainer');
    const fileInput = document.getElementById('fileInput');

    if (!dropzone || !fileInput) return;

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('drag-over');
    });

    dropzone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('drag-over');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('drag-over');
        
        const droppedFiles = Array.from(e.dataTransfer.files);
        handleIncomingFiles(droppedFiles);
    });

    fileInput.addEventListener('change', (e) => {
        const selectedFiles = Array.from(e.target.files);
        handleIncomingFiles(selectedFiles);
        fileInput.value = ''; // Reset input so re-selecting same file works
    });
}

function handleIncomingFiles(files) {
    showUploadAlert('', 'hidden');

    if (queuedFiles.length + files.length > UPLOAD_CONFIG.MAX_BATCH_SIZE) {
        showUploadAlert(`Cannot exceed maximum batch limit of ${UPLOAD_CONFIG.MAX_BATCH_SIZE} files.`, 'error');
        return;
    }

    let addedCount = 0;
    files.forEach(file => {
        const ext = '.' + file.name.split('.').pop().toLowerCase();

        if (!UPLOAD_CONFIG.ALLOWED_EXTENSIONS.includes(ext)) {
            showUploadAlert(`Invalid file "${file.name}". Allowed: ${UPLOAD_CONFIG.ALLOWED_EXTENSIONS.join(', ')}`, 'error');
            return;
        }

        const fileSizeMB = file.size / (1024 * 1024);
        if (fileSizeMB > UPLOAD_CONFIG.MAX_FILE_SIZE_MB) {
            showUploadAlert(`File "${file.name}" exceeds limit of ${UPLOAD_CONFIG.MAX_FILE_SIZE_MB} MB.`, 'error');
            return;
        }

        // Prevent exact duplicate files in queue
        if (queuedFiles.some(f => f.name === file.name && f.size === file.size)) {
            return;
        }

        queuedFiles.push(file);
        addedCount++;
    });

    if (addedCount > 0) {
        renderQueueList();
    }
}

function renderQueueList() {
    const queueList = document.getElementById('queueList');
    const queueCount = document.getElementById('queueCount');
    const btnClear = document.getElementById('btnClearQueue');
    const btnProceed = document.getElementById('btnProceedPreprocessing');

    queueCount.textContent = queuedFiles.length;

    if (queuedFiles.length === 0) {
        queueList.innerHTML = `
            <div class="queue-empty-state" id="emptyQueueState">
                <span class="empty-icon">📁</span>
                <p>No documents queued for processing</p>
            </div>`;
        btnClear.classList.add('hidden');
        btnProceed.disabled = true;
        return;
    }

    btnClear.classList.remove('hidden');
    btnProceed.disabled = false;
    queueList.innerHTML = ''; // Safely clear container

    queuedFiles.forEach((file, index) => {
        const ext = file.name.split('.').pop().toLowerCase();
        const formattedSize = (file.size / (1024 * 1024)).toFixed(2) + ' MB';

        const fileCard = document.createElement('div');
        fileCard.className = 'file-card';

        let iconHtml = `<div class="file-thumbnail">📄</div>`;
        if (['jpg', 'jpeg', 'png'].includes(ext)) {
            const previewUrl = URL.createObjectURL(file);
            iconHtml = `<img class="file-thumbnail" src="${previewUrl}" alt="Preview" />`;
        } else if (ext === 'pdf') {
            iconHtml = `<div class="file-thumbnail">📕</div>`;
        }

        fileCard.innerHTML = `
            ${iconHtml}
            <div class="file-info">
                <div class="file-name" title="${file.name}">${file.name}</div>
                <div class="file-meta">
                    <span class="format-badge ${ext}">${ext.toUpperCase()}</span>
                    <span class="file-size">${formattedSize}</span>
                </div>
            </div>
            <button type="button" class="btn-remove-file" onclick="removeQueueItem(${index})" title="Remove File">&times;</button>
        `;

        queueList.appendChild(fileCard);
    });
}

function removeQueueItem(index) {
    queuedFiles.splice(index, 1);
    renderQueueList();
}

function clearBatchQueue() {
    queuedFiles = [];
    renderQueueList();
}

function showUploadAlert(message, type) {
    const alertBox = document.getElementById('upload-alert');
    if (!alertBox) return;

    if (type === 'hidden' || !message) {
        alertBox.className = 'alert hidden';
        return;
    }
    alertBox.textContent = message;
    alertBox.className = `alert ${type}`;
}

// 5. Transition Action to Preprocessing
function proceedToPreprocessing() {
    if (queuedFiles.length === 0) return;
    uploadAndStartPreprocessing(queuedFiles);
}