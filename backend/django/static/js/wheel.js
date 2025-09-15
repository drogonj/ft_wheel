import { getCookie } from "./utils.js";
import { init_time_to_spin, counter_distance } from "./counter.js";

function adjustScale() {
    const screenWidth = document.documentElement.clientWidth;
    const screenHeight = document.documentElement.clientHeight;
    const scaleValue = Math.min(screenHeight / 1800, screenWidth / 1200);
    document.querySelector('#spin_the_wheel').style.transform = `scale(${scaleValue})`;
}

window.addEventListener('resize', adjustScale);
adjustScale();

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
    // Adapter la formule pour qu'elle corresponde à l'orientation des secteurs
    return (tot - Math.floor(mod(ang, TAU) / TAU * tot) - 1) % tot;
};

const tickSound = new Audio('/static/sounds/tick.mp3');
tickSound.volume = 0.5;

const winSound = new Audio('/static/sounds/win.mp3');
winSound.volume = 0.5;

function playTickSound() {
    const tickSoundClone = tickSound.cloneNode();
    tickSoundClone.play().catch(e => console.log("Lecture audio bloquée:", e));
}
function playWinSound() {
    const winSoundClone = winSound.cloneNode();
    winSoundClone.play().catch(e => console.log("Lecture audio bloquée:", e));
}

document.addEventListener('wheelConfigChanged', (e) => {
    
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
    elSpin.removeAttribute('style');
    
    update();

});

const showWinPopup = (message) => {
    const popup = document.getElementById('win-popup');
    const messageEl = document.getElementById('win-message');

    playWinSound();
    messageEl.textContent = message || "Vous avez gagné un prix!";
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
    // ctx.lineWidth = 2; // Définir l'épaisseur de la bordure
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
    const currentProgress = spinAnimation?.effect.getComputedTiming().progress ?? 0;

    const angDiff = ang - oldAng;
    const angCurr = angDiff * currentProgress;
    const angAbs = mod(oldAng + angCurr, TAU);

    const sectorIndexNew = getIndex(angAbs);

    if (sectorIndex !== sectorIndexNew) {
        playTickSound();
    }
    sectorIndex = sectorIndexNew;
    if (spinAnimation) {
        elSpin.textContent = sectors[sectorIndex].label;
        elSpin.style.background = sectors[sectorIndex].color;
    } else {
        elSpin.textContent = "SPIN";
        elSpin.removeAttribute('style');
    }
};

const spin = (index, duration) => {

    // PROBLÈME ICI: L'index est inversé, mais le reste du code ne tient pas compte de cette inversion
    // var nindex = tot - index; // Commentons cette ligne qui cause le problème

    // On utilise l'index directement
    const nindex = index; 

    // Absolute current angle (without turns)
    oldAng = ang;
    const angAbs = mod(ang, TAU);

    // Absolute new angle - adaptation pour corriger le calcul de l'angle
    let angNew = arc * (tot - nindex - 1); // Ici on adapte la formule pour l'orientation
    
    // (backtrack a bit to not end on the exact edge)
    angNew += rand(0, arc * 0.7); // On ajoute un peu d'aléatoire dans le secteur, sans risquer de déborder

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
        cancelAnimationFrame(animationFrameId);
        elSpin.textContent = "Spin";
        elSpin.style.background = "#1b1728";
        elSpin.classList.remove('disabled'); // Réactive le bouton
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
    if (spinAnimation || elSpin.classList.contains('disabled') || counter_distance > 0) return; // Already animating / disabled or counter is active

    try {
        const response = await fetch(`/spin/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
        });

        if (!response.ok) {
            console.error(`Can't spin wheel: ${response.status}`);
            elSpin.classList.remove('disabled');
            return;
        }

        const result = await response.json();
        const targetIndex = result.result;
        if (targetIndex >= 0 && targetIndex < sectors.length) {
            // REMOVE: engine(); // Don't call engine() here
            spin(targetIndex);
        } else {
            console.error("Index de secteur invalide:", targetIndex);
            elSpin.classList.remove('disabled');
        }
    } catch (error) {
        console.error('Error during spin:', error);
        elSpin.classList.remove('disabled');
    }
});
window._spinListenerAdded = true;

// INIT!
sectors.forEach(drawSector);
update();