// ========== MATTFISH THEME SYSTEM ==========
// Toggle panel, background color, accent color, image upload
// Syncs across pages via localStorage

var THEME_KEYS = {
    bgColor: 'mattfish_bg_color',
    accentColor: 'mattfish_accent_color',
    bgImage: 'mattfish_bg_image'
};

var DEFAULTS = {
    bgColor: '#1e1e1e',
    accentColor: '#e74c3c'
};

var PRESET_BG_COLORS = [
    '#1e1e1e', '#0d0d0d', '#1a1a2e', '#16213e',
    '#0f3460', '#1a1a1a', '#2c2c2c', '#1e1e2e',
    '#0a0a0a', '#121212', '#1e1e1e', '#2d2d2d',
    '#1a1a1a', '#0f0f0f', '#1e1e1e', '#252525'
];

var PRESET_ACCENT_COLORS = [
    '#e74c3c', '#c0392b', '#e67e22', '#f39c12',
    '#f1c40f', '#2ecc71', '#27ae60', '#1abc9c',
    '#16a085', '#3498db', '#2980b9', '#9b59b6',
    '#8e44ad', '#e91e63', '#ff5722', '#00bcd4'
];

function getTheme() {
    var bg = localStorage.getItem(THEME_KEYS.bgColor) || DEFAULTS.bgColor;
    var accent = localStorage.getItem(THEME_KEYS.accentColor) || DEFAULTS.accentColor;
    var img = localStorage.getItem(THEME_KEYS.bgImage) || null;
    return { bgColor: bg, accentColor: accent, bgImage: img };
}

function saveTheme(key, value) {
    if (value === null || value === undefined) {
        localStorage.removeItem(key);
    } else {
        localStorage.setItem(key, value);
    }
}

function lightenColor(hex, percent) {
    var num = parseInt(hex.replace('#', ''), 16);
    var amt = Math.round(2.55 * percent);
    var R = Math.min((num >> 16) + amt, 255);
    var G = Math.min((num >> 8 & 0x00FF) + amt, 255);
    var B = Math.min((num & 0x0000FF) + amt, 255);
    return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
}

function darkenColor(hex, percent) {
    var num = parseInt(hex.replace('#', ''), 16);
    var amt = Math.round(2.55 * percent);
    var R = Math.max((num >> 16) - amt, 0);
    var G = Math.max((num >> 8 & 0x00FF) - amt, 0);
    var B = Math.max((num & 0x0000FF) - amt, 0);
    return '#' + (0x1000000 + R * 0x10000 + G * 0x100 + B).toString(16).slice(1);
}

function applyThemeToPage() {
    var theme = getTheme();

    document.body.style.backgroundColor = theme.bgColor;

    var h1 = document.querySelector('h1');
    if (h1) h1.style.color = theme.accentColor;

    var ngb = document.querySelector('.new-game-btn');
    if (ngb) {
        ngb.style.backgroundColor = theme.accentColor;
    }

    var playLink = document.querySelector('a[href="/play"]');
    if (playLink) {
        playLink.style.backgroundColor = theme.accentColor;
    }

    var evalLine = document.querySelector('.eval-center-line');
    if (evalLine) evalLine.style.background = theme.accentColor;

    var panelTitle = document.querySelector('.personalize-panel h3');
    if (panelTitle) panelTitle.style.color = theme.accentColor;

    document.querySelectorAll('.stat-card h2, .chart-section h2, .openings-section h2, .pie-card h3').forEach(function(el) {
        el.style.color = theme.accentColor;
    });

    document.querySelectorAll('th').forEach(function(el) {
        el.style.color = theme.accentColor;
    });

    document.querySelectorAll('.diff-btn.active, .color-btn.active').forEach(function(el) {
        el.style.borderColor = theme.accentColor;
    });

    var cardBg = lightenColor(theme.bgColor, 8);
    document.querySelectorAll('.stat-card, .chart-section, .pie-card, .openings-section, .personalize-panel, #status, .move-history').forEach(function(el) {
        el.style.backgroundColor = cardBg;
    });

    var overlay = document.getElementById('bgImageOverlay');
    if (overlay) {
        if (theme.bgImage) {
            overlay.style.backgroundImage = 'url(' + theme.bgImage + ')';
        } else {
            overlay.style.backgroundImage = '';
        }
    }
}

function togglePersonalizePanel() {
    var panel = document.getElementById('personalizePanel');
    var btn = document.getElementById('personalizeToggleBtn');
    if (!panel) return;

    if (panel.style.display === 'none' || panel.style.display === '') {
        panel.style.display = 'block';
        if (btn) btn.textContent = '✕ Close';
    } else {
        panel.style.display = 'none';
        if (btn) btn.textContent = '🎨 Personalize';
    }
}

function initThemePanel(containerId, options) {
    options = options || {};
    var container = document.getElementById(containerId);
    if (!container) return;

    var theme = getTheme();
    var showBg = options.showBg !== false;
    var showAccent = options.showAccent !== false;
    var showImage = options.showImage !== false;

    var html = '<div id="personalizePanel" style="display:none;">';
    html += '<div class="personalize-panel">';
    html += '<h3 style="color:' + theme.accentColor + '">&#127912; Personalize</h3>';

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

    if (showImage) {
        html += '<div class="upload-area" id="uploadArea" onclick="document.getElementById(\'bgImageInput\').click()">';
        html += '<p>&#128444; Click or drop image</p>';
        html += '<button class="upload-btn" type="button">Choose Image</button>';
        html += '<img class="preview-img" id="previewImg" alt="Preview">';
        html += '<button class="remove-img-btn" id="removeImgBtn" onclick="event.stopPropagation(); removeBgImage()">Remove Image</button>';
        html += '</div>';
        html += '<input type="file" id="bgImageInput" accept="image/*" onchange="handleImageUpload(event)">';
    }

    html += '<button class="reset-btn" onclick="resetTheme()">Reset to Default</button>';
    html += '</div></div>';

    container.innerHTML = html;

    if (showBg) {
        var bgGrid = document.getElementById('bgColorGrid');
        if (bgGrid) {
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
    }

    if (showAccent) {
        var accentGrid = document.getElementById('accentColorGrid');
        if (accentGrid) {
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
    }

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
    saveTheme(THEME_KEYS.bgImage, null);
    location.reload();
}
