/**
 * @file sensorDisplay.js
 * @description Functions for displaying foot pressure and accelerometer sensor data
 */

/**
 * Initialize foot pressure bar visualizations
 * Creates 18 bars for each foot (left and right)
 */
function initFootBars() {
    const leftBars = document.getElementById('leftFootBars');
    const rightBars = document.getElementById('rightFootBars');

    for (let i = 0; i < 18; i++) {
        leftBars.innerHTML += `<div class="w-1 bg-blue-500 sensor-bar" style="height: 5%"></div>`;
        rightBars.innerHTML += `<div class="w-1 bg-green-500 sensor-bar" style="height: 5%"></div>`;
    }
}

/**
 * Update foot pressure display with new sensor data
 * @param {Object} data - Foot sensor data object
 * @param {Object} data.data - Inner data object
 * @param {string} data.data.foot - 'LEFT' or 'RIGHT'
 * @param {number[]} data.data.values - Array of 18 sensor values
 * @param {number} data.data.max - Maximum sensor value
 * @param {number} data.data.avg - Average sensor value
 */
function updateFootDisplay(data) {
    if (!data || !data.data) return;

    const foot = data.data.foot || 'LEFT';
    const values = data.data.values || [];
    const max = data.data.max || 0;
    const avg = data.data.avg || 0;

    const barsContainer = document.getElementById(foot === 'LEFT' ? 'leftFootBars' : 'rightFootBars');
    const bars = barsContainer.querySelectorAll('.sensor-bar');

    values.forEach((val, i) => {
        if (bars[i]) {
            const height = Math.min(100, Math.max(5, (val / 100) * 100));
            bars[i].style.height = `${height}%`;
        }
    });

    document.getElementById(foot === 'LEFT' ? 'leftMax' : 'rightMax').textContent = max.toFixed(1);
    document.getElementById(foot === 'LEFT' ? 'leftAvg' : 'rightAvg').textContent = avg.toFixed(1);

    document.getElementById('footStatus').textContent = new Date().toLocaleTimeString();

    // Increment counts when in recording state
    if (isRecording) {
        footReadingCount++;
        document.getElementById('footCount').textContent = footReadingCount;
    }
}

/**
 * Update accelerometer display with new sensor data
 * @param {Object} data - Accelerometer sensor data object
 * @param {Object} data.data - Inner data object
 * @param {Object} data.data.acc - Acceleration values {x, y, z}
 * @param {Object} data.data.gyro - Gyroscope values {x, y, z}
 * @param {Object} data.data.angle - Angle values {roll, pitch, yaw}
 */
function updateAccelDisplay(data) {
    if (!data || !data.data) return;

    const acc = data.data.acc || {};
    const gyro = data.data.gyro || {};
    const angle = data.data.angle || {};

    document.getElementById('accX').textContent = (acc.x || 0).toFixed(2);
    document.getElementById('accY').textContent = (acc.y || 0).toFixed(2);
    document.getElementById('accZ').textContent = (acc.z || 0).toFixed(2);

    document.getElementById('gyroX').textContent = (gyro.x || 0).toFixed(2);
    document.getElementById('gyroY').textContent = (gyro.y || 0).toFixed(2);
    document.getElementById('gyroZ').textContent = (gyro.z || 0).toFixed(2);

    document.getElementById('roll').textContent = (angle.roll || 0).toFixed(2);
    document.getElementById('pitch').textContent = (angle.pitch || 0).toFixed(2);
    document.getElementById('yaw').textContent = (angle.yaw || 0).toFixed(2);

    document.getElementById('accelStatus').textContent = new Date().toLocaleTimeString();

    // Increment counts when in recording state
    if (isRecording) {
        accelReadingCount++;
        document.getElementById('accelCount').textContent = accelReadingCount;
    }
}
