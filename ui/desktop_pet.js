/**
 * Jarvis Desktop Pet Client Logic
 * Handles interactive mascot animations, visemes, pupil tracking, pointing gestures,
 * and WebSocket synchronization with the Jarvis Web Server.
 */

document.addEventListener('DOMContentLoaded', () => {
    const eyeLeft = document.getElementById('pet-eye-left');
    const eyeRight = document.getElementById('pet-eye-right');
    const pupilLeft = document.getElementById('pet-pupil-left');
    const pupilRight = document.getElementById('pet-pupil-right');
    const mouth = document.getElementById('pet-mouth');
    const armLeft = document.getElementById('pet-arm-left');
    const armRight = document.getElementById('pet-arm-right');
    const antennaLight = document.getElementById('pet-antenna-light');
    const speechBubble = document.getElementById('pet-speech-bubble');
    const speechText = document.getElementById('pet-speech-text');
    const shutterBadge = document.getElementById('shutter-indicator-badge');
    const btnMic = document.getElementById('btn-pet-mic');
    const mascotSvg = document.getElementById('pet-mascot-svg');

    let currentMood = 'idle';
    let isBlinking = false;
    let isSpeaking = false;
    let ws = null;

    // =========================================================================
    // 1. Natural Eye Blinking & Pupil Tracking
    // =========================================================================

    function triggerBlink() {
        if (isBlinking || currentMood === 'happy') return;
        isBlinking = true;
        if (eyeLeft && eyeRight) {
            eyeLeft.setAttribute('ry', '2');
            eyeRight.setAttribute('ry', '2');
            if (pupilLeft) pupilLeft.style.opacity = '0';
            if (pupilRight) pupilRight.style.opacity = '0';
        }

        setTimeout(() => {
            if (eyeLeft && eyeRight) {
                eyeLeft.setAttribute('ry', '16');
                eyeRight.setAttribute('ry', '16');
                if (pupilLeft) pupilLeft.style.opacity = '1';
                if (pupilRight) pupilRight.style.opacity = '1';
            }
            isBlinking = false;
        }, 150);
    }

    setInterval(() => {
        if (Math.random() > 0.4) triggerBlink();
    }, 3500);

    // Mouse Tracking for Pupils
    window.addEventListener('mousemove', (e) => {
        const cx = window.innerWidth / 2;
        const cy = window.innerHeight / 2;
        const dx = Math.max(-6, Math.min(6, (e.clientX - cx) / 20));
        const dy = Math.max(-6, Math.min(6, (e.clientY - cy) / 20));

        if (pupilLeft) {
            pupilLeft.setAttribute('cx', (80 + dx).toFixed(1));
            pupilLeft.setAttribute('cy', (88 + dy).toFixed(1));
        }
        if (pupilRight) {
            pupilRight.setAttribute('cx', (120 + dx).toFixed(1));
            pupilRight.setAttribute('cy', (88 + dy).toFixed(1));
        }
    });

    // =========================================================================
    // 2. Pointing Gestures & Shutter Flash
    // =========================================================================

    window.pointToTarget = function(direction = 'left') {
        currentMood = 'pointing';
        if (direction === 'left' && armLeft) {
            armLeft.classList.add('arm-pointing-left');
            if (armRight) armRight.classList.remove('arm-pointing-right');
        } else if (armRight) {
            armRight.classList.add('arm-pointing-right');
            if (armLeft) armLeft.classList.remove('arm-pointing-left');
        }

        setTimeout(() => {
            if (armLeft) armLeft.classList.remove('arm-pointing-left');
            if (armRight) armRight.classList.remove('arm-pointing-right');
            currentMood = 'idle';
        }, 4500);
    };

    window.triggerShutterFlash = function() {
        if (shutterBadge) {
            shutterBadge.classList.remove('hidden');
            shutterBadge.classList.add('shutter-active');
            setTimeout(() => {
                shutterBadge.classList.add('hidden');
                shutterBadge.classList.remove('shutter-active');
            }, 2500);
        }
        if (antennaLight) {
            antennaLight.setAttribute('fill', '#f59e0b');
            setTimeout(() => antennaLight.setAttribute('fill', '#00f2ff'), 1200);
        }
    };

    // =========================================================================
    // 3. Speech Bubble & Viseme Synchronization
    // =========================================================================

    const VISEMES = {
        idle: "M 88 110 Q 100 114 112 110",
        open: "M 88 108 Q 100 118 112 108",
        wide: "M 84 109 Q 100 120 116 109",
        round: "M 92 108 A 8 8 0 1 0 108 108 Z"
    };

    window.speakText = function(text) {
        if (!text) return;
        isSpeaking = true;
        currentMood = 'speaking';
        
        if (speechBubble && speechText) {
            speechText.innerText = text;
            speechBubble.classList.remove('hidden');
        }

        let step = 0;
        const visemeKeys = ['open', 'wide', 'round', 'idle'];
        const mouthTimer = setInterval(() => {
            if (!isSpeaking) {
                clearInterval(mouthTimer);
                if (mouth) mouth.setAttribute('d', VISEMES.idle);
                return;
            }
            const key = visemeKeys[step % visemeKeys.length];
            if (mouth) mouth.setAttribute('d', VISEMES[key]);
            step++;
        }, 130);

        // Auto-dismiss bubble after reading duration
        const duration = Math.max(3000, text.length * 70);
        setTimeout(() => {
            isSpeaking = false;
            currentMood = 'idle';
            if (speechBubble) speechBubble.classList.add('hidden');
        }, duration);
    };

    // =========================================================================
    // 4. WebSocket Synchronization with Web Server
    // =========================================================================

    function connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host || 'localhost:8000';
        ws = new WebSocket(`${protocol}//${host}/ws/desktop_pet`);

        ws.onopen = () => {
            console.log('[Desktop Pet] Connected to Jarvis Web Server.');
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'point_to') {
                    window.pointToTarget(data.direction || 'left');
                    if (data.message) window.speakText(data.message);
                } else if (data.type === 'shutter_flash') {
                    window.triggerShutterFlash();
                } else if (data.type === 'speak') {
                    window.speakText(data.text);
                } else if (data.type === 'mood') {
                    currentMood = data.mood || 'idle';
                }
            } catch (err) {
                console.warn('[Desktop Pet] Error parsing WS message:', err);
            }
        };

        ws.onclose = () => {
            setTimeout(connectWebSocket, 3000);
        };
    }

    connectWebSocket();

    // =========================================================================
    // 5. Mascot Poke Reactions & Quick Mic
    // =========================================================================

    if (mascotSvg) {
        mascotSvg.addEventListener('click', () => {
            triggerBlink();
            window.speakText("Jarvis Desktop Pet online, sir!");
        });
    }

    if (btnMic) {
        btnMic.addEventListener('click', () => {
            window.triggerShutterFlash();
            window.speakText("Listening to your command...");
        });
    }
});
