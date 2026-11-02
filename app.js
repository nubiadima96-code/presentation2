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
    ' <span class="title-tagline">We&nbsp;don’t&nbsp;lie</span>'
  );
  c = c.replace(/(\d)–(\d)/g, "$1–$2");
  return c;
};

/** Multiline text-slide body → lead or points list */
const formatTextBody = (raw = "") => {
  const lines = String(raw)
    .split(/\n+/)
    .map((l) => l.trim())
    .filter(Boolean);
  if (!lines.length) return "";
  if (lines.length === 1) {
    return `<p class="slide__lead">${formatCaption(lines[0])}</p>`;
  }
  const items = lines
    .map((line, i) => {
      const cls =
        i === 0
          ? "slide__point slide__point--lead"
          : i === lines.length - 1
            ? "slide__point slide__point--punch"
            : "slide__point";
      // Name — role → split visually
      const m = line.match(/^(.+?)\s+[—–-]\s+(.+)$/);
      if (m) {
        return `<li class="${cls}"><span class="slide__point-name">${formatCaption(
          m[1]
        )}</span><span class="slide__point-role">${formatCaption(
          m[2]
        )}</span></li>`;
      }
      return `<li class="${cls}">${formatCaption(line)}</li>`;
    })
    .join("");
  return `<ul class="slide__points">${items}</ul>`;
};

const ILLUSTRATIONS = {};

const ratioOf = (p) => (p.w || 1) / (p.h || 1);

/** Pick layout that never forces a crop */
const pickLayout = (photos) => {
  if (!photos.length) return "empty";
  if (photos.length === 1) return "single";
  if (photos.length === 2) return "duo";
  if (photos.length === 3) return "trio";
  if (photos.length === 4) return "quad";
  return "stack";
};

/** Size for wide stage (full-bleed / title-above). Intro uses its own layout. */
const sizeStyle = (p, layout) => {
  const tall = ratioOf(p) < 0.85;
  // Leave room for equal glass padding (8px × 2) so the frame never stretches
  const pad = 16;
  const stage = `(100vw - ${56 + pad}px)`;
  const fullH = `calc(100svh - ${120 + pad}px)`;
  const halfH = `calc((100svh - ${150 + pad}px) / 2)`;

  if (layout === "intro-duo") {
    return `max-width:calc(50vw - ${36 + pad / 2}px);max-height:${halfH};`;
  }

  if (layout === "single" || layout === "ill") {
    // vw/svh only — never % max, or fit-content glass inflates unevenly
    if (tall) {
      return `max-width:min(56vw,calc((100svh - ${140 + pad}px) * 0.72));max-height:calc(100svh - ${140 + pad}px);`;
    }
    return `max-width:calc(100vw - ${96 + pad}px);max-height:calc(100svh - ${280 + pad}px);`;
  }

  if (layout === "duo") {
    return `max-width:calc(${stage} / 2 - 8px);max-height:${fullH};`;
  }

  if (layout === "duo-diagonal") {
    return `max-width:min(54vw,${880 - pad}px);max-height:min(34svh,${380 - pad}px);`;
  }

  if (layout === "duo-mixed") {
    const div = Number(p._duoDiv) > 0 ? p._duoDiv : 2.1;
    return `height:min(100cqh,calc((100cqw - ${36 + pad}px) / ${div}));width:auto;max-height:min(100cqh,calc((100cqw - ${36 + pad}px) / ${div}));min-width:0;`;
  }

  if (layout === "trio") {
    return `max-width:calc(${stage} / 3 - 8px);max-height:${fullH};`;
  }

  if (layout === "quad") {
    return `width:100%;height:100%;max-width:none;max-height:none;object-fit:contain;`;
  }

  if (layout === "aside") {
    if (tall) {
      return `max-width:min(40vw,${500 - pad}px);max-height:calc(100svh - ${170 + pad}px);`;
    }
    return `max-width:min(calc(52vw - ${16 + pad}px),${664 - pad}px);max-height:calc((100svh - ${180 + pad}px) / 2 - ${pad}px);`;
  }

  if (tall) {
    return `max-width:calc(${stage} * 0.78);max-height:${halfH};`;
  }
  return `max-width:calc(${stage});max-height:${halfH};`;
};

const picTag = (p, layout) => {
  const sized = sizeStyle(p, layout);
  const style = `${sized}width:auto;height:auto;object-fit:contain;object-position:center;`;
  const src = p.src.includes("?") ? p.src : `${p.src}?v=156`;
  // Never hover-zoom — photos should already read on stage
  const glass = `<span class="pic-glass pic-glass--solo"><span class="pic-glass__in"><img class="pic" src="./${escapeHtml(src)}" alt="" decoding="async" draggable="false" style="${style}" /></span></span>`;
  const cap = String(p.caption || "").trim();
  if (!cap) return glass;
  const side = String(p.capSide || "top").toLowerCase();
  const sideCls =
    side === "left" || side === "right" ? ` pic-stack--${side}` : "";
  return `<span class="pic-stack${sideCls}"><span class="pic-stack__cap">${escapeHtml(cap)}</span>${glass}</span>`;
};

const hasSlideCopy = (s) =>
  !!(String(s.caption || "").trim() || String(s.subtitle || "").trim());

const mediaHTML = (s) => {
  const videos = s.videos || [];
  if (videos.length) {
    const tags = videos
      .map((v) => {
        const src = v.src.includes("?") ? v.src : `${v.src}?v=106`;
        const wide = (v.w || 16) >= (v.h || 9);
        const cls = wide ? "vid vid--wide" : "vid vid--tall";
        const clipStart = Number(v.start);
        const clipEnd = Number(v.end);
        const clip =
          (Number.isFinite(clipStart) ? ` data-clip-start="${clipStart}"` : "") +
          (Number.isFinite(clipEnd) && clipEnd > 0 ? ` data-clip-end="${clipEnd}"` : "");
        if (v.kind === "audio") {
          return `<audio class="aud" controls preload="metadata"${clip} src="./${escapeHtml(src)}"></audio>`;
        }
        const poster = v.poster
          ? ` poster="./${escapeHtml(v.poster.includes("?") ? v.poster : `${v.poster}?v=112`)}"`
          : "";
        return `<video class="${cls}" controls playsinline preload="metadata"${poster}${clip} src="./${escapeHtml(src)}"></video>`;
      })
      .join("");
    return `<div class="slide__media slide__media--video">${tags}</div>`;
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

  if (s.id === 43 && photos.length >= 3) {
    const docs = photos.slice(0, 2);
    const lead = photos[2];
    const lect = photos.slice(3);
    return `<div class="slide__media slide__media--roles">
      <div class="roles__col"><span class="pic-stack__cap">ЛІКАР</span>${docs
        .map((p) => picTag({ ...p, caption: "" }, "single"))
        .join("")}</div>
      ${picTag(lead, "single")}
      <div class="roles__col"><span class="pic-stack__cap">ЛЕКТОР</span>${lect
        .map((p) => picTag({ ...p, caption: "" }, "single"))
        .join("")}</div>
    </div>`;
  }

  const tall = photos.filter((p) => ratioOf(p) < 0.85);
  const rest = photos.filter((p) => ratioOf(p) >= 0.85);

  // 1 tall + 2 landscape
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

  // Diagonal: one top-left, one bottom-right, captions toward center
  if (s.layout === "duo-diagonal" && photos.length === 2) {
    return `<div class="slide__media slide__media--duo-diagonal">${photos
      .map((p, i) =>
        picTag(
          {
            ...p,
            capSide: p.capSide || (i === 0 ? "right" : "left"),
          },
          "duo-diagonal"
        )
      )
      .join("")}</div>`;
  }

  // tall + wide — equal height; size from real combined aspect ratios
  if (photos.length === 2 && tall.length === 1 && rest.length === 1) {
    // Must fit stage width: height ≈ width / (arTall + arWide + gap)
    const duoDiv = Math.max(
      1.55,
      ratioOf(tall[0]) + ratioOf(rest[0]) + 0.14
    );
    return `<div class="slide__media slide__media--duo-mixed" style="--duo-div:${duoDiv.toFixed(3)}">${photos
      .map((p) => picTag({ ...p, _duoDiv: duoDiv }, "duo-mixed"))
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
  const photos = s.photos || [];
  const videos = s.videos || [];
  const hasMedia = photos.length > 0 || videos.length > 0;
  const isIll = false;
  const isText = !hasMedia && !isPlaceholder;
  const section = escapeHtml(s.section || "DSC");
  const caption = formatCaption(s.caption || "");
  const subtitleRaw = s.subtitle || "";
  const subtitle = subtitleRaw
    .split("\n")
    .map((line) => formatCaption(line.trim()))
    .filter(Boolean)
    .join("<br>");
  const theme = themeOf(s.section || "");

  const isContact =
    (s.section || "") === "Контакт" ||
    /\+?380/.test(s.caption || "") ||
    /\+?380/.test(s.text || "");
  const isAudioOnly =
    !photos.length &&
    videos.length > 0 &&
    videos.every((v) => v.kind === "audio");
  const isManifesto =
    s.id === 201 || /^Який я лікар$/i.test(String(s.caption || "").trim());
  const isPlace = s.id === 30;
  const isRoster = s.id === 46;
  const isQuotePhoto = [31, 192, 193, 194, 195].includes(s.id);
  const isRoles = s.id === 43;
  const isTextSlide = (isText || isAudioOnly || isManifesto || isRoster) && !isContact && !isQuotePhoto;
  const hasCopy = hasSlideCopy(s);
  const isIntro = i === 0;
  // Tall solo + caption → text left (empty side of portrait); intro too.
  // Wider / multi photo + caption → title above.
  // Place card (Радивилів) → text left + wide photo right, never stacked/cropped.
  const isTallSolo =
    photos.length === 1 &&
    !videos.length &&
    ratioOf(photos[0]) < 0.85;
  const isSide =
    !isContact &&
    !isTextSlide &&
    hasMedia &&
    hasCopy &&
    (isIntro || isTallSolo || isPlace || isQuotePhoto);
  const isTop = !isContact && !isTextSlide && !isPlace && hasMedia && hasCopy && !isSide;
  const isFull = !isContact && !isTextSlide && hasMedia && !hasCopy;
  // Cards slide: pull photo back a bit so it doesn't feel glued to the lens
  const isMediaPullback = s.id === 4;
  const isEvenTrio = s.id === 199;
  const isRadyDuo = s.id === 189;
  const isClinicQuad = s.id === 41;
  const el = document.createElement("section");
  el.className = `slide slide--${theme}${isTextSlide ? " slide--text" : ""}${isManifesto ? " slide--manifesto" : ""}${isRoster ? " slide--roster" : ""}${isPlace ? " slide--place" : ""}${isQuotePhoto ? " slide--quote-photo" : ""}${isRoles ? " slide--roles" : ""}${isContact ? " slide--contact" : ""}${isSide ? " slide--side" : ""}${isTop ? " slide--top" : ""}${isFull ? " slide--full" : ""}${isIll ? " slide--quote-ill" : ""}${isIntro ? " slide--intro" : ""}${isMediaPullback ? " slide--media-pullback" : ""}${isEvenTrio ? " slide--even-trio" : ""}${isRadyDuo ? " slide--rady-duo" : ""}${isClinicQuad ? " slide--clinic-quad" : ""}`;
  el.dataset.index = String(i);
  el.dataset.section = s.section || "DSC";
  el.setAttribute("aria-label", `Слайд ${s.id}`);

  const manifestoBody = subtitleRaw
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const manifestoTag = manifestoBody.find((line) => /don.?t\s+lie/i.test(line));
  const manifestoLines = manifestoBody.filter((line) => line !== manifestoTag);

  const placeLines = manifestoBody;
  const placeKicker = placeLines.find((line) => /населення/i.test(line)) || "";
  const placeStat = placeLines.find((line) => /^\d[\d\s]*$/.test(line)) || "";
  const placeNote =
    placeLines.find((line) => /повернення|додому/i.test(line)) || "";
  const placeLead =
    placeLines.find(
      (line) =>
        line !== placeKicker && line !== placeStat && line !== placeNote
    ) || "";

  const titleBlock = isContact
    ? `<div class="contact">
        <p class="contact__kicker">DSC on AIR</p>
        <a class="contact__phone" href="tel:+380995646545">+380 99 564 65 45</a>
        <a class="contact__qr" href="tel:+380995646545">
          <img src="./assets/qr-phone.svg" alt="QR: подзвонити DSC" />
          <span>Подзвонити</span>
        </a>
      </div>`
    : isPlace
      ? `<div class="place">
          <h1 class="slide__title">${caption || "Радивилів"}</h1>
          ${
            placeKicker
              ? `<p class="place__kicker">${formatCaption(placeKicker)}</p>`
              : ""
          }
          ${
            placeStat
              ? `<p class="place__stat">${formatCaption(placeStat)}</p>`
              : ""
          }
          ${
            placeLead
              ? `<p class="place__lead">${formatCaption(placeLead)}</p>`
              : ""
          }
          ${
            placeNote
              ? `<p class="place__note">${formatCaption(placeNote)}</p>`
              : ""
          }
        </div>`
    : isManifesto
      ? `<div class="manifesto">
          <h1 class="slide__title">${caption || "Який я лікар"}</h1>
          ${
            manifestoLines.length
              ? `<p class="manifesto__body">${manifestoLines
                  .map((line) => formatCaption(line))
                  .join("<br>")}</p>`
              : ""
          }
          ${
            manifestoTag
              ? `<p class="manifesto__tag">${formatCaption(manifestoTag)}</p>`
              : ""
          }
        </div>`
    : isTextSlide
      ? `<div class="quote${
          subtitleRaw.trim() ? " quote--rich" : ""
        }"><i class="quote__line" aria-hidden="true"></i><div class="quote__stack">${
          caption ? `<h1 class="slide__title">${caption}</h1>` : ""
        }${
          subtitleRaw.trim() ? formatTextBody(subtitleRaw) : ""
        }</div></div>`
      : caption
        ? `<h1 class="slide__title">${caption}</h1>${
            subtitle ? `<p class="slide__sub">${subtitle}</p>` : ""
          }`
        : "";

  el.innerHTML = `
    <div class="slide__stage">${mediaHTML(s)}</div>
    ${i === 0 ? `<p class="intro-hint" id="introHint">листай →</p>` : ""}
    <div class="slide__copy">
      <div class="slide__copy-inner">
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

const pauseMedia = () => {
  deck.querySelectorAll("video, audio").forEach((el) => {
    try {
      el.pause();
    } catch (_) {
      /* ignore */
    }
  });
};

const playActiveMedia = () => {
  const el = slidesEls()[index];
  if (!el) return;
  el.querySelectorAll("video, audio").forEach((media) => {
    try {
      const start = Number(media.dataset.clipStart || 0);
      if (!media._dscClipBound) {
        media._dscClipBound = true;
        media.addEventListener("timeupdate", () => {
          const clipEnd = Number(media.dataset.clipEnd || 0);
          if (!(clipEnd > 0)) return;
          const dur = media.duration;
          if (!Number.isFinite(dur) || dur <= clipEnd + 0.3) return;
          if (media.currentTime >= clipEnd - 0.04) {
            try {
              media.pause();
              media.currentTime = clipEnd;
            } catch (_) {
              /* ignore */
            }
          }
        });
      }
      media.currentTime = Number.isFinite(start) && start > 0.05 ? start : 0.01;
      const p = media.play();
      if (p && typeof p.catch === "function") p.catch(() => {});
    } catch (_) {
      /* ignore autoplay blocks */
    }
  });
};

const goTo = (i, behavior = "smooth") => {
  hidePicZoom();
  pauseMedia();
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
    playActiveMedia();
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
  const res = await fetch("./assets/slides.json?v=173");
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
