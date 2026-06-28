// ========== MATTFISH SHARED THEME SYSTEM ==========
// This file handles background color, accent color, and background image
// Syncs between index.html and chess.html via localStorage

const THEME_KEYS = {
    bgColor: 'mattfish_bg_color',
    accentColor: 'mattfish_accent_color',
    bgImage: 'mattfish_bg_image',
    textColor: 'mattfish_text_color'
};

const DEFAULTS = {
    bgColor: '#1e1e1e',
    accentColor: '#e74c3c',
    textColor: '#ffffff'
};

const PRESET_BG_COLORS = [
    '#1e1e1e', '#0d0d0d', '#1a1a2e', '#16213e',
    '#0f3460', '#1a1a1a', '#2c2c2c', '#1e1e2e',
    '#0a0a0a', '#121212', '#1e1e1e', '#2d2d2d',
    '#1a1a1a', '#0f0f0f', '#1e1e1e', '#252525'
];

const PRESET_ACCENT_COLORS = [
    '#e74c3c', '#c0392b', '#e67e22', '#f39c12',
    '#f1c40f', '#2ecc71', '#27ae60', '#1abc9c',
    '#16a085', '#3498db', '#2980b9', '#9b59b6',
    '#8e44ad', '#e91e63', '#ff5722', '#00bcd4'
];

function getTheme() {
    return {
        bgColor: localStorage.getItem(THEME_KEYS.bgColor) || DEFAULTS.bgColor,
        accentColor: localStorage.getItem(THEME_KEYS.accentColor) || DEFAULTS.accentColor,
        bgImage: localStorage.getItem(THEME_KEYS.bgImage) || null,
        textColor: localStorage.getItem(THEME_KEYS.textColor) || DEFAULTS.textColor
    };
}

function saveTheme(key, value) {
    if (value === null || value === undefined) {
        localStorage.removeItem(key);
    } else {
        localStorage.setItem(key, value);
    }
}

function lightenColor(hex, percent) {
    const num = parseInt(hex.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = Math.min((num >> 16) + amt, 255);
    const G = Math.min((num >> 8 & 0x00FF) + amt, 255);
    const B = Math.min((num & 0x0000FF) + amt, 255);
    return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
}

function darkenColor(hex, percent) {
    const num = parseInt(hex.replace('#', ''), 16);
    const amt = Math.round(2.55 * percent);
    const R = Math.max((num >> 16) - amt, 0);
    const G = Math.max((num >> 8 & 0x00FF) - amt, 0);
    const B = Math.max((num & 0x0000FF) - amt, 0);
    return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
}

function applyThemeToPage() {
    const theme = getTheme();

    // Apply background color to body
    document.body.style.backgroundColor = theme.bgColor;

    // Apply text color
    document.body.style.color = theme.textColor;

    // Apply accent color to all accent elements
    document.querySelectorAll('.accent-color').forEach(el => {
        el.style.color = theme.accentColor;
    });
    document.querySelectorAll('.accent-bg').forEach(el => {
        el.style.backgroundColor = theme.accentColor;
    });
    document.querySelectorAll('.accent-border').forEach(el => {
        el.style.borderColor = theme.accentColor;
    });

    // Apply accent to specific common elements
    document.querySelectorAll('h1').forEach(el => {
        if (!el.classList.contains('no-accent')) el.style.color = theme.accentColor;
    });

    // Update card backgrounds to be slightly lighter than body
    const cardBg = lightenColor(theme.bgColor, 8);
    document.querySelectorAll('.stat-card, .chart-section, .pie-card, .openings-section, .personalize-panel, #status, .move-history').forEach(el => {
        el.style.backgroundColor = cardBg;
    });

    // Update input backgrounds
    document.querySelectorAll('input[type="text"]').forEach(el => {
        el.style.backgroundColor = lightenColor(theme.bgColor, 5);
        el.style.color = theme.textColor;
    });

    // Update new game button
    const newGameBtn = document.querySelector('.new-game-btn');
    if (newGameBtn) {
        newGameBtn.style.backgroundColor = theme.accentColor;
    }

    // Update eval center line
    const evalLine = document.querySelector('.eval-center-line');
    if (evalLine) evalLine.style.background = theme.accentColor;

    // Update personalization panel title
    const panelTitle = document.querySelector('.personalize-panel h3');
    if (panelTitle) panelTitle.style.color = theme.accentColor;

    // Apply background image
    const overlay = document.getElementById('bgImageOverlay');
    if (overlay && theme.bgImage) {
        overlay.style.backgroundImage = `url(${theme.bgImage})`;
    }
}

function initThemePanel(containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const theme = getTheme();
    const showBg = options.showBg !== false;
    const showAccent = options.showAccent !== false;
    const showImage = options.showImage !== false;
    const showText = options.showText !== false;

    let html = '<div class="personalize-panel">';
    html += '<h3 class="accent-color">🎨 Personalize</h3>';

    if (showBg) {
        html += '<div class="section-title">Background Color</div>';
        html += '<div class="color-grid" id="bgColorGrid"></div>';
        html += '<div class="custom-color-row">';
        html += '<label>Custom BG:</label>';
        html += `<input type="color" id="customBgColorPicker" value="${theme.bgColor}" onchange="applyCustomBgColor(this.value)">`;
        html += `<input type="text" id="customBgColorHex" value="${theme.bgColor}" maxlength="7" onchange="applyCustomBgColor(this.value)">`;
        html += '</div>';
    }

    if (showAccent) {
        html += '<div class="section-title">Accent Color</div>';
        html += '<div class="color-grid" id="accentColorGrid"></div>';
        html += '<div class="custom-color-row">';
        html += '<label>Custom:</label>';
        html += `<input type="color" id="customAccentColorPicker" value="${theme.accentColor}" onchange="applyCustomAccentColor(this.value)">`;
        html += `<input type="text" id="customAccentColorHex" value="${theme.accentColor}" maxlength="7" onchange="applyCustomAccentColor(this.value)">`;
        html += '</div>';
    }

    if (showText) {
        html += '<div class="section-title">Text Color</div>';
        html += '<div class="text-color-options">';
        html += '<button class="text-color-btn" onclick="applyTextColor('#ffffff')" style="background:#fff;color:#000">White</button>';
        html += '<button class="text-color-btn" onclick="applyTextColor('#cccccc')" style="background:#ccc;color:#000">Light Gray</button>';
        html += '<button class="text-color-btn" onclick="applyTextColor('#888888')" style="background:#888;color:#fff">Gray</button>';
        html += '<button class="text-color-btn" onclick="applyTextColor('#ffeb3b')" style="background:#ffeb3b;color:#000">Yellow</button>';
        html += '<button class="text-color-btn" onclick="applyTextColor('#00bcd4')" style="background:#00bcd4;color:#fff">Cyan</button>';
        html += '<button class="text-color-btn" onclick="applyTextColor('#e91e63')" style="background:#e91e63;color:#fff">Pink</button>';
        html += '</div>';
        html += '<div class="custom-color-row">';
        html += '<label>Custom Text:</label>';
        html += `<input type="color" id="customTextColorPicker" value="${theme.textColor}" onchange="applyCustomTextColor(this.value)">`;
        html += `<input type="text" id="customTextColorHex" value="${theme.textColor}" maxlength="7" onchange="applyCustomTextColor(this.value)">`;
        html += '</div>';
    }

    if (showImage) {
        html += '<div class="upload-area" id="uploadArea" onclick="document.getElementById('bgImageInput').click()">';
        html += '<p>🖼️ Click or drop image</p>';
        html += '<button class="upload-btn" type="button">Choose Image</button>';
        html += '<img class="preview-img" id="previewImg" alt="Preview">';
        html += '<button class="remove-img-btn" id="removeImgBtn" onclick="event.stopPropagation(); removeBgImage()">Remove Image</button>';
        html += '</div>';
        html += '<input type="file" id="bgImageInput" accept="image/*" onchange="handleImageUpload(event)">';
    }

    html += '<button class="reset-btn" onclick="resetTheme()">Reset to Default</button>';
    html += '</div>';

    container.innerHTML = html;

    // Populate color grids
    if (showBg) {
        const bgGrid = document.getElementById('bgColorGrid');
        PRESET_BG_COLORS.forEach(color => {
            const swatch = document.createElement('div');
            swatch.className = 'color-swatch';
            swatch.style.backgroundColor = color;
            swatch.dataset.color = color;
            swatch.onclick = () => applyBgColor(color);
            if (color === theme.bgColor) swatch.classList.add('active');
            bgGrid.appendChild(swatch);
        });
    }

    if (showAccent) {
        const accentGrid = document.getElementById('accentColorGrid');
        PRESET_ACCENT_COLORS.forEach(color => {
            const swatch = document.createElement('div');
            swatch.className = 'color-swatch';
            swatch.style.backgroundColor = color;
            swatch.dataset.color = color;
            swatch.onclick = () => applyAccentColor(color);
            if (color === theme.accentColor) swatch.classList.add('active');
            accentGrid.appendChild(swatch);
        });
    }

    // Load saved image preview
    if (showImage && theme.bgImage) {
        const preview = document.getElementById('previewImg');
        if (preview) {
            preview.src = theme.bgImage;
            preview.classList.add('visible');
        }
        const removeBtn = document.getElementById('removeImgBtn');
        if (removeBtn) removeBtn.classList.add('visible');
        const uploadAreaP = document.querySelector('#uploadArea p');
        if (uploadAreaP) uploadAreaP.textContent = 'Image set!';
    }

    // Setup drag and drop
    if (showImage) {
        const uploadArea = document.getElementById('uploadArea');
        if (uploadArea) {
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });
            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('dragover');
            });
            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                const file = e.dataTransfer.files[0];
                if (file && file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = function(evt) {
                        const dataUrl = evt.target.result;
                        applyBgImage(dataUrl);
                        saveTheme(THEME_KEYS.bgImage, dataUrl);
                        applyThemeToPage();
                    };
                    reader.readAsDataURL(file);
                }
            });
        }
    }

    applyThemeToPage();
}

function applyBgColor(color) {
    saveTheme(THEME_KEYS.bgColor, color);
    const picker = document.getElementById('customBgColorPicker');
    const hex = document.getElementById('customBgColorHex');
    if (picker) picker.value = color;
    if (hex) hex.value = color;
    document.querySelectorAll('#bgColorGrid .color-swatch').forEach(s => {
        s.classList.toggle('active', s.dataset.color === color);
    });
    applyThemeToPage();
}

function applyCustomBgColor(value) {
    let color = value;
    if (!color.startsWith('#')) color = '#' + color;
    if (/^#[0-9A-Fa-f]{6}$/.test(color)) {
        applyBgColor(color);
    }
}

function applyAccentColor(color) {
    saveTheme(THEME_KEYS.accentColor, color);
    const picker = document.getElementById('customAccentColorPicker');
    const hex = document.getElementById('customAccentColorHex');
    if (picker) picker.value = color;
    if (hex) hex.value = color;
    document.querySelectorAll('#accentColorGrid .color-swatch').forEach(s => {
        s.classList.toggle('active', s.dataset.color === color);
    });
    applyThemeToPage();
}

function applyCustomAccentColor(value) {
    let color = value;
    if (!color.startsWith('#')) color = '#' + color;
    if (/^#[0-9A-Fa-f]{6}$/.test(color)) {
        applyAccentColor(color);
    }
}

function applyTextColor(color) {
    saveTheme(THEME_KEYS.textColor, color);
    const picker = document.getElementById('customTextColorPicker');
    const hex = document.getElementById('customTextColorHex');
    if (picker) picker.value = color;
    if (hex) hex.value = color;
    applyThemeToPage();
}

function applyCustomTextColor(value) {
    let color = value;
    if (!color.startsWith('#')) color = '#' + color;
    if (/^#[0-9A-Fa-f]{6}$/.test(color)) {
        applyTextColor(color);
    }
}

function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        const dataUrl = e.target.result;
        applyBgImage(dataUrl);
        saveTheme(THEME_KEYS.bgImage, dataUrl);
        applyThemeToPage();
    };
    reader.readAsDataURL(file);
}

function applyBgImage(dataUrl) {
    const overlay = document.getElementById('bgImageOverlay');
    if (overlay) overlay.style.backgroundImage = `url(${dataUrl})`;

    const preview = document.getElementById('previewImg');
    if (preview) {
        preview.src = dataUrl;
        preview.classList.add('visible');
    }

    const removeBtn = document.getElementById('removeImgBtn');
    if (removeBtn) removeBtn.classList.add('visible');

    const uploadAreaP = document.querySelector('#uploadArea p');
    if (uploadAreaP) uploadAreaP.textContent = 'Image set!';
}

function removeBgImage() {
    const overlay = document.getElementById('bgImageOverlay');
    if (overlay) overlay.style.backgroundImage = '';

    const preview = document.getElementById('previewImg');
    if (preview) {
        preview.src = '';
        preview.classList.remove('visible');
    }

    const removeBtn = document.getElementById('removeImgBtn');
    if (removeBtn) removeBtn.classList.remove('visible');

    const uploadAreaP = document.querySelector('#uploadArea p');
    if (uploadAreaP) uploadAreaP.textContent = '🖼️ Click or drop image';

    saveTheme(THEME_KEYS.bgImage, null);
    const fileInput = document.getElementById('bgImageInput');
    if (fileInput) fileInput.value = '';
}

function resetTheme() {
    saveTheme(THEME_KEYS.bgColor, null);
    saveTheme(THEME_KEYS.accentColor, null);
    saveTheme(THEME_KEYS.textColor, null);
    saveTheme(THEME_KEYS.bgImage, null);
    location.reload();
}
