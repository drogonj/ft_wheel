import { getCookie } from "./utils.js";
import { init_time_to_spin, counter_distance } from "./counter.js";
import { showLoadingIndicator, hideLoadingIndicator } from "./menu.js";


// Function to reload wheel data dynamically
window.reloadWheelData = async function() {
    try {
        showLoadingIndicator();
        
        const response = await fetch('/api/current-wheel-config/');
        if (!response.ok) {
            throw new Error(`Failed to fetch wheel config: ${response.status}`);
        }
        
        const data = await response.json();
        const currentMode = data.current_mode;
        
        if (!currentMode) {
            throw new Error('No wheel configuration available');
        }
        
        // Fetch the actual wheel page to get the new sectors
        const wheelResponse = await fetch(`/?mode=${currentMode}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        if (wheelResponse.ok) {
            // For now, we'll do a page reload to ensure everything is synchronized
            // This is safer than trying to parse HTML and extract sectors
            window.location.href = `/?mode=${currentMode}&t=${Date.now()}`;
        } else {
            throw new Error('Failed to reload wheel data');
        }
        
    } catch (error) {
        console.error('Error reloading wheel data:', error);
        hideLoadingIndicator();
        alert('Failed to reload wheel. Please refresh the page.');
    }
};

function adjustScale() {
    const screenWidth = document.documentElement.clientWidth;
    const screenHeight = document.documentElement.clientHeight;
    const scaleValue = Math.min(screenHeight / 1800, screenWidth / 1200);
    document.querySelector('#spin_the_wheel').style.transform = `scale(${scaleValue})`;
}

window.addEventListener('resize', adjustScale);
adjustScale();

// Use global window.sectors provided by template
let sectors = window.sectors;
if (typeof sectors === 'string') {
    try { sectors = JSON.parse(sectors); } catch(e) { console.error('Invalid sectors JSON string', e); sectors = []; }
}
if (!Array.isArray(sectors)) {
    console.error('sectors is not an array after parse, defaulting to []');
    sectors = [];
}
window.sectors = sectors; // ensure canonical

// Generate random float in range min-max:
const rand = (m, M) => Math.random() * (M - m) + m;
// Fix negative modulo stackoverflow.com/a/71167019/383904
const mod = (n, m) => (n % m + m) % m;

window.tot = sectors.length;
window.elSpin = document.querySelector("#spin");
window.elWheel = document.querySelector("#wheel");
window.ctx = elWheel.getContext`2d`;
window.dia = 1000;

ctx.canvas.width = dia;
ctx.canvas.height = dia;

window.rad = dia / 2;
window.PI = Math.PI;
window.TAU = 2 * PI;
window.arc = TAU / tot;
window.angOffset = TAU * 0.75; // needle is north

window.sectorIndex = 0; // Current sector index
window.oldAng = 0;
window.ang = 0; // Angle rotation in radians

window.spinAnimation = null;
window.animationFrameId = null;


//* Get index of current sector */
window.getIndex = (ang) => {
    // Adapt for the orientation of the wheel (starting point)
    return (tot - Math.floor(mod(ang, TAU) / TAU * tot) - 1) % tot;
};

const tickSound = new Audio('/static/sounds/tick.mp3');
tickSound.volume = 0.5;

const winSound = new Audio('/static/sounds/win.mp3');
winSound.volume = 0.5;

function playTickSound() {
    const tickSoundClone = tickSound.cloneNode();
    tickSoundClone.play().catch(e => console.log("Audio playback blocked:", e));
}
function playWinSound() {
    const winSoundClone = winSound.cloneNode();
    winSoundClone.play().catch(e => console.log("Audio playback blocked:", e));
}


document.addEventListener('wheelConfigChanged', (e) => {
    // If an external script updated window.sectors, rebind local sectors
    if (Array.isArray(window.sectors)) {
        sectors = window.sectors;
    }
    window.tot = sectors.length;
    window.arc = TAU / tot;
    
    ctx.clearRect(0, 0, dia, dia);
    sectors.forEach(drawSector);
    
    ang = 0;
    oldAng = 0;
    if (spinAnimation) {
        spinAnimation.cancel();
        spinAnimation = null;
    }
    elSpin.textContent = "SPIN";
    update();

});


const showWinPopup = (message) => {
    const popup = document.getElementById('win-popup');
    const messageEl = document.getElementById('win-message');

    playWinSound();
    messageEl.textContent = message || "You won a prize!";
    popup.style.display = 'flex';
    const closeBtn = document.querySelector('.close-popup');
    const claimBtn = document.getElementById('claim-prize');
    const closePopup = () => {
        popup.style.display = 'none';
    };

    closeBtn.removeEventListener('click', closePopup);
    claimBtn.removeEventListener('click', closePopup);

    closeBtn.addEventListener('click', closePopup);
    claimBtn.addEventListener('click', closePopup);
    
}


//* Draw sectors and prizes texts to canvas */
const drawSector = (sector, i) => {
    const ang = arc * i;
    ctx.save();

    // COLOR
    ctx.beginPath();
    ctx.fillStyle = sector.color;
    ctx.moveTo(rad, rad);
    ctx.arc(rad, rad, rad, ang - 0.003, ang + arc + 0.003);
    ctx.lineTo(rad, rad);
    ctx.fill();

    // BORDER
    // ctx.strokeStyle = "#4c4f69";
    // ctx.lineWidth = 2; // Define the border width
    // ctx.stroke();

    // TEXT
    ctx.translate(rad, rad);
    ctx.rotate(ang + arc / 2);
    ctx.textAlign = "right";
    ctx.fillStyle = "#fff";
    ctx.font = `bold 2rem sans-serif`;
    ctx.fillText(sector.label, rad - 10, 10);
    
    ctx.restore();
};


const update = () => {
    if (spinAnimation) {
        const currentProgress = spinAnimation.effect.getComputedTiming().progress ?? 0;

        const angDiff = ang - oldAng;
        const angCurr = angDiff * currentProgress;
        const angAbs = mod(oldAng + angCurr, TAU);

        const sectorIndexNew = getIndex(angAbs);

        if (sectorIndex !== sectorIndexNew) {
            playTickSound();
        }
        sectorIndex = sectorIndexNew;
        
        elSpin.textContent = "";
        elSpin.style.background = "radial-gradient(circle,rgba(0, 0, 0, 0.54) 0%, rgb(48, 42, 123) 100%)";
    } else {
        // Wheel stopped
        if (window.USER_TEST_MODE || (window.CURRENT_WHEEL_TICKET_ONLY === 'false' && counter_distance <= 0) || (window.CURRENT_WHEEL_TICKET_ONLY === 'true' && window.CURRENT_WHEEL_TICKETS_COUNT > 0)) {
            // Can SPIN
            elSpin.textContent = "SPIN";
            elSpin.style.background = "linear-gradient(145deg, #4776E6, #8E54E9)";
        } else {
            // Can't SPIN
            elSpin.textContent = "🔒";
            elSpin.style.background = "#1b1728";
        }
    }
};


const spin = (index, duration) => {
    const nindex = index; 

    // Absolute current angle (without turns)
    oldAng = ang;
    const angAbs = mod(ang, TAU);

    // Absolute new angle - adaptation to orientation
    let angNew = arc * (tot - nindex - 1); // Here we adapt the formula for orientation
    
    // (backtrack a bit to not end on the exact edge)
    angNew += rand(0, arc * 0.7);

    // Fix negative angles
    angNew = mod(angNew, TAU);

    // Get the angle difference
    const angDiff = mod(angNew - angAbs, TAU);

    // Add N full revolutions
    const rev = TAU * Math.floor(rand(2, 4));

    ang += angDiff + rev;

    spinAnimation = elWheel.animate([{ rotate: `${ang + angOffset}rad` }], {
        duration: duration ?? rand(6000, 8000) * rev * 0.1,
        easing: "cubic-bezier(0.2, 0, 0.1, 1)",
        fill: "forwards"
    });

    spinAnimation.addEventListener("finish", () => {
        showWinPopup(sectors[index].message);
        spinAnimation = null;
        update();
    }, { once: true });

    init_time_to_spin();
};


const engine = () => {
    update();
    window.animationFrameId = requestAnimationFrame(engine);
};


// Only start the engine once!
if (!window._engineStarted) {
    engine();
    window._engineStarted = true;
}


// In your spin handler, REMOVE engine(); call
elSpin.addEventListener("click", async () => {
    if (spinAnimation) return;
    if (!window.USER_TEST_MODE) {
        // Gate: if ticket-only, require at least 1 ticket; else use cooldown
        if (window.CURRENT_WHEEL_TICKET_ONLY === 'true') {
            const n = parseInt(window.CURRENT_WHEEL_TICKETS_COUNT || '0', 10) || 0;
            if (n <= 0) return;
            window.CURRENT_WHEEL_TICKETS_COUNT = String(Math.max(0, n - 1));
        } else {
            if (!window.USER_TEST_MODE && counter_distance > 0) return; // In test mode we ignore countdown
        }
    }

    // Show loading indicator
    showLoadingIndicator();
    
    try {
        // Send POST request to /spin/ endpoint
        const response = await fetch(`/spin/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ wheel_version_id: window.CURRENT_WHEEL_VERSION_ID })
        });

        // Check for errors
        if (!response.ok) {
            hideLoadingIndicator();
            init_time_to_spin();
            if (response.status === 409) {
                // Outdated wheel configuration
                try {
                    const data = await response.json();
                    console.warn('Wheel configuration outdated. Expected version', data.expected_version);
                } catch(e) {}
                alert('Wheel has been updated. Reloading page...');
                window.location.reload();
                return;
            }
            if (response.status === 500) {
                alert('An error occurred while processing your spin.\n\nPlease contact an admin.\n\nYou may be refunded your ticket 🎟️ or your cooldown.');
                return;
            }
            console.error(`Can't spin wheel: ${response.status}`);
            return;
        }

        // Parse JSON response
        const result = await response.json();
        
        // Hide loading indicator after successful response
        hideLoadingIndicator();

        const targetIndex = result.result;
        if (result.wheel_version_id && result.wheel_version_id !== window.CURRENT_WHEEL_VERSION_ID) {
            // Sync local version id (should be same). If different just sync.
            window.CURRENT_WHEEL_VERSION_ID = result.wheel_version_id;
        }
        if (targetIndex >= 0 && targetIndex < sectors.length) {
            spin(targetIndex);
        } else {
            console.error("Invalid sector index:", targetIndex);
        }
    } catch (error) {
        // Hide loading indicator on catch error
        hideLoadingIndicator();
        console.error('Error during spin:', error);
    }
});
window._spinListenerAdded = true;


// INIT!
sectors.forEach(drawSector);
update();