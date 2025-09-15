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

    var hours = Math.floor((counter_distance % hoursMult1) / hoursMult2);
    var minutes = Math.floor((counter_distance % hoursMult2) / 60000);
    var seconds = Math.floor((counter_distance % 60000) / 1000);

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

    const timeParts = result.timeToSpin.split(":");
    const hours = parseInt(timeParts[0], 10);
    const minutes = parseInt(timeParts[1], 10);
    const seconds = parseFloat(timeParts[2]);

    const now = new Date().getTime();
    const futureTime = now + (hours * hoursMult2) + (minutes * 60000) + (seconds * 1000);

    countDownDate = futureTime;

    startTimer(); // Start timer after countdown date is set

  } catch (error) {
    console.error('Error during time_to_spin update:', error);
  }
}

init_time_to_spin();