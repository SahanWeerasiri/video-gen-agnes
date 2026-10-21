/* ==============================================================================
   Agnes Studio - Client Application Logic
   ============================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const promptInput = document.getElementById('promptInput');
  const scenesSlider = document.getElementById('scenesSlider');
  const scenesVal = document.getElementById('scenesVal');
  const durationSlider = document.getElementById('durationSlider');
  const durationVal = document.getElementById('durationVal');
  const fpsSelect = document.getElementById('fpsSelect');
  const motionToggle = document.getElementById('motionToggle');
  const continuityToggle = document.getElementById('continuityToggle');
  const btnGenerate = document.getElementById('btnGenerate');
  const btnDryRun = document.getElementById('btnDryRun');

  // Display elements
  const stageEmpty = document.getElementById('stageEmpty');
  const progressContainer = document.getElementById('progressContainer');
  const stageBadge = document.getElementById('stageBadge');
  const progressPercent = document.getElementById('progressPercent');
  const progressBarFill = document.getElementById('progressBarFill');
  const logBox = document.getElementById('logBox');
  const videoViewport = document.getElementById('videoViewport');
  const videoElement = document.getElementById('videoElement');
  const btnDownload = document.getElementById('btnDownload');
  const storyboardGallery = document.getElementById('storyboardGallery');
  const apiKeyStatus = document.getElementById('apiKeyStatus');
  const serverHealthBadge = document.getElementById('serverHealthBadge');
  const healthDot = document.getElementById('healthDot');
  const serverHealthText = document.getElementById('serverHealthText');

  // Engine Elements
  const tabZeroCost = document.getElementById('tabZeroCost');
  const tabNativeVideo = document.getElementById('tabNativeVideo');
  const zeroCostControls = document.getElementById('zeroCostControls');
  const nativeVideoControls = document.getElementById('nativeVideoControls');
  const videoDurationSlider = document.getElementById('videoDurationSlider');
  const videoDurationVal = document.getElementById('videoDurationVal');
  const nativeMultiSceneToggle = document.getElementById('nativeMultiSceneToggle');
  const nativeSceneCountWrapper = document.getElementById('nativeSceneCountWrapper');
  const nativeScenesSlider = document.getElementById('nativeScenesSlider');
  const nativeScenesVal = document.getElementById('nativeScenesVal');

  let currentEngine = 'zero_cost';
  let selectedStyle = null;
  let selectedSize = '1024x768';
  let selectedVideoSize = '720P';
  let selectedVideoAspect = '16:9';
  let activeTaskId = null;
  let pollInterval = null;

  // Initialize Config & Health Status
  fetchConfig();
  checkServerHealth();
  setInterval(checkServerHealth, 10000);

  // Engine Switcher
  tabZeroCost.addEventListener('click', () => setEngine('zero_cost'));
  tabNativeVideo.addEventListener('click', () => setEngine('native_video'));

  function setEngine(engine) {
    currentEngine = engine;
    if (engine === 'zero_cost') {
      tabZeroCost.classList.add('active');
      tabNativeVideo.classList.remove('active');
      zeroCostControls.style.display = 'block';
      nativeVideoControls.style.display = 'none';
      btnGenerate.querySelector('span').textContent = '✨ Generate Video ($0 Free)';
    } else {
      tabNativeVideo.classList.add('active');
      tabZeroCost.classList.remove('active');
      zeroCostControls.style.display = 'none';
      nativeVideoControls.style.display = 'block';
      btnGenerate.querySelector('span').textContent = '🎥 Generate AI Video (Agnes Video 2.5)';
    }
  }

  // Native Video Spec Listeners
  if (videoDurationSlider) {
    videoDurationSlider.addEventListener('input', (e) => {
      videoDurationVal.textContent = `${e.target.value}s`;
    });
  }

  document.querySelectorAll('[data-videosize]').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-videosize]').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      selectedVideoSize = btn.dataset.videosize;
    });
  });

  document.querySelectorAll('[data-videoaspect]').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-videoaspect]').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      selectedVideoAspect = btn.dataset.videoaspect;
    });
  });

  if (nativeMultiSceneToggle) {
    nativeMultiSceneToggle.addEventListener('change', (e) => {
      nativeSceneCountWrapper.style.display = e.target.checked ? 'block' : 'none';
    });
  }

  if (nativeScenesSlider) {
    nativeScenesSlider.addEventListener('input', (e) => {
      nativeScenesVal.textContent = e.target.value;
    });
  }

  // Slider Listeners
  scenesSlider.addEventListener('input', (e) => {
    scenesVal.textContent = e.target.value;
  });

  durationSlider.addEventListener('input', (e) => {
    durationVal.textContent = `${parseFloat(e.target.value).toFixed(1)}s`;
  });

  // Prompt Chips
  document.querySelectorAll('.chip-btn').forEach((chip) => {
    chip.addEventListener('click', () => {
      promptInput.value = chip.dataset.prompt;
      if (chip.dataset.style) {
        selectStyle(chip.dataset.style);
      }
      promptInput.focus();
    });
  });

  // Style Pills
  document.querySelectorAll('.style-pill').forEach((pill) => {
    pill.addEventListener('click', () => {
      const style = pill.dataset.style;
      if (pill.classList.contains('active')) {
        pill.classList.remove('active');
        selectedStyle = null;
      } else {
        document.querySelectorAll('.style-pill').forEach((p) => p.classList.remove('active'));
        pill.classList.add('active');
        selectedStyle = style;
      }
    });
  });

  function selectStyle(styleName) {
    document.querySelectorAll('.style-pill').forEach((pill) => {
      if (pill.dataset.style.toLowerCase() === styleName.toLowerCase()) {
        pill.classList.add('active');
        selectedStyle = styleName;
      } else {
        pill.classList.remove('active');
      }
    });
  }

  // Resolution Cards
  document.querySelectorAll('.res-card').forEach((card) => {
    card.addEventListener('click', () => {
      document.querySelectorAll('.res-card').forEach((c) => c.classList.remove('active'));
      card.classList.add('active');
      selectedSize = card.dataset.size;
    });
  });

  // Buttons
  btnGenerate.addEventListener('click', () => startTask(false));
  btnDryRun.addEventListener('click', () => startTask(true));

  async function checkServerHealth() {
    try {
      const res = await fetch('/api/health');
      if (!res.ok) throw new Error('Health check failed');
      const data = await res.json();

      serverHealthBadge.classList.remove('offline');
      healthDot.classList.remove('offline');
      serverHealthText.textContent = `Server Online (v${data.version})`;
      serverHealthBadge.title = `Server: ${data.server} v${data.version} | Uptime: ${data.uptime_seconds}s | FFmpeg: ${data.ffmpeg_installed ? 'Installed' : 'Missing'}`;
    } catch (err) {
      serverHealthBadge.classList.add('offline');
      healthDot.classList.add('offline');
      serverHealthText.textContent = 'Server Offline';
      serverHealthBadge.title = 'Cannot connect to backend server. Is python app.py running?';
    }
  }

  async function fetchConfig() {
    try {
      const res = await fetch('/api/config');
      const data = await res.json();
      if (data.has_api_key) {
        apiKeyStatus.innerHTML = `<span class="pulse-dot"></span> Key Connected (${data.masked_key})`;
        apiKeyStatus.style.color = '#34d399';
      } else {
        apiKeyStatus.innerHTML = `⚠️ Key Missing in .env`;
        apiKeyStatus.style.color = '#f59e0b';
      }
    } catch (err) {
      console.error('Error fetching config:', err);
    }
  }

  async function startTask(dryRun = false) {
    const prompt = promptInput.value.trim();
    if (!prompt) {
      alert('Please enter a video prompt or click one of the example ideas.');
      promptInput.focus();
      return;
    }

    setLoading(true);
    resetDisplay();

    const scenesCount = currentEngine === 'native_video'
      ? (nativeMultiSceneToggle && nativeMultiSceneToggle.checked ? parseInt(nativeScenesSlider.value, 10) : 1)
      : parseInt(scenesSlider.value, 10);

    const payload = {
      prompt: prompt,
      engine: currentEngine,
      scenes: scenesCount,
      duration: parseFloat(durationSlider.value),
      size: selectedSize,
      style: selectedStyle,
      fps: parseInt(fpsSelect.value, 10),
      enable_motion: motionToggle.checked,
      use_continuity: continuityToggle.checked,
      video_seconds: videoDurationSlider ? videoDurationSlider.value : "5",
      video_size: selectedVideoSize,
      video_aspect_ratio: selectedVideoAspect,
      video_mode: 'text',
      dry_run: dryRun,
    };

    try {
      addLog(`Submitting ${dryRun ? 'dry-run storyboard' : 'video'} request...`);
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || 'Request failed');
      }

      const data = await res.json();
      activeTaskId = data.task_id;
      addLog(`Task queued (ID: ${activeTaskId.slice(0, 8)}...)`);

      // Begin polling
      pollInterval = setInterval(pollTaskStatus, 1500);
    } catch (err) {
      addLog(`❌ Failed to start: ${err.message}`);
      stageBadge.textContent = 'Failed';
      stageBadge.style.color = '#ef4444';
      setLoading(false);
    }
  }

  async function pollTaskStatus() {
    if (!activeTaskId) return;

    try {
      const res = await fetch(`/api/task/${activeTaskId}`);
      if (!res.ok) throw new Error('Task not found');
      const task = await res.json();

      // Update progress & status
      progressPercent.textContent = `${task.progress}%`;
      progressBarFill.style.width = `${task.progress}%`;
      stageBadge.textContent = task.stage || 'In progress...';

      // Update logs
      if (task.logs && task.logs.length > 0) {
        renderLogs(task.logs);
      }

      if (task.status === 'completed') {
        clearInterval(pollInterval);
        setLoading(false);
        renderCompletion(task);
      } else if (task.status === 'failed') {
        clearInterval(pollInterval);
        setLoading(false);
        stageBadge.textContent = `Error: ${task.error || 'Generation failed'}`;
        stageBadge.style.color = '#ef4444';
      }
    } catch (err) {
      console.error('Polling error:', err);
    }
  }

  function renderCompletion(task) {
    stageBadge.textContent = task.dry_run ? 'Storyboard Ready!' : 'Video Rendered!';
    stageBadge.style.color = '#34d399';

    // Show video player if video available
    if (task.video_url) {
      videoElement.src = task.video_url;
      videoViewport.style.display = 'block';
      btnDownload.href = task.video_url;
      videoElement.play().catch(() => {});
    }

    // Render Scene Cards Gallery
    if (task.storyboard && task.storyboard.scenes) {
      scenesGrid.innerHTML = '';
      storyboardGallery.style.display = 'block';

      task.storyboard.scenes.forEach((scene, idx) => {
        const frameData = task.frames ? task.frames.find((f) => f.scene_index === scene.index) : null;
        const card = document.createElement('div');
        card.className = 'scene-card';

        const thumbHtml = frameData
          ? `<img src="${frameData.url}" alt="Scene ${scene.index}" class="scene-thumb" />`
          : `<div class="scene-thumb" style="display:flex;align-items:center;justify-content:center;color:#64748b;font-size:0.8rem;">Frame planned</div>`;

        card.innerHTML = `
          ${thumbHtml}
          <div class="scene-info">
            <div class="scene-badge-row">
              <span class="scene-num">Scene ${scene.index} (${scene.duration}s)</span>
              <span class="motion-tag">${scene.camera_motion}</span>
            </div>
            <p class="scene-desc" title="${scene.description}">${scene.description}</p>
          </div>
        `;
        scenesGrid.appendChild(card);
      });
    }
  }

  function renderLogs(logs) {
    logBox.innerHTML = '';
    logs.forEach((log) => {
      const line = document.createElement('div');
      line.className = 'log-entry';
      line.textContent = `➜ ${log}`;
      logBox.appendChild(line);
    });
    logBox.scrollTop = logBox.scrollHeight;
  }

  function addLog(msg) {
    const line = document.createElement('div');
    line.className = 'log-entry';
    line.textContent = `➜ ${msg}`;
    logBox.appendChild(line);
    logBox.scrollTop = logBox.scrollHeight;
  }

  function resetDisplay() {
    stageEmpty.style.display = 'none';
    progressContainer.style.display = 'block';
    videoViewport.style.display = 'none';
    storyboardGallery.style.display = 'none';
    logBox.innerHTML = '';
    progressBarFill.style.width = '0%';
    progressPercent.textContent = '0%';
    stageBadge.style.color = '#c084fc';
  }

  function setLoading(isLoading) {
    btnGenerate.disabled = isLoading;
    btnDryRun.disabled = isLoading;
    if (isLoading) {
      btnGenerate.innerHTML = `<span>⏳ Generating...</span>`;
    } else {
      const label = currentEngine === 'native_video'
        ? '🎥 Generate AI Video (Agnes Video 2.5)'
        : '✨ Generate Video ($0 Free)';
      btnGenerate.innerHTML = `<span>${label}</span>`;
    }
  }
});
