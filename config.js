/**
 * TeenSync Global Configuration
 * 
 * In development, we point to localhost.
 * When deployed, we point to our Render backend URL.
 */

const CONFIG = {
  // Replace with your Render URL after deployment (e.g., https://teensync-api.onrender.com)
  API_BASE_URL: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : 'https://teensync-api.onrender.com' // Placeholder – update this after Render deployment
};

// Ensure this is globally available
window.TEENSYNC_CONFIG = CONFIG;
