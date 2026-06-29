// Summer theme background animation

// Create background canvas for gradient and waves
const bgCanvas = document.createElement('canvas');
bgCanvas.style.position = 'fixed';
bgCanvas.style.top = '0';
bgCanvas.style.left = '0';
bgCanvas.style.width = '100%';
bgCanvas.style.height = '100%';
bgCanvas.style.zIndex = '-2';
bgCanvas.style.pointerEvents = 'none';
bgCanvas.width = window.innerWidth;
bgCanvas.height = window.innerHeight;
document.body.appendChild(bgCanvas);
const bgCtx = bgCanvas.getContext('2d');

// Draw summer gradient background
function drawBackground() {
    const gradient = bgCtx.createLinearGradient(0, 0, 0, bgCanvas.height);
    gradient.addColorStop(0, '#87CEEB');    // Sky blue
    gradient.addColorStop(0.5, '#FFA07A');  // Light salmon
    gradient.addColorStop(1, '#FF6347');    // Tomato red (sunset)
    bgCtx.fillStyle = gradient;
    bgCtx.fillRect(0, 0, bgCanvas.width, bgCanvas.height);
    
    // Draw animated waves
    const time = Date.now() * 0.001;
    bgCtx.fillStyle = 'rgba(30, 144, 255, 0.15)';
    
    for (let i = 0; i < 3; i++) {
        bgCtx.beginPath();
        for (let x = 0; x <= bgCanvas.width; x += 10) {
            const y = bgCanvas.height * 0.7 + Math.sin(x * 0.01 + time + i) * 30 + i * 20;
            if (x === 0) {
                bgCtx.moveTo(x, y);
            } else {
                bgCtx.lineTo(x, y);
            }
        }
        bgCtx.lineTo(bgCanvas.width, bgCanvas.height);
        bgCtx.lineTo(0, bgCanvas.height);
        bgCtx.closePath();
        bgCtx.fill();
    }
}

const animate = () => {
    drawBackground();
    requestAnimationFrame(animate);
}

window.addEventListener('resize', () => {
    bgCanvas.width = window.innerWidth;
    bgCanvas.height = window.innerHeight;
});

animate();
