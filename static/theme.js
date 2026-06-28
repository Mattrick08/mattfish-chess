// ========== MATTFISH SHARED THEME SYSTEM ==========
// Uses CSS custom properties for clean, non-destructive theming
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

    // Set CSS custom properties on the root element
    // This allows CSS to use var(--mattfish-bg) etc.
    const root = document.documentElement;
    root.style.setProperty('--mattfish-bg', theme.bgColor);
    root.style.setProperty('--mattfish-accent', theme.accentColor);
    root.style.setProperty('--mattfish-text', theme.textColor);
    root.style.setProperty('--mattfish-card-bg', lightenColor(theme.bgColor, 8));
    root.style.setProperty('--mattfish-input-bg', lightenColor(theme.bgColor, 5));

    // Apply background color to body ONLY
    document.body.style.backgroundColor = theme.bgColor;

    // Apply text color to body ONLY (inherited by children)
    document.body.style.color = theme.textColor;

    // Apply accent color to specific elements with accent-color class
    document.querySelectorAll('.accent-color').forEach(el => {
        el.style.color = theme.accentColor;
    });

    // Apply accent background ONLY to new-game-btn and similar primary buttons
    // NOT to period-btn, sort-btn, diff-btn, etc.
    document.querySelectorAll('.new-game-btn').forEach(el => {
        el.style.backgroundColor = theme.accentColor;
        el.onmouseenter = function() { 
            this.style.backgroundColor = darkenColor(theme.accentColor, 20); 
        };
        el.onmouseleave = function() { 
            this.style.backgroundColor = theme.accentColor; 
        };
    });

    // Apply accent to "Play vs MattFish" link on index page
    document.querySelectorAll('a.accent-bg').forEach(el => {
        el.style.backgroundColor = theme.accentColor;
        el.onmouseenter = function() { 
            this.style.backgroundColor = darkenColor(theme.accentColor, 20); 
        };
        el.onmouseleave = function() { 
            this.style.backgroundColor = theme.accentColor; 
        };
    });

    // Update card/panel backgrounds
    document.querySelectorAll('.stat-card, .chart-section, .pie-card, .openings-section, .personalize-panel, #status, .move-history').forEach(el => {
        el.style.backgroundColor = lightenColor(theme.bgColor, 8);
    });

    // Update input backgrounds
    document.querySelectorAll('input[type="text"]').forEach(el => {
        el.style.backgroundColor = lightenColor(theme.bgColor, 5);
        el.style.color = theme.textColor;
    });

    // Update eval center line
    document.querySelectorAll('.eval-center-line').forEach(el => {
        el.style.background = theme.accentColor;
    });

    // Update personalization panel title
    document.querySelectorAll('.personalize-panel h3').forEach(el => {
        el.style.color = theme.accentColor;
    });

    // Update stat card headings
    document.querySelectorAll('.stat-card h2, .chart-section h2, .openings-section h2, .pie-card h3').forEach(el => {
        el.style.color = theme.accentColor;
    });

    // Update table headers
    document.querySelectorAll('th').forEach(el => {
        el.style.color = theme.accentColor;
    });

    // Update active button borders
    document.querySelectorAll('.diff-btn.active, .color-btn.active').forEach(el => {
        el.style.borderColor = theme.accentColor;
    });

    // Apply background image
    const overlay = document.getElementById('bgImageOverlay');
    if (overlay) {
        if (theme.bgImage) {
            overlay.style.backgroundImage = 'url(' + theme.bgImage + ')';
        } else {
            overlay.style.backgroundImage = '';
        }
    }
}

function initThemePanel(containerId, options) {
    options = options || {};
    const container = document.getElementById(containerId);
    if (!container) return;

    const theme = getTheme();
    const showBg = options.showBg !== false;
    const showAccent = options.showAccent !== false;
    const showImage = options.showImage !== false;
    const showText = options.showText !== false;

    var html = '<div class="personalize-panel">';
    html += '<h3 class="accent-color">&#127912; Personalize</h3>';

    if (showBg) {
        html += '<div class="section-title">Background Color</div>';
        html += '<div class="color-grid" id="bgColorGrid"></div>';
        html += '<div class="custom-color-row">';
        html += '<label>Custom BG:</label>';
        html += '<input type="color" id="customBgColorPicker" value="' + theme.bgColor + '" onchange="applyCustomBgColor(this.value)">';
        html += '<input type="text" id="customBgColorHex" value="' + theme.bgColor + '" maxlength="7" onchange="applyCustomBgColor(this.value)">';
        html += '</div>';
    }

    if (showAccent) {
        html += '<div class="section-title">Accent Color</div>';
        html += '<div class="color-grid" id="accentColorGrid"></div>';
        html += '<div class="custom-color-row">';
        html += '<label>Custom:</label>';
        html += '<input type="color" id="customAccentColorPicker" value="' + theme.accentColor + '" onchange="applyCustomAccentColor(this.value)">';
        html += '<input type="text" id="customAccentColorHex" value="' + theme.accentColor + '" maxlength="7" onchange="applyCustomAccentColor(this.value)">';
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
        html += '<input type="color" id="customTextColorPicker" value="' + theme.textColor + '" onchange="applyCustomTextColor(this.value)">';
        html += '<input type="text" id="customTextColorHex" value="' + theme.textColor + '" maxlength="7" onchange="applyCustomTextColor(this.value)">';
        html += '</div>';
    }

    if (showImage) {
        html += '<div class="upload-area" id="uploadArea" onclick="document.getElementById('bgImageInput').click()">';
        html += '<p>&#128444; Click or drop image</p>';
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
        var bgGrid = document.getElementById('bgColorGrid');
        PRESET_BG_COLORS.forEach(function(color) {
            var swatch = document.createElement('div');
            swatch.className = 'color-swatch';
            swatch.style.backgroundColor = color;
            swatch.dataset.color = color;
            swatch.onclick = function() { applyBgColor(color); };
            if (color === theme.bgColor) swatch.classList.add('active');
            bgGrid.appendChild(swatch);
        });
    }

    if (showAccent) {
        var accentGrid = document.getElementById('accentColorGrid');
        PRESET_ACCENT_COLORS.forEach(function(color) {
            var swatch = document.createElement('div');
            swatch.className = 'color-swatch';
            swatch.style.backgroundColor = color;
            swatch.dataset.color = color;
            swatch.onclick = function() { applyAccentColor(color); };
            if (color === theme.accentColor) swatch.classList.add('active');
            accentGrid.appendChild(swatch);
        });
    }

    // Load saved image preview
    if (showImage && theme.bgImage) {
        var preview = document.getElementById('previewImg');
        if (preview) {
            preview.src = theme.bgImage;
            preview.classList.add('visible');
        }
        var removeBtn = document.getElementById('removeImgBtn');
        if (removeBtn) removeBtn.classList.add('visible');
        var uploadAreaP = document.querySelector('#uploadArea p');
        if (uploadAreaP) uploadAreaP.textContent = 'Image set!';
    }

    // Setup drag and drop
    if (showImage) {
        var uploadArea = document.getElementById('uploadArea');
        if (uploadArea) {
            uploadArea.addEventListener('dragover', function(e) {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });
            uploadArea.addEventListener('dragleave', function() {
                uploadArea.classList.remove('dragover');
            });
            uploadArea.addEventListener('drop', function(e) {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                var file = e.dataTransfer.files[0];
                if (file && file.type.startsWith('image/')) {
                    var reader = new FileReader();
                    reader.onload = function(evt) {
                        var dataUrl = evt.target.result;
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
    var picker = document.getElementById('customBgColorPicker');
    var hex = document.getElementById('customBgColorHex');
    if (picker) picker.value = color;
    if (hex) hex.value = color;
    document.querySelectorAll('#bgColorGrid .color-swatch').forEach(function(s) {
        s.classList.toggle('active', s.dataset.color === color);
    });
    applyThemeToPage();
}

function applyCustomBgColor(value) {
    var color = value;
    if (!color.startsWith('#')) color = '#' + color;
    if (/^#[0-9A-Fa-f]{6}$/.test(color)) {
        applyBgColor(color);
    }
}

function applyAccentColor(color) {
    saveTheme(THEME_KEYS.accentColor, color);
    var picker = document.getElementById('customAccentColorPicker');
    var hex = document.getElementById('customAccentColorHex');
    if (picker) picker.value = color;
    if (hex) hex.value = color;
    document.querySelectorAll('#accentColorGrid .color-swatch').forEach(function(s) {
        s.classList.toggle('active', s.dataset.color === color);
    });
    applyThemeToPage();
}

function applyCustomAccentColor(value) {
    var color = value;
    if (!color.startsWith('#')) color = '#' + color;
    if (/^#[0-9A-Fa-f]{6}$/.test(color)) {
        applyAccentColor(color);
    }
}

function applyTextColor(color) {
    saveTheme(THEME_KEYS.textColor, color);
    var picker = document.getElementById('customTextColorPicker');
    var hex = document.getElementById('customTextColorHex');
    if (picker) picker.value = color;
    if (hex) hex.value = color;
    applyThemeToPage();
}

function applyCustomTextColor(value) {
    var color = value;
    if (!color.startsWith('#')) color = '#' + color;
    if (/^#[0-9A-Fa-f]{6}$/.test(color)) {
        applyTextColor(color);
    }
}

function handleImageUpload(event) {
    var file = event.target.files[0];
    if (!file) return;

    var reader = new FileReader();
    reader.onload = function(e) {
        var dataUrl = e.target.result;
        applyBgImage(dataUrl);
        saveTheme(THEME_KEYS.bgImage, dataUrl);
        applyThemeToPage();
    };
    reader.readAsDataURL(file);
}

function applyBgImage(dataUrl) {
    var overlay = document.getElementById('bgImageOverlay');
    if (overlay) overlay.style.backgroundImage = 'url(' + dataUrl + ')';

    var preview = document.getElementById('previewImg');
    if (preview) {
        preview.src = dataUrl;
        preview.classList.add('visible');
    }

    var removeBtn = document.getElementById('removeImgBtn');
    if (removeBtn) removeBtn.classList.add('visible');

    var uploadAreaP = document.querySelector('#uploadArea p');
    if (uploadAreaP) uploadAreaP.textContent = 'Image set!';
}

function removeBgImage() {
    var overlay = document.getElementById('bgImageOverlay');
    if (overlay) overlay.style.backgroundImage = '';

    var preview = document.getElementById('previewImg');
    if (preview) {
        preview.src = '';
        preview.classList.remove('visible');
    }

    var removeBtn = document.getElementById('removeImgBtn');
    if (removeBtn) removeBtn.classList.remove('visible');

    var uploadAreaP = document.querySelector('#uploadArea p');
    if (uploadAreaP) uploadAreaP.textContent = '&#128444; Click or drop image';

    saveTheme(THEME_KEYS.bgImage, null);
    var fileInput = document.getElementById('bgImageInput');
    if (fileInput) fileInput.value = '';
}

function resetTheme() {
    saveTheme(THEME_KEYS.bgColor, null);
    saveTheme(THEME_KEYS.accentColor, null);
    saveTheme(THEME_KEYS.textColor, null);
    saveTheme(THEME_KEYS.bgImage, null);
    location.reload();
}
