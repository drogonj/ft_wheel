import { getCookie } from "./utils.js";

let countDownDate;
export let counter_distance = 0;

// Saving some constants for time calculations
const hoursMult1 = 1000 * 60 * 60 * 24
const hoursMult2 = 1000 * 60 * 60;

function startTimer() {
  setInterval(function() {
    if (!countDownDate) return;

    var now = new Date().getTime();
    counter_distance = countDownDate - now;

    var hours = Math.floor(counter_distance / hoursMult2);
    var minutes = Math.floor((counter_distance % hoursMult2) / 60000);
    var seconds = Math.floor((counter_distance % 60000) / 1000);

    console.log(counter_distance, hoursMult2, hours)

    document.getElementById("counter").innerHTML = hours + "h "
      + minutes + "m " + seconds + "s ";

    if (counter_distance < 0) {
      document.getElementById("counter").innerHTML = "You can turn the wheel !";
    }
  }, 1000);
}

// INIT
export async function init_time_to_spin()  {
  // Test mode or superuser: infinite spins, no countdown logic needed
  if (window.USER_TEST_MODE) {
    const el = document.getElementById("counter");
    if (el) {
      el.textContent = '∞';
    }
    counter_distance = 0;
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

    const now = new Date().getTime();
    const futureTime = now + (totalHours * hoursMult2) + (minutes * 60000) + (seconds * 1000);

    countDownDate = futureTime;

    startTimer(); // Start timer after countdown date is set

  } catch (error) {
    console.error('Error during time_to_spin update:', error);
  }
}

init_time_to_spin();