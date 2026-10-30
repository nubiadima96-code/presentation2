const deck = document.getElementById("deck");
const progressBar = document.getElementById("progressBar");
const slideNum = document.getElementById("slideNum");
const slideTotal = document.getElementById("slideTotal");
const prevBtn = document.getElementById("prevBtn");
const nextBtn = document.getElementById("nextBtn");
const muteBtn = document.getElementById("muteBtn");
const fullBtn = document.getElementById("fullBtn");
const sectionName = document.getElementById("sectionName");

let slidesData = [];
let index = 0;
let locked = false;

const pad = (n) => String(n).padStart(2, "0");

const escapeHtml = (str = "") =>
  String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

const formatCaption = (raw = "") => {
  let c = escapeHtml(raw);
  c = c.replace(/Ю\.\s*В\.\s*Лай/g, "Ю.&nbsp;В.&nbsp;Лай");
  c = c.replace(
    /\s*·\s*We (?:don’t|don't|don(?:&rsquo;)?t) lie/gi,
    '<span class="title-tagline">We&nbsp;don’t&nbsp;lie</span>'
  );
  c = c.replace(/(\d)–(\d)/g, "$1–$2");
  return c;
};

const ILLUSTRATIONS = {
  6: "assets/ill/p006.jpg?v=17",
  9: "assets/ill/p009.jpg?v=17",
  18: "assets/ill/p018.jpg?v=17",
  19: "assets/ill/p019.jpg?v=17",
  23: "assets/ill/p023.jpg?v=17",
  24: "assets/ill/p024.jpg?v=17",
  26: "assets/ill/p026.jpg?v=17",
  34: "assets/ill/p034.jpg?v=17",
  44: "assets/ill/p044.jpg?v=17",
  45: "assets/ill/p045.jpg?v=17",
  46: "assets/ill/p046.jpg?v=17",
  47: "assets/ill/p047.jpg?v=17",
  75: "assets/ill/p075.jpg?v=17",
  77: "assets/ill/p077.jpg?v=17",
  200: "assets/ill/p200.jpg?v=17",
  201: "assets/ill/p201.jpg?v=17",
  202: "assets/ill/p202.jpg?v=17",
  203: "assets/ill/p203.jpg?v=17",
  207: "assets/ill/p207.jpg?v=21",
  208: "assets/ill/p208.jpg?v=17",
  209: "assets/ill/p209.jpg?v=17",
  210: "assets/ill/p210.jpg?v=17",
  216: "assets/ill/p216.jpg?v=17",
};

const ratioOf = (p) => (p.w || 1) / (p.h || 1);

/** Pick layout that never forces a crop */
const pickLayout = (photos) => {
  if (!photos.length) return "empty";
  if (photos.length === 1) return "single";
  if (photos.length === 2) return "duo";
  if (photos.length === 3) return "trio";
  return "stack";
};

/** Fill the right-hand stage, never cropped, never off-canvas */
const sizeStyle = (p, layout) => {
  const tall = ratioOf(p) < 0.85;
  const stage = "(100vw - min(28vw, 420px) - 40px)";
  const fullH = "calc(100svh - 148px)";
  const halfH = "calc((100svh - 168px) / 2)";

  if (layout === "intro-duo") {
    return `max-width:calc(50vw - 40px);max-height:${halfH};`;
  }

  if (layout === "single" || layout === "ill") {
    return `max-width:calc(100vw - min(26vw, 380px) - 28px);max-height:calc(100svh - 120px);`;
  }

  if (layout === "duo") {
    return `max-width:calc(${stage} / 2 - 10px);max-height:${fullH};`;
  }

  if (layout === "trio") {
    return `max-width:calc(${stage} / 3 - 10px);max-height:${fullH};`;
  }

  if (layout === "aside") {
    if (tall) {
      return `max-width:calc(${stage} * 0.44);max-height:${fullH};`;
    }
    return `max-width:calc(${stage} * 0.54);max-height:${halfH};`;
  }

  if (tall) {
    return `max-width:calc(${stage} * 0.72);max-height:${halfH};`;
  }
  return `max-width:calc${stage};max-height:${halfH};`;
};

const picTag = (p, layout) => {
  const style = `${sizeStyle(p, layout)}width:auto;height:auto;object-fit:contain;object-position:center;`;
  const src = p.src.includes("?") ? p.src : `${p.src}?v=35`;
  const solo = layout === "single" || layout === "ill";
  const tall = ratioOf(p) < 0.9;
  const cls = `pic-glass${solo || tall ? " pic-glass--solo" : ""}`;
  return `<span class="${cls}"><span class="pic-glass__in"><img class="pic" src="./${escapeHtml(src)}" alt="" decoding="async" draggable="false" style="${style}" /></span></span>`;
};

const mediaHTML = (s) => {
  if (ILLUSTRATIONS[s.id]) {
    const p = { src: ILLUSTRATIONS[s.id], w: 1600, h: 1200 };
    return `<div class="slide__media slide__media--ill">${picTag(p, "ill")}</div>`;
  }

  if (s.placeholder || s.layout === "placeholder") {
    return `<div class="slide__media slide__media--single">
      <div class="ph">
        <span class="ph__label">Тут буде фото</span>
        <span class="ph__hint">${escapeHtml(s.caption || "")}</span>
      </div>
    </div>`;
  }

  const photos = s.photos || [];
  if (!photos.length) return "";

  const tall = photos.filter((p) => ratioOf(p) < 0.85);
  const rest = photos.filter((p) => ratioOf(p) >= 0.85);

  // 1 tall + 2 landscape: tall on the side, two wides stacked (slide 14)
  if (
    photos.length === 3 &&
    tall.length === 1 &&
    rest.length === 2 &&
    rest.every((p) => ratioOf(p) > 1.25)
  ) {
    return `<div class="slide__media slide__media--aside">
      ${picTag(tall[0], "aside")}
      <div class="slide__col">${rest.map((p) => picTag(p, "aside")).join("")}</div>
    </div>`;
  }

  if (s.id === 1 && photos.length === 2) {
    return `<div class="slide__media slide__media--intro-duo">${photos
      .map((p) => picTag(p, "intro-duo"))
      .join("")}</div>`;
  }

  const layout = pickLayout(photos);
  return `<div class="slide__media slide__media--${layout}">${photos
    .map((p) => picTag(p, layout))
    .join("")}</div>`;
};

const themeOf = (section = "") => {
  const s = section.toLowerCase();
  if (s.includes("дитинств")) return "warm";
  if (
    s.includes("реконструкц") ||
    s.includes("школа") ||
    s.includes("ментор") ||
    s.includes("клінік") ||
    s.includes("радівилів")
  ) {
    return "cold";
  }
  if (s.includes("титул")) return "intro";
  if (s.includes("філософ") || s.includes("контакт")) return "finale";
  return "mid";
};

const buildSlide = (s, i) => {
  const isPlaceholder = !!(s.placeholder || s.layout === "placeholder");
  const isIll = !!ILLUSTRATIONS[s.id];
  const isText = (!(s.photos && s.photos.length) && !isPlaceholder) || isIll;
  const section = escapeHtml(s.section || "DSC");
  const caption = formatCaption(s.caption || `Слайд ${s.id}`);
  const theme = themeOf(s.section || "");

  const isContact = s.id === 217 || (s.section || "") === "Контакт";
  const photos = s.photos || [];
  const isSide = !isContact && !isIll && (photos.length > 0 || isPlaceholder);
  const el = document.createElement("section");
  el.className = `slide slide--${theme}${isText ? " slide--text" : ""}${isContact ? " slide--contact" : ""}${isSide ? " slide--side" : ""}${isIll ? " slide--quote-ill" : ""}${i === 0 ? " slide--intro" : ""}`;
  el.dataset.index = String(i);
  el.dataset.section = s.section || "DSC";
  el.setAttribute("aria-label", `Слайд ${s.id}`);

  const titleBlock = isContact
    ? `<div class="contact">
        <p class="contact__kicker">DSC on AIR</p>
        <a class="contact__phone" href="tel:+380995646545">+380 99 564 65 45</a>
        <p class="contact__hint">Натисни номер або скануй QR</p>
        <a class="contact__qr" href="tel:+380995646545">
          <img src="./assets/qr-phone.svg" alt="QR: подзвонити DSC" />
          <span>Подзвонити</span>
        </a>
      </div>`
    : isText
      ? `<div class="quote"><i class="quote__line" aria-hidden="true"></i><h1 class="slide__title">${caption}</h1></div>`
      : `<h1 class="slide__title">${caption}</h1>`;

  el.innerHTML = `
    <div class="slide__stage">${mediaHTML(s)}</div>
    ${i === 0 ? `<p class="intro-hint" id="introHint">листай →</p>` : ""}
    <div class="slide__copy">
      <div class="slide__copy-inner">
        ${isContact ? "" : `<p class="slide__kicker">${section}</p>`}
        ${titleBlock}
      </div>
    </div>
  `;
  return el;
};

const slidesEls = () => [...deck.querySelectorAll(".slide")];

const loadAround = (i) => {
  [i - 1, i, i + 1, i + 2].forEach((n) => {
    if (n < 0 || n >= slidesData.length) return;
    slidesEls()[n]?.querySelectorAll("img.pic").forEach((img) => {
      img.classList.add("is-ready");
    });
  });
};

const setBackdrop = (section) => {
  const theme = themeOf(section || "");
  document.querySelectorAll(".backdrop__tone").forEach((el) => {
    el.classList.toggle("is-on", el.dataset.theme === theme);
  });
  const backdrop = document.getElementById("backdrop");
  backdrop?.setAttribute("data-active", theme);
  document.body.dataset.theme = theme;
};

const updateUI = () => {
  const total = slidesData.length || 1;
  progressBar.style.width = `${((index + 1) / total) * 100}%`;
  slideNum.textContent = pad(index + 1);
  slideTotal.textContent = String(total);
  const current = slidesData[index];
  if (sectionName) sectionName.textContent = current?.section || "DSC";
  setBackdrop(current?.section);
  prevBtn.disabled = index === 0;
  nextBtn.disabled = index >= total - 1;
  slidesEls().forEach((el, i) => el.classList.toggle("is-active", i === index));
  loadAround(index);
  history.replaceState(null, "", `#${index + 1}`);
};

const easeOutQuint = (t) => 1 - (1 - t) ** 5;

const animateScrollTo = (left, duration = 760) => {
  const from = deck.scrollLeft;
  const dist = left - from;
  if (Math.abs(dist) < 1) return Promise.resolve();
  const start = performance.now();
  return new Promise((resolve) => {
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration);
      deck.scrollLeft = from + dist * easeOutQuint(t);
      if (t < 1) requestAnimationFrame(tick);
      else {
        deck.scrollLeft = left;
        resolve();
      }
    };
    requestAnimationFrame(tick);
  });
};

let audioCtx = null;
let muted = localStorage.getItem("dsc-mute") === "1";

const syncMuteBtn = () => {
  if (!muteBtn) return;
  muteBtn.textContent = muted ? "🔇" : "♪";
  muteBtn.setAttribute("aria-pressed", muted ? "true" : "false");
  muteBtn.title = muted ? "Звук вимкнено" : "Звук перегортання";
};

const playTurn = () => {
  if (muted) return;
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtx.state === "suspended") audioCtx.resume();
    const t = audioCtx.currentTime;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(380, t);
    osc.frequency.exponentialRampToValueAtTime(160, t + 0.14);
    gain.gain.setValueAtTime(0.035, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.16);
    osc.connect(gain).connect(audioCtx.destination);
    osc.start(t);
    osc.stop(t + 0.18);
  } catch (_) {
    /* ignore */
  }
};

const goTo = (i, behavior = "smooth") => {
  hidePicZoom();
  const next = Math.max(0, Math.min(slidesData.length - 1, i));
  const changed = next !== index;
  index = next;
  locked = true;
  const target = slidesEls()[index];
  if (changed && behavior !== "auto") playTurn();
  updateUI();
  const finish = () => {
    const el = slidesEls()[index];
    if (el) deck.scrollLeft = el.offsetLeft;
    locked = false;
  };
  if (!target) {
    finish();
    return;
  }
  if (behavior === "auto") {
    deck.scrollLeft = target.offsetLeft;
    window.setTimeout(finish, 24);
    return;
  }
  animateScrollTo(target.offsetLeft, 760).then(finish);
};

const syncFromScroll = () => {
  if (locked) return;
  const list = slidesEls();
  const mid = deck.scrollLeft + deck.clientWidth / 2;
  let best = 0;
  let bestDist = Infinity;
  list.forEach((s, i) => {
    const center = s.offsetLeft + s.offsetWidth / 2;
    const dist = Math.abs(center - mid);
    if (dist < bestDist) {
      bestDist = dist;
      best = i;
    }
  });
  if (best !== index) {
    index = best;
    updateUI();
  }
};

prevBtn.addEventListener("click", () => goTo(index - 1));
nextBtn.addEventListener("click", () => goTo(index + 1));

let zoomGlass = null;

const hidePicZoom = () => {
  const layer = document.getElementById("picZoom");
  const card = layer?.querySelector(".pic-zoom__card");
  zoomGlass?.classList.remove("is-zooming");
  zoomGlass = null;
  if (card) {
    card.style.transition = "none";
    card.style.transform = "";
  }
  if (layer) {
    layer.hidden = true;
    layer.setAttribute("aria-hidden", "true");
  }
};

const showPicZoom = (glass) => {
  const layer = document.getElementById("picZoom");
  const card = layer?.querySelector(".pic-zoom__card");
  const layerImg = layer?.querySelector("img");
  const img = glass.querySelector("img.pic");
  if (!layer || !card || !layerImg || !img) return;
  if (zoomGlass === glass) return;
  hidePicZoom();
  zoomGlass = glass;
  layerImg.src = img.currentSrc || img.src;
  const from = glass.getBoundingClientRect();
  glass.classList.add("is-zooming");
  layer.hidden = false;
  layer.setAttribute("aria-hidden", "false");
  const play = () => {
    if (zoomGlass !== glass) return;
    card.style.transition = "none";
    card.style.transform = "none";
    const to = card.getBoundingClientRect();
    if (!to.width || !to.height) return;
    const s = Math.min(from.width / to.width, from.height / to.height);
    card.style.transformOrigin = "top left";
    card.style.transform = `translate(${from.left - to.left}px, ${from.top - to.top}px) scale(${s})`;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (zoomGlass !== glass) return;
        card.style.transition = "transform 0.42s cubic-bezier(0.22, 1, 0.36, 1)";
        card.style.transform = "translate(0, 0) scale(1)";
      });
    });
  };
  if (layerImg.complete) play();
  else layerImg.addEventListener("load", play, { once: true });
};

deck.addEventListener("pointerover", (e) => {
  const glass = e.target.closest(".pic-glass");
  if (!glass || glass.closest("#picZoom") || glass.classList.contains("pic-glass--solo")) return;
  if (glass.closest(".slide__media--single, .slide__media--ill")) return;
  showPicZoom(glass);
});
deck.addEventListener("pointerout", (e) => {
  const glass = e.target.closest(".pic-glass");
  if (!glass) return;
  const next = e.relatedTarget;
  if (next && glass.contains(next)) return;
  if (next && deck.contains(next) && next.closest?.(".pic-glass")) return;
  hidePicZoom();
});

const toggleMute = () => {
  muted = !muted;
  localStorage.setItem("dsc-mute", muted ? "1" : "0");
  syncMuteBtn();
};

const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen?.();
  } else {
    document.exitFullscreen?.();
  }
};

muteBtn?.addEventListener("click", toggleMute);
fullBtn?.addEventListener("click", toggleFullscreen);

window.addEventListener(
  "keydown",
  (e) => {
    if (["ArrowRight", "PageDown", " "].includes(e.key)) {
      e.preventDefault();
      goTo(index + 1);
    }
    if (["ArrowLeft", "PageUp"].includes(e.key)) {
      e.preventDefault();
      goTo(index - 1);
    }
    if (e.key === "Home") {
      e.preventDefault();
      goTo(0);
    }
    if (e.key === "End") {
      e.preventDefault();
      goTo(slidesData.length - 1);
    }
    if (e.key === "f" || e.key === "F") {
      e.preventDefault();
      toggleFullscreen();
    }
    if (e.key === "m" || e.key === "M") {
      e.preventDefault();
      toggleMute();
    }
    if (e.key === "Escape" && document.fullscreenElement) {
      document.exitFullscreen?.();
    }
  },
  { passive: false }
);

let tick = false;
deck.addEventListener(
  "scroll",
  () => {
    if (tick) return;
    tick = true;
    requestAnimationFrame(() => {
      syncFromScroll();
      tick = false;
    });
  },
  { passive: true }
);

let wheelAcc = 0;
let wheelReset = 0;
window.addEventListener(
  "wheel",
  (e) => {
    e.preventDefault();
    if (locked) return;
    const raw = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
    const scaled =
      e.deltaMode === 1 ? raw * 16 : e.deltaMode === 2 ? raw * 800 : raw;
    wheelAcc += scaled;
    window.clearTimeout(wheelReset);
    wheelReset = window.setTimeout(() => {
      wheelAcc = 0;
    }, 180);
    if (Math.abs(wheelAcc) < 24) return;
    const dir = wheelAcc > 0 ? 1 : -1;
    wheelAcc = 0;
    goTo(index + dir);
  },
  { passive: false }
);

deck.addEventListener("click", (e) => {
  if (e.target.closest("a, button, .navbtn, .pic-glass, input, textarea")) return;
  goTo(index + 1);
});

let touchX = 0;
deck.addEventListener(
  "touchstart",
  (e) => {
    touchX = e.changedTouches[0]?.clientX || 0;
  },
  { passive: true }
);
deck.addEventListener(
  "touchmove",
  (e) => {
    e.preventDefault();
  },
  { passive: false }
);
deck.addEventListener(
  "touchend",
  (e) => {
    const x = e.changedTouches[0]?.clientX || 0;
    const dx = x - touchX;
    if (Math.abs(dx) < 48 || locked) return;
    goTo(index + (dx < 0 ? 1 : -1));
  },
  { passive: true }
);

const boot = async () => {
  const res = await fetch("./assets/slides.json?v=35");
  const data = await res.json();
  slidesData = data.slides || [];

  slidesData.forEach((s) => {
    const seen = new Set();
    s.photos = (s.photos || []).filter((p) => {
      if (!p?.src || seen.has(p.src)) return false;
      seen.add(p.src);
      return true;
    });
  });

  const frag = document.createDocumentFragment();
  slidesData.forEach((s, i) => frag.append(buildSlide(s, i)));
  deck.append(frag);

  const hash = Number(location.hash.replace("#", ""));
  const start = Number.isFinite(hash) && hash >= 1 && hash <= slidesData.length ? hash - 1 : 0;
  goTo(start, "auto");
  deck.focus({ preventScroll: true });

  syncMuteBtn();

  const first = slidesEls()[0];
  if (first) {
    const skipMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (start !== 0 || skipMotion) {
      first.classList.add("is-intro-done");
    } else {
      window.setTimeout(() => {
        first.classList.add("is-intro-done");
        const hint = document.getElementById("introHint");
        if (hint) {
          hint.classList.add("is-on");
          window.setTimeout(() => hint.classList.remove("is-on"), 2000);
        }
      }, 2400);
    }
  }
};

boot().catch((err) => console.error(err));
