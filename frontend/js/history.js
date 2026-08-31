let selectedHistoryPages = new Map(); // Key: `${docId}_${pageNum}`, Value: page Object

// Switch active sidebar tabs
function switchMainTab(tabName) {
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

    const targetTab = document.getElementById(`tab-${tabName}`);
    const targetNav = document.getElementById(`nav-${tabName}`);

    if (targetTab) targetTab.classList.remove('hidden');
    if (targetNav) targetNav.classList.add('active');

    if (tabName === 'history') {
        loadDocumentHistory();
    }
}

// Fetch and render document history with granular thumbnail page selection
async function loadDocumentHistory() {
    const container = document.getElementById("historyContainer");
    if (!container) return;

    container.innerHTML = `<div class="history-loading">Loading document history from disk...</div>`;

    const isGuest = localStorage.getItem("isGuest") === "true";
    const storedUserRaw = localStorage.getItem("user");
    let userId = null;

    if (!isGuest && storedUserRaw) {
        try {
            const parsed = JSON.parse(storedUserRaw);
            userId = parsed.id || parsed.user_id;
        } catch (e) {
            console.error("Invalid user JSON", e);
        }
    }

    try {
        let fetchUrl = `${CONFIG.API_BASE_URL}/documents/history`;
        if (userId) fetchUrl += `?user_id=${encodeURIComponent(userId)}`;

        const response = await fetch(fetchUrl, {
            headers: getAuthHeaders(true)
        });

        if (!response.ok) throw new Error("Failed to load history.");

        const documents = await response.json();

        if (!documents || documents.length === 0) {
            container.innerHTML = `<div class="history-empty">No stored documents found. Upload files to get started.</div>`;
            return;
        }

        renderHistoryGrid(documents);
    } catch (err) {
        container.innerHTML = `<div class="history-error">${err.message}</div>`;
    }
}

function renderHistoryGrid(documents) {
    const container = document.getElementById("historyContainer");
    container.innerHTML = "";

    documents.forEach((doc) => {
        const docGroup = document.createElement("div");
        docGroup.className = "history-doc-group";

        const formattedDate = new Date(doc.created_at).toLocaleString();

        let pageCardsHtml = "";
        doc.pages.forEach((page) => {
            const selectKey = `${doc.document_id}_${page.page_number}`;
            const isChecked = selectedHistoryPages.has(selectKey) ? "checked" : "";
            const rawImageUrl = `${CONFIG.API_BASE_URL}/documents/${doc.document_id}/pages/${page.page_number}/image`;
            const statusBadgeClass = page.is_preprocessed ? "badge-processed" : "badge-raw";

            pageCardsHtml += `
                <div class="history-page-card ${isChecked ? 'selected' : ''}" id="card_${selectKey}">
                    <div class="card-checkbox-overlay">
                        <input type="checkbox" 
                               id="chk_${selectKey}" 
                               ${isChecked} 
                               onchange="togglePageSelection('${doc.document_id}', '${doc.filename}', ${page.page_number}, '${page.page_id}', ${JSON.stringify(page.quality_metrics).replace(/"/g, '&quot;')}, this.checked)" />
                    </div>
                    
                    <div class="history-thumb-container" onclick="openImageLightbox('${rawImageUrl}', '${doc.filename} — Page ${page.page_number}')">
                        <img src="${rawImageUrl}" alt="Page ${page.page_number}" loading="lazy" />
                        <span class="page-number-tag">Page ${page.page_number}</span>
                    </div>

                    <div class="history-card-details">
                        <span class="status-pill ${statusBadgeClass}">
                            ${page.is_preprocessed ? (page.applied_profile || 'Preprocessed') : 'Raw / Uploaded'}
                        </span>
                        <div class="quality-mini-metric">
                            Blur: <strong>${page.quality_metrics?.blur_score?.toFixed(1) || 'N/A'}</strong>
                        </div>
                    </div>
                </div>
            `;
        });

        docGroup.innerHTML = `
            <div class="history-doc-header">
                <div class="doc-header-info">
                    <h3>${doc.filename}</h3>
                    <span class="doc-meta-sub">${doc.page_count} Page(s) • Uploaded ${formattedDate}</span>
                </div>
                <div class="doc-header-actions">
                    <button class="btn-secondary-sm" onclick="toggleSelectAllDocPages('${doc.document_id}', true)">Select All Pages</button>
                    <button class="btn-danger-sm" onclick="deleteHistoryDoc('${doc.document_id}')">Delete</button>
                </div>
            </div>
            <div class="history-pages-grid">
                ${pageCardsHtml}
            </div>
        `;

        container.appendChild(docGroup);
    });

    updateSelectionSummary();
}

function togglePageSelection(docId, filename, pageNumber, pageId, qualityMetrics, isChecked) {
    const selectKey = `${docId}_${pageNumber}`;
    const cardEl = document.getElementById(`card_${selectKey}`);

    if (isChecked) {
        selectedHistoryPages.set(selectKey, {
            document_id: docId,
            filename: filename,
            page_number: pageNumber,
            page_id: pageId,
            quality: qualityMetrics || {},
            isCustom: Boolean(qualityMetrics?.applied_profile && qualityMetrics?.applied_profile !== qualityMetrics?.recommended_profile),
            updatedAt: Date.now()
        });
        if (cardEl) cardEl.classList.add("selected");
    } else {
        selectedHistoryPages.delete(selectKey);
        if (cardEl) cardEl.classList.remove("selected");
    }

    updateSelectionSummary();
}

function updateSelectionSummary() {
    const countSpan = document.getElementById("historySelectionCount");
    const proceedBtn = document.getElementById("btnProceedSelectedPrep");

    const size = selectedHistoryPages.size;
    if (countSpan) countSpan.textContent = `${size} page(s) selected`;
    if (proceedBtn) proceedBtn.disabled = size === 0;
}

// Hand off selected history pages directly to active Batch Preprocessing view
async function sendSelectedToPreprocessing() {
    if (selectedHistoryPages.size === 0) return;

    activeBatchPages = Array.from(selectedHistoryPages.values());

    // Switch view to Preprocessing tab and render selected items
    switchMainTab("preprocessing");
    renderPreprocessingView();
}

// Delete document cascade trigger
async function deleteHistoryDoc(docId) {
    if (!confirm("Are you sure you want to delete this document and its pages permanently?")) return;

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/documents/${docId}`, {
            method: "DELETE",
            headers: getAuthHeaders(true)
        });

        if (!response.ok) throw new Error("Failed to delete document.");

        // Clear references from selection map
        for (const [key, value] of selectedHistoryPages.entries()) {
            if (value.document_id === docId) selectedHistoryPages.delete(key);
        }

        loadDocumentHistory();
    } catch (err) {
        alert(err.message);
    }
}