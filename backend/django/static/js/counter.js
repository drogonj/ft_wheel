import { getCookie } from "./utils.js";

let countDownDate;
export let counter_distance = 0;
let timerId = null; // ensure a single interval
let counterEl = null; // cache DOM reference
let lastRenderedText = null; // avoid redundant DOM writes

// Saving some constants for time calculations
const hoursMult1 = 1000 * 60 * 60 * 24
const hoursMult2 = 1000 * 60 * 60;

function clearTimer() {
  if (timerId !== null) {
    clearInterval(timerId);
    timerId = null;
  }
}

function startTimer() {
  clearTimer();
  if (!counterEl) counterEl = document.getElementById("counter");

  const tick = () => {
    // Ticket-only wheels: no timer updates
    if (window.CURRENT_WHEEL_TICKET_ONLY === 'true') {
      return;
    }
    if (!countDownDate) return;

    const now = Date.now();
    counter_distance = countDownDate - now;

    const hours = Math.floor(counter_distance / hoursMult2);
    const minutes = Math.floor((counter_distance % hoursMult2) / 60000);
    const seconds = Math.floor((counter_distance % 60000) / 1000);

    let text;
    if (counter_distance < 0) {
      text = "You can turn the wheel !";
    } else {
      text = `${hours}h ${minutes}m ${seconds}s `;
    }

    if (counterEl && text !== lastRenderedText) {
      counterEl.textContent = text;
      lastRenderedText = text;
    }
  };

  // render immediately, then every second
  tick();
  timerId = setInterval(tick, 1000);
}

// INIT
export async function init_time_to_spin()  {
  // Test mode or superuser: infinite spins, no countdown logic needed
  if (window.USER_TEST_MODE) {
    clearTimer();
    if (!counterEl) counterEl = document.getElementById("counter");
    if (counterEl) {
      counterEl.textContent = '∞';
      lastRenderedText = '∞';
    }
    counter_distance = 0;
    return;
  } else if (window.CURRENT_WHEEL_TICKET_ONLY === 'true') {
    // Ticket-only: no cooldown fetch, we just display tickets
    clearTimer();
    if (!counterEl) counterEl = document.getElementById("counter");
    if (counterEl) {
      const n = parseInt(window.CURRENT_WHEEL_TICKETS_COUNT || '0', 10) || 0;
      const text = n === 1 ? 'You have 1 ticket 🎟️' : `You have ${n} tickets 🎟️`;
      if (text !== lastRenderedText) {
        counterEl.textContent = text;
        lastRenderedText = text;
      }
    }
    return;
  }

  try {
    const response = await fetch(`/time_to_spin/`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
    });
    if (!response.ok) {
      console.error(`Can't retrieve time_to_spin: ${response.status}`);
      return;
    }

    const result = await response.json();

    // Parse time format that can be "HH:MM:SS" or "X days, HH:MM:SS"
    let totalHours = 0;
    let minutes = 0;
    let seconds = 0;

    const timeStr = result.timeToSpin;
    if (timeStr.includes("days,") || timeStr.includes("day,")) {
      // Format: "X days, HH:MM:SS"
      const parts = timeStr.split(", ");
      const daysPart = parts[0]; // "6 days"
      const timePart = parts[1]; // "23:31:46.092474"
      
      const days = parseInt(daysPart.split(" ")[0], 10);
      const timeParts = timePart.split(":");
      const hours = parseInt(timeParts[0], 10);
      minutes = parseInt(timeParts[1], 10);
      seconds = parseFloat(timeParts[2]);
      
      totalHours = (days * 24) + hours;
    } else {
      // Format: "HH:MM:SS"
      const timeParts = timeStr.split(":");
      totalHours = parseInt(timeParts[0], 10);
      minutes = parseInt(timeParts[1], 10);
      seconds = parseFloat(timeParts[2]);
    }

  const now = Date.now();
    const futureTime = now + (totalHours * hoursMult2) + (minutes * 60000) + (seconds * 1000);

    countDownDate = futureTime;

    startTimer(); // Start timer after countdown date is set

  } catch (error) {
    console.error('Error during time_to_spin update:', error);
  }
}

init_time_to_spin();