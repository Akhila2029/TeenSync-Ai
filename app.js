/* ===========================
   TeenSync - app.js
   Global JS (all pages)
   =========================== */

// ==========================================
// ====== AUTHENTICATION PROTECTION ======
// ==========================================
const currentPath = window.location.pathname.toLowerCase();
const isProtectedPage = currentPath.includes('dashboard.html') || 
                        currentPath.includes('community.html') || 
                        currentPath.includes('resources.html');

const token = localStorage.getItem('teensync_token');

if (isProtectedPage && !token) {
  // Redirect to login if a protected page is accessed without a token
  window.location.href = 'login.html';
}

// Global logout function
function handleLogout() {
  localStorage.removeItem('teensync_token');
  window.location.href = 'index.html';
}

// Fetch user profile and update dashboard elements
async function loadUserProfile() {
  if (!token) return;
  try {
    // 1. Fetch User Profile
    const res = await fetch(`${window.TEENSYNC_CONFIG.API_BASE_URL}/api/v1/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      const data = await res.json();
      const userName = data.username;
      
      // Update welcome header
      const welcomeHeader = document.getElementById('dashboard-welcome-name');
      if (welcomeHeader) {
        welcomeHeader.innerHTML = `Hey ${userName} 👋`;
      }
      
      // Update avatar initials
      const avatarDiv = document.getElementById('dashboard-avatar');
      if (avatarDiv) {
        avatarDiv.title = userName;
        avatarDiv.textContent = userName.substring(0, 2).toUpperCase();
      }
      
      // Update Luna greeting
      const lunaGreeting = document.getElementById('luna-greeting-name');
      if (lunaGreeting) {
        lunaGreeting.textContent = `Hi ${userName}!`;
      }

      // Universal Personalization (Profiles, Testimonials, Community)
      document.querySelectorAll('[data-personalize="name"]').forEach(el => {
        el.textContent = userName;
        if (el.textContent.includes(",")) { // Fix for "Alex, 16" -> "Name, 16"
           const age = el.textContent.split(",")[1] || "16";
           el.textContent = `${userName}, ${age.trim()}`;
        }
      });
      document.querySelectorAll('[data-personalize="initials"]').forEach(el => {
        el.textContent = userName.substring(0, 1).toUpperCase();
      });
      
      const commAvatar = document.getElementById('community-avatar');
      if (commAvatar) {
        commAvatar.textContent = userName.substring(0, 1).toUpperCase();
        commAvatar.title = userName;
      }
    }

    // 2. Fetch Mood Streak
    const streakRes = await fetch(`${window.TEENSYNC_CONFIG.API_BASE_URL}/api/v1/mood/streak`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (streakRes.ok) {
      const streakData = await streakRes.json();
      const streakElement = document.getElementById('dashboard-streak-number');
      if (streakElement) {
        streakElement.textContent = streakData.streak_days || 0;
      }
    }

    // 3. Simple Leveling & Volume Calculation
    const historyRes = await fetch(`${window.TEENSYNC_CONFIG.API_BASE_URL}/api/v1/mood/history?days=365`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (historyRes.ok) {
      const historyData = await historyRes.json();
      const totalEntries = historyData.total || 0;
      
      // Update Sessions Count
      const sessionsCount = document.getElementById('dashboard-sessions-count');
      if (sessionsCount) {
        sessionsCount.textContent = totalEntries;
      }
      
      // Update XP Earned (Mock: 25 XP per entry)
      const xpEarned = document.getElementById('dashboard-xp-earned');
      if (xpEarned) {
        xpEarned.textContent = totalEntries * 25;
      }
      
      // Update Level & Progress
      const level = Math.floor(totalEntries / 5) + 1; // 1 level every 5 mood logs
      const progressToNext = (totalEntries % 5) * 20; // 20% progress per log
      
      const levelLabel = document.getElementById('dashboard-level-label');
      if (levelLabel) {
        levelLabel.textContent = `Level ${level} Explorer`;
      }
      
      const progressBar = document.getElementById('dashboard-level-progress');
      if (progressBar) {
        progressBar.style.width = `${progressToNext || 5}%`; // Min 5% width for visual flair
      }
    }

  } catch (err) {
    console.error('Failed to load user profile or stats', err);
  }
}

// Attach logout to any button with id="logout-btn" and load profile
document.addEventListener('DOMContentLoaded', () => {
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleLogout);
  }
  
  if (typeof currentPath !== 'undefined' && currentPath.includes('dashboard.html')) {
    loadUserProfile();
  }
});

// ---- Navbar scroll effect ----
const navbar = document.getElementById('navbar');
if (navbar) {
  window.addEventListener('scroll', () => {
    if (window.scrollY > 40) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  });
}

// ---- Mobile menu toggle ----
const menuBtn = document.getElementById('menu-btn');
const mobileMenu = document.getElementById('mobile-menu');
if (menuBtn && mobileMenu) {
  menuBtn.addEventListener('click', () => {
    const isHidden = mobileMenu.classList.contains('hidden');
    mobileMenu.classList.toggle('hidden', !isHidden);
    mobileMenu.style.animation = isHidden ? 'slideInLeft 0.3s ease forwards' : '';
  });
}

// ---- Scroll reveal animation ----
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
    }
  });
}, { threshold: 0.12, rootMargin: '0px 0px -50px 0px' });

document.querySelectorAll('.reveal').forEach(el => revealObserver.observe(el));

// ---- Counter animation ----
function animateCounter(el, target, suffix = '') {
  const duration = 2000;
  const start = performance.now();
  const update = (time) => {
    const elapsed = time - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(eased * target);
    el.textContent = current.toLocaleString() + suffix;
    if (progress < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

const counterObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const el = entry.target;
      const target = parseInt(el.getAttribute('data-target'));
      const suffix = el.getAttribute('data-suffix') || '';
      animateCounter(el, target, suffix);
      counterObserver.unobserve(el);
    }
  });
}, { threshold: 0.5 });

document.querySelectorAll('.counter').forEach(el => counterObserver.observe(el));

// ---- Three.js Hero Animation (index page only) ----
const heroCanvas = document.getElementById('hero-canvas');
if (heroCanvas && typeof THREE !== 'undefined') {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
  const renderer = new THREE.WebGLRenderer({ canvas: heroCanvas, alpha: true, antialias: true });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  const colors = [0x9ea1e8, 0xbdbeff, 0xa8d8ff, 0xb4f5bd, 0xd4b8ff];
  const blobs = [];

  for (let i = 0; i < 7; i++) {
    const geometry = new THREE.IcosahedronGeometry(Math.random() * 2.5 + 1.5, 3);
    const material = new THREE.MeshPhongMaterial({
      color: colors[i % colors.length],
      transparent: true,
      opacity: 0.35,
      shininess: 80,
      specular: new THREE.Color(0xffffff),
    });
    const blob = new THREE.Mesh(geometry, material);
    blob.position.set(
      (Math.random() - 0.5) * 24,
      (Math.random() - 0.5) * 14,
      (Math.random() - 0.5) * 8 - 12
    );
    blob.originalPos = blob.position.clone();
    blob.rotSpeed = { x: (Math.random() - 0.5) * 0.004, y: (Math.random() - 0.5) * 0.003 };
    blobs.push(blob);
    scene.add(blob);
  }

  // Ambient + directional lights
  scene.add(new THREE.AmbientLight(0xffffff, 0.7));
  const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
  dirLight.position.set(5, 10, 5);
  scene.add(dirLight);
  const pointLight = new THREE.PointLight(0xbdbeff, 1.5, 30);
  pointLight.position.set(-5, 5, 5);
  scene.add(pointLight);

  camera.position.z = 18;

  // Mouse parallax
  let mouse = { x: 0, y: 0 };
  window.addEventListener('mousemove', (e) => {
    mouse.x = (e.clientX / window.innerWidth - 0.5) * 2;
    mouse.y = -(e.clientY / window.innerHeight - 0.5) * 2;
  });

  function animateBlobs() {
    requestAnimationFrame(animateBlobs);
    const t = Date.now() * 0.0004;

    blobs.forEach((blob, i) => {
      blob.position.x = blob.originalPos.x + Math.sin(t + i * 1.3) * 2.5 + mouse.x * 1.5;
      blob.position.y = blob.originalPos.y + Math.cos(t * 0.7 + i * 0.9) * 1.8 + mouse.y * 1;
      blob.rotation.x += blob.rotSpeed.x;
      blob.rotation.y += blob.rotSpeed.y;
      const scale = 1 + Math.sin(t * 0.6 + i) * 0.08;
      blob.scale.setScalar(scale);
    });

    camera.position.x += (mouse.x * 0.5 - camera.position.x) * 0.05;
    camera.position.y += (mouse.y * 0.3 - camera.position.y) * 0.05;
    camera.lookAt(scene.position);

    renderer.render(scene, camera);
  }
  animateBlobs();

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });
}

// ---- Toast notification ----
function showToast(message, icon = 'check_circle', color = '#575a93') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerHTML = `
    <span class="material-symbols-outlined" style="color:${color};font-variation-settings:'FILL' 1">${icon}</span>
    <span>${message}</span>
  `;
  document.body.appendChild(toast);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => toast.classList.add('show'));
  });

  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 400);
  }, 3000);
}
window.showToast = showToast;

// ---- Like button toggle ----
document.querySelectorAll('.like-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    btn.classList.toggle('liked');
    const count = btn.querySelector('.like-count');
    if (count) {
      const n = parseInt(count.textContent);
      count.textContent = btn.classList.contains('liked') ? n + 1 : n - 1;
    }
    if (btn.classList.contains('liked')) showToast('Liked! Spreading good vibes 💙', 'favorite', '#ac3149');
  });
});

// ---- Bookmark toggle ----
document.querySelectorAll('.bookmark-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    btn.classList.toggle('bookmarked');
    const icon = btn.querySelector('.material-symbols-outlined');
    if (icon) {
      icon.style.fontVariationSettings = btn.classList.contains('bookmarked')
        ? "'FILL' 1" : "'FILL' 0";
      icon.style.color = btn.classList.contains('bookmarked') ? '#575a93' : '';
    }
    if (btn.classList.contains('bookmarked')) showToast('Saved to your toolkit!', 'bookmark', '#575a93');
  });
});

// ---- Filter buttons (resources page) ----
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const filter = btn.getAttribute('data-filter') || 'all';
    filterResources(filter);
  });
});

function filterResources(category) {
  document.querySelectorAll('.resource-card').forEach(card => {
    const cat = card.getAttribute('data-category') || 'all';
    if (category === 'all' || cat === category) {
      card.style.display = '';
      card.style.animation = 'scaleIn 0.4s ease forwards';
    } else {
      card.style.display = 'none';
    }
  });
}

// ---- Mood tracker (dashboard) ----
document.querySelectorAll('.mood-option').forEach(opt => {
  opt.addEventListener('click', () => {
    document.querySelectorAll('.mood-option').forEach(o => o.classList.remove('selected'));
    opt.classList.add('selected');
    const mood = opt.getAttribute('data-mood');
    showToast(`Mood logged: ${mood}`, 'favorite', '#ac3149');
  });
});

// ---- Animate progress bars on scroll ----
const progressObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const fill = entry.target;
      const width = fill.getAttribute('data-width') || '0%';
      fill.style.width = width;
    }
  });
}, { threshold: 0.3 });

document.querySelectorAll('.progress-fill').forEach(el => progressObserver.observe(el));

// ---- Animate chart bars ----
const chartObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const bars = entry.target.querySelectorAll('.chart-bar-fill');
      bars.forEach((bar, i) => {
        setTimeout(() => {
          const h = bar.getAttribute('data-height') || '0%';
          bar.style.height = h;
        }, i * 80);
      });
    }
  });
}, { threshold: 0.2 });

document.querySelectorAll('.chart-bars').forEach(el => chartObserver.observe(el));

// ---- Start session button ----
const startBtn = document.getElementById('start-session-btn');
if (startBtn) {
  startBtn.addEventListener('click', () => {
    showToast('Starting your mindfulness session...', 'self_improvement', '#306b3f');
  });
}

// ---- Page transition on load ----
document.body.classList.add('page-transition');

// ---- Set active nav link ----
const currentPage = window.location.pathname.split('/').pop() || 'index.html';
document.querySelectorAll('.nav-link').forEach(link => {
  const href = link.getAttribute('href');
  if (href && currentPage.includes(href.replace('.html', ''))) {
    link.classList.add('active');
  }
});

// ==========================================
// ====== LUNA CHATBOT INTEGRATION ======
// ==========================================

const lunaChatToggle = document.getElementById('luna-chat-toggle');
const lunaChatWindow = document.getElementById('luna-chat-window');
const lunaChatClose = document.getElementById('luna-chat-close');
const lunaChatMessages = document.getElementById('luna-chat-messages');
const lunaChatInput = document.getElementById('luna-chat-input');
const lunaChatSend = document.getElementById('luna-chat-send');
const lunaTypingIndicator = document.getElementById('luna-typing-indicator');
const lunaToggleIcon = document.getElementById('luna-toggle-icon');

// Generate or get session ID for conversation memory
let chatSessionId = localStorage.getItem('luna_session_id');
if (!chatSessionId) {
  chatSessionId = 'session_' + Math.random().toString(36).substring(2, 15);
  localStorage.setItem('luna_session_id', chatSessionId);
}

if (lunaChatSend && lunaChatInput) {
  // If the toggle exists (floating widget mode), handle it
  if (lunaChatToggle && lunaChatWindow) {
    lunaChatToggle.addEventListener('click', () => {
      const isHidden = lunaChatWindow.classList.contains('hidden');
      if (isHidden) {
        lunaChatWindow.classList.remove('hidden');
        setTimeout(() => {
          lunaChatWindow.classList.remove('opacity-0', 'scale-95');
          lunaChatWindow.classList.add('opacity-100', 'scale-100');
          if (lunaToggleIcon) lunaToggleIcon.textContent = 'close';
        }, 10);
      } else {
        closeLunaChat();
      }
    });

    if (lunaChatClose) {
      lunaChatClose.addEventListener('click', closeLunaChat);
    }

    function closeLunaChat() {
      lunaChatWindow.classList.remove('opacity-100', 'scale-100');
      lunaChatWindow.classList.add('opacity-0', 'scale-95');
      if (lunaToggleIcon) lunaToggleIcon.textContent = 'chat';
      setTimeout(() => {
        lunaChatWindow.classList.add('hidden');
      }, 300);
    }
  }

  // Handle Input
  lunaChatSend.addEventListener('click', handleSendMessage);
  lunaChatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSendMessage();
  });

  async function handleSendMessage() {
    const message = lunaChatInput.value.trim();
    if (!message) return;

    // 1. Add user message
    addChatMessage(message, 'user');
    lunaChatInput.value = '';
    
    // 2. Show typing indicator
    lunaTypingIndicator.classList.remove('hidden');
    scrollToBottom();

    try {
      // 3. API Call to FastAPI Backend
      console.log('Sending message to Luna:', message);
      const response = await fetch(`${window.TEENSYNC_CONFIG.API_BASE_URL}/api/v1/chat/message`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ 
          message: message,
          session_id: chatSessionId 
        })
      });

      if (!response.ok) {
        throw new Error(`API returned status: ${response.status}`);
      }

      const data = await response.json();
      console.log('Received from API:', data);
      
      // Hide typing indicator
      lunaTypingIndicator.classList.add('hidden');

      // 4. Add bot response
      if (data && data.assistant_message && data.assistant_message.content) {
        addChatMessage(data.assistant_message.content, 'assistant');
        
        // Handle source document citations if provided gracefully
        if (data.source_docs && data.source_docs.length > 0) {
           const sourcesHtml = data.source_docs.map(doc => 
              `<span class="inline-block bg-primary/10 text-primary px-2 py-0.5 rounded text-[10px] mt-1 mr-1">${doc.topic || doc.source}</span>`
           ).join('');
           const hintDiv = document.createElement('div');
           hintDiv.className = 'text-xs text-on-surface-variant flex flex-wrap mt-1 opacity-70';
           hintDiv.innerHTML = 'Resources: ' + sourcesHtml;
           lunaChatMessages.appendChild(hintDiv);
           scrollToBottom();
        }
      } else {
        throw new Error('Invalid response format');
      }
      
    } catch (error) {
      console.error('Chat error:', error);
      lunaTypingIndicator.classList.add('hidden');
      addChatMessage("I'm having trouble connecting right now. Please check if the server is running or try again later.", 'error');
    }
  }

  function addChatMessage(text, sender) {
    const div = document.createElement('div');
    
    if (sender === 'user') {
      div.className = 'self-end bg-primary text-white px-4 py-2.5 rounded-2xl rounded-tr-sm max-w-[85%] text-sm';
      div.innerText = text;
    } else if (sender === 'assistant') {
      div.className = 'self-start bg-surface-container px-4 py-2.5 rounded-2xl rounded-tl-sm max-w-[85%] text-sm text-on-surface whitespace-pre-wrap';
      div.innerText = text;
    } else if (sender === 'error') {
      div.className = 'self-start bg-error/10 text-error px-4 py-2.5 rounded-2xl rounded-tl-sm max-w-[85%] text-sm';
      div.innerText = text;
    }
    
    // Check if the user mentioned a crisis-related term to show high priority
    if (sender === 'assistant' && text.includes("Helpline")) {
        div.style.borderLeft = "4px solid #ac3149";
    }

    lunaChatMessages.appendChild(div);
    scrollToBottom();
  }

  function scrollToBottom() {
    lunaChatMessages.scrollTop = lunaChatMessages.scrollHeight;
  }
}

