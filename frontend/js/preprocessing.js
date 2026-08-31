// Available profiles matching backend pipeline options
const AVAILABLE_PROFILES = [
    { key: "original", label: "Original (No Preprocessing)" },
    { key: "basic", label: "Basic (Denoise & Grayscale)" },
    { key: "low_light", label: "Low Light (CLAHE & Adaptive)" },
    { key: "overexposed", label: "Overexposed (Gamma Fix)" },
    { key: "skewed", label: "Skewed (Deskew & Rotate)" },
    { key: "noisy_scan", label: "Noisy Scan (Median Filter)" },
    { key: "small_text", label: "Small Text (Upscale 2x & Sharpen)" }
];

let activeBatchPages = [];

function getAuthHeaders(isJson = false) {
    const token = localStorage.getItem("access_token") || localStorage.getItem("token");
    const headers = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (isJson) headers["Content-Type"] = "application/json";
    return headers;
}

// 1. Ingestion persistence & automatic initial batch assessment
async function uploadAndStartPreprocessing(files) {
    activeBatchPages = [];
    showUploadAlert("", "hidden");

    const btnProceed = document.getElementById("btnProceedPreprocessing");
    if (btnProceed) {
        btnProceed.disabled = true;
        btnProceed.innerHTML = `<span>Uploading & Processing...</span>`;
    }

    const isGuest = localStorage.getItem("isGuest") === "true";
    const storedUserRaw = localStorage.getItem("user");
    let userId = null;

    if (!isGuest && storedUserRaw) {
        try {
            const parsedUser = JSON.parse(storedUserRaw);
            userId = parsedUser.id || parsedUser.user_id;
        } catch (e) {
            console.error("Failed to parse user data:", e);
        }
    }

    try {
        for (const file of files) {
            const formData = new FormData();
            formData.append("file", file);

            let uploadUrl = `${CONFIG.API_BASE_URL}/documents/upload`;
            if (userId) uploadUrl += `?user_id=${encodeURIComponent(userId)}`;

            // Step A: Save document
            const uploadRes = await fetch(uploadUrl, {
                method: "POST",
                headers: getAuthHeaders(false),
                body: formData
            });

            if (!uploadRes.ok) {
                const err = await uploadRes.json();
                throw new Error(err.detail || `Upload failed for ${file.name}`);
            }

            const docData = await uploadRes.json();
            const docId = docData.document_id || docData.id;

            // Step B: Run automated batch quality assessment & initial preprocessing
            const prepRes = await fetch(`${CONFIG.API_BASE_URL}/preprocessing/documents/${docId}`, {
                method: "POST",
                headers: getAuthHeaders(true)
            });

            if (!prepRes.ok) {
                const err = await prepRes.json();
                throw new Error(err.detail || "Quality analysis failed.");
            }

            const prepData = await prepRes.json();
            const pagesMetadata = docData.pages_metadata || docData.pages || [];
            const processedPagesList = prepData.processed_pages || prepData.pages || [];

            pagesMetadata.forEach((pageMeta, pageIdx) => {
                const targetPageNum = pageMeta.page_number ?? pageMeta.page;
                const targetPageId = pageMeta.page_id ?? pageMeta.id;

                // Robust lookup: match by page_id/id, then page_number, then fallback to array index position
                const matchedReport = processedPagesList.find((p) => {
                    const pId = p.page_id ?? p.id;
                    const pNum = p.page_number ?? p.page;
                    if (targetPageId && pId && String(pId) === String(targetPageId)) return true;
                    if (targetPageNum !== undefined && pNum !== undefined && String(pNum) === String(targetPageNum)) return true;
                    return false;
                }) || processedPagesList[pageIdx] || {};

                // Extract nested quality object if wrapped by backend
                const qualityData = matchedReport.quality_metrics || matchedReport.quality || matchedReport;

                const recProfile = qualityData.recommended_profile || "basic";
                const appProfile = qualityData.applied_profile || recProfile;

                activeBatchPages.push({
                    document_id: docId,
                    filename: docData.filename || file.name,
                    page_number: targetPageNum,
                    page_id: targetPageId,
                    quality: qualityData,
                    isCustom: Boolean(appProfile && recProfile && appProfile !== recProfile),
                    updatedAt: Date.now()
                });
            });
        }

        renderPreprocessingView();
        switchMainTab("preprocessing");

    } catch (err) {
        console.error("Preprocessing upload error:", err);
        showUploadAlert(err.message, "error");
    } finally {
        if (btnProceed) {
            btnProceed.disabled = false;
            btnProceed.innerHTML = `
                <span>Proceed to Preprocessing</span>
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                    <polyline points="12 5 19 12 12 19"></polyline>
                </svg>`;
        }
    }
}

// 2. Render Toolbar and Vertical Side-by-Side Comparison Layout
function renderPreprocessingView() {
    const container = document.getElementById("preprocessingPagesContainer");
    const totalCounter = document.getElementById("prepTotalPages");

    if (totalCounter) totalCounter.textContent = activeBatchPages.length;
    if (!container) return;

    // Header Control Toolbar
    const toolbarHtml = `
        <div class="prep-toolbar">
            <div class="prep-toolbar-left">
                <label for="batchPresetSelect">Apply Pipeline Profile to All Pages:</label>
                <select id="batchPresetSelect" onchange="applyBatchPreset(this.value)">
                    <option value="" disabled selected>Select preset for batch...</option>
                    ${AVAILABLE_PROFILES.map(p => `<option value="${p.key}">${p.label}</option>`).join("")}
                </select>
            </div>
            <button class="btn-primary-action" onclick="proceedToOCR()">
                <span>Proceed to OCR Engine</span>
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                    <polyline points="12 5 19 12 12 19"></polyline>
                </svg>
            </button>
        </div>
    `;

    container.innerHTML = toolbarHtml;

    const cardsWrapper = document.createElement("div");
    cardsWrapper.className = "prep-cards-grid";

    activeBatchPages.forEach((item, index) => {
        const q = item.quality || {};
        const pageCard = document.createElement("div");
        pageCard.className = "prep-card";

        const rawImageUrl = `${CONFIG.API_BASE_URL}/documents/${item.document_id}/pages/${item.page_number}/image`;
        const processedImageUrl = `${CONFIG.API_BASE_URL}/preprocessing/documents/${item.document_id}/pages/${item.page_number}/processed-image?t=${item.updatedAt || Date.now()}`;
        const qualityClass = (q.quality_label || "unknown").toLowerCase().replace(/\s+/g, "-");

        const customBadgeHtml = item.isCustom 
            ? `<span class="badge-custom">Custom Pipeline</span>`
            : "";

        // Selection priority: applied profile -> recommended profile -> original
        const activeProfileKey = q.applied_profile || q.recommended_profile || "original";

        const dropdownOptionsHtml = AVAILABLE_PROFILES.map(prof => {
            const isSelected = activeProfileKey === prof.key;
            return `<option value="${prof.key}" ${isSelected ? "selected" : ""}>${prof.label}</option>`;
        }).join("");

        const recKey = q.recommended_profile || "basic";
        const recommendedLabel = AVAILABLE_PROFILES.find(p => p.key === recKey)?.label || recKey;

        pageCard.innerHTML = `
            <div class="prep-card-header">
                <div class="prep-card-title-group">
                    <span class="prep-card-title">${item.filename}</span>
                    <span class="prep-page-badge">Page ${item.page_number}</span>
                    ${customBadgeHtml}
                </div>
                <span class="quality-badge ${qualityClass}">${q.quality_label || "Pending"}</span>
            </div>

            <div class="prep-card-body">
                <div class="prep-thumbnails-wrapper">
                    <div class="prep-thumb-box" onclick="openImageLightbox('${rawImageUrl}', 'Original Image — ${item.filename} (Page ${item.page_number})')">
                        <span class="thumb-label">Original Image</span>
                        <div class="thumb-img-container portrait-box">
                            <img src="${rawImageUrl}" alt="Raw Page ${item.page_number}" loading="lazy" />
                            <div class="thumb-hover-overlay">
                                <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="15 3 21 3 21 9"></polyline>
                                    <polyline points="9 21 3 21 3 15"></polyline>
                                    <line x1="21" y1="3" x2="14" y2="10"></line>
                                    <line x1="3" y1="21" x2="10" y2="14"></line>
                                </svg>
                                <span>Click for Fullscreen Overlay</span>
                            </div>
                        </div>
                    </div>

                    <div class="prep-thumb-box" onclick="openImageLightbox('${processedImageUrl}', 'Enhanced Output — ${item.filename} (Page ${item.page_number})')">
                        <span class="thumb-label output-label">Enhanced Output</span>
                        <div class="thumb-img-container portrait-box">
                            <img src="${processedImageUrl}" alt="Processed Page ${item.page_number}" loading="lazy" />
                            <div class="thumb-hover-overlay">
                                <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="15 3 21 3 21 9"></polyline>
                                    <polyline points="9 21 3 21 3 15"></polyline>
                                    <line x1="21" y1="3" x2="14" y2="10"></line>
                                    <line x1="3" y1="21" x2="10" y2="14"></line>
                                </svg>
                                <span>Click for Fullscreen Overlay</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="prep-metrics-panel">
                    <h4 class="metrics-panel-title">Quality Assessment</h4>
                    <div class="metric-list">
                        <div class="metric-item"><span>Blur Score</span> <strong>${q.blur_score ?? q.blur ?? "N/A"}</strong></div>
                        <div class="metric-item"><span>Brightness</span> <strong>${q.brightness_score ?? q.brightness ?? "N/A"}</strong></div>
                        <div class="metric-item"><span>Contrast</span> <strong>${q.contrast_score ?? q.contrast ?? "N/A"}</strong></div>
                        <div class="metric-item"><span>Skew Angle</span> <strong>${q.skew_angle ?? 0}°</strong></div>
                        <div class="metric-item"><span>Est. DPI</span> <strong>${q.estimated_dpi ?? q.dpi ?? "N/A"}</strong></div>
                        <div class="metric-item"><span>Boundary</span> <strong>${q.has_document_boundary !== undefined ? (q.has_document_boundary ? "Detected" : "None") : "N/A"}</strong></div>
                    </div>
                    ${q.resolution_warning ? `<div class="prep-warning-bar">⚠️ Low Resolution Detected</div>` : ""}
                </div>
            </div>

            <div class="prep-card-footer">
                <div class="prep-select-group">
                    <label>Selected Profile Override:</label>
                    <select onchange="updatePageProfile('${item.document_id}', ${item.page_number}, this.value, ${index})">
                        ${dropdownOptionsHtml}
                    </select>
                </div>
                <div class="prep-recommendation">
                    Auto-Suggested: <strong>${recommendedLabel}</strong>
                </div>
            </div>
        `;

        cardsWrapper.appendChild(pageCard);
    });

    container.appendChild(cardsWrapper);
}

// 3. Update single page custom pipeline override
async function updatePageProfile(documentId, pageNumber, newProfile, index) {
    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}/preprocessing/documents/${documentId}/pages/${pageNumber}`, {
            method: "POST",
            headers: getAuthHeaders(true),
            body: JSON.stringify({ override_profile: newProfile })
        });

        if (!response.ok) throw new Error("Failed to set custom manual profile override.");

        const responseData = await response.json();
        const updatedQuality = responseData.quality_metrics || responseData.quality || responseData;

        // Update active batch item state
        activeBatchPages[index].quality = updatedQuality;
        activeBatchPages[index].isCustom = Boolean(
            updatedQuality.applied_profile && 
            updatedQuality.recommended_profile && 
            updatedQuality.applied_profile !== updatedQuality.recommended_profile
        );
        activeBatchPages[index].updatedAt = Date.now(); // Cache busting timestamp trigger

        // Re-render UI to update images, tags, and metrics
        renderPreprocessingView();

    } catch (err) {
        alert(err.message);
    }
}

// 4. Batch preset selector handler (applies single profile to all items sequentially)
async function applyBatchPreset(selectedProfile) {
    if (!selectedProfile || activeBatchPages.length === 0) return;

    for (let i = 0; i < activeBatchPages.length; i++) {
        const item = activeBatchPages[i];
        await updatePageProfile(item.document_id, item.page_number, selectedProfile, i);
    }
}

// 5. Image Lightbox Viewer Modal
function openImageLightbox(imgUrl, captionText) {
    const modal = document.getElementById("imageLightboxModal");
    const img = document.getElementById("lightboxImage");
    const caption = document.getElementById("lightboxCaption");

    if (!modal || !img) return;
    img.src = imgUrl;
    if (caption) caption.textContent = captionText;
    modal.classList.remove("hidden");
}

function closeImageLightbox(e, force = false) {
    const modal = document.getElementById("imageLightboxModal");
    if (!modal) return;
    if (force || e.target.id === "imageLightboxModal" || e.target.classList.contains("lightbox-close")) {
        modal.classList.add("hidden");
    }
}

// 6. Manual trigger step to handoff active batch to OCR pipeline
function proceedToOCR() {
    if (activeBatchPages.length === 0) {
        alert("No preprocessed document pages available for OCR.");
        return;
    }
    
    window.dispatchEvent(new CustomEvent("pipeline:start-ocr", {
        detail: { pages: activeBatchPages }
    }));
}