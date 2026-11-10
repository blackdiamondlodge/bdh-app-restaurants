(function () {
  "use strict";
  const D = JSON.parse(document.getElementById("rs-data").textContent);
  const C = JSON.parse(document.getElementById("rs-config").textContent);
  const $ = id => document.getElementById(id);
  const ov = $("rs-ov"), sov = $("rs-sov"), dlg = $("rs-dlg");
  const STORE = "rs-shortlist", MAX = 8;
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const bg = (d, i = 0) => d.photos && d.photos[i] ? `background-image:url('${d.photos[i].url}')` : "";

  function stars(r, n) {
    if (r == null) return '<span class="nr">No rating yet</span>';
    const full = Math.floor(r), half = r - full >= .5 ? 1 : 0;
    return '<span class="stars">' + '<i class="fas fa-star"></i>'.repeat(full) + (half ? '<i class="fas fa-star-half-stroke"></i>' : "") +
      '<i class="far fa-star"></i>'.repeat(5 - full - half) + `</span> <b>${r.toFixed(1)}</b>` +
      (n ? ` <span class="cnt">(${n.toLocaleString()})</span>` : "");
  }
  document.querySelectorAll(".rc .rt").forEach(el => {
    const d = D[el.closest(".rc").dataset.slug];
    el.innerHTML = stars(d.rating, d.count);
  });

  // ── Shortlist: kept in localStorage for the whole stay ──
  // Cleared only when a different stay begins. A list made with no stay showing
  // (early arrival, or HA unreachable) is adopted by the next stay instead.
  const stay = document.querySelector(".rs-wrap").dataset.stay || "";
  let list = [], owner = stay;
  try {
    const saved = JSON.parse(localStorage.getItem(STORE) || "null");
    if (saved && Array.isArray(saved.list)) {
      const prev = saved.stay || "";
      if (!stay || !prev || prev === stay) {
        list = saved.list.filter(s => D[s]);
        owner = stay || prev;
      }
    }
  } catch (e) { /* ignore */ }
  const persist = () => { try { localStorage.setItem(STORE, JSON.stringify({list, stay: owner})); } catch (e) { /* ignore */ } };
  persist();

  function sync() {
    document.querySelectorAll(".hb").forEach(b => {
      const on = list.includes(b.dataset.h);
      b.classList.toggle("on", on);
      b.innerHTML = `<i class="${on ? "fas" : "far"} fa-heart"></i>`;
    });
    $("rs-send").disabled = !list.length;
    $("rs-list").innerHTML = list.length ? list.map(s => {
      const d = D[s], ph = d.photos.length;
      return `<div class="si" data-slug="${s}" style="--c1:${d.c1};--c2:${d.c2}"><div class="ic${ph ? " ph" : ""}" style="${bg(d)}">${ph ? "" : `<i class="fas ${d.icon}"></i>`}</div>` +
        `<div class="t"><div class="n">${esc(d.name)}</div><div class="s">${d.rating ? "★ " + d.rating.toFixed(1) + " · " : ""}${esc(d.st[1])}</div></div>` +
        `<button type="button" class="x" data-x="${s}" aria-label="Remove"><i class="fas fa-xmark"></i></button></div>`;
    }).join("") : '<div class="empty"><i class="far fa-heart"></i>Nothing saved yet.<br>Tap the heart on a restaurant to add it.</div>';
    const cur = dlg.dataset.slug, sb = dlg.querySelector(".save");
    if (sb && cur) {
      const on = list.includes(cur);
      sb.classList.toggle("saved", on);
      sb.innerHTML = on ? '<i class="fas fa-heart"></i> On your shortlist' : '<i class="far fa-heart"></i> Add to shortlist';
    }
    persist();
  }
  function toggle(s) { list = list.includes(s) ? list.filter(x => x !== s) : [s, ...list].slice(0, MAX); sync(); }

  // ── Details ──
  // Same look as the Wi-Fi app's QR: round dots, square finder patterns (rounded
  // ones break some decoders) and the lodge monogram over a cleared centre.
  const QR_INK = "#0b1622", QR_BORDER = 2;  // the .qr box's white padding adds to the quiet zone
  const MONOGRAM = '<polygon points="50,3 97,50 50,97 3,50" fill="#0b1622"/><polygon points="50,11 89,50 50,89 11,50" fill="none" stroke="#fff" stroke-opacity=".45" stroke-width="1.5"/><path fill="#fff" d="M28 56.67V55.59H29.71V44.41H28V43.33H35.9Q38.34 43.33 39.57 44.15Q40.79 44.98 40.79 46.63Q40.79 47.82 39.95 48.51Q39.1 49.21 37.44 49.39Q39.45 49.58 40.52 50.46Q41.59 51.34 41.59 52.81Q41.59 54.79 40.1 55.73Q38.6 56.67 35.41 56.67ZM33.14 48.9H34.32Q35.85 48.9 36.59 48.34Q37.33 47.78 37.33 46.63Q37.33 45.47 36.62 44.94Q35.9 44.41 34.32 44.41H33.14ZM33.14 55.59H34.42Q36.13 55.59 36.95 54.91Q37.77 54.23 37.77 52.81Q37.77 51.38 36.94 50.67Q36.11 49.97 34.42 49.97H33.14ZM49.14 55.59H50.38Q52.47 55.59 53.44 54.25Q54.41 52.91 54.41 49.99Q54.41 47.08 53.45 45.75Q52.48 44.41 50.38 44.41H49.14ZM44 56.67V55.59H45.7V44.41H44V43.33H50.84Q54.43 43.33 56.33 45.05Q58.24 46.76 58.24 49.99Q58.24 53.23 56.33 54.95Q54.42 56.67 50.84 56.67ZM60.4 56.67V55.59H62.1V44.41H60.4V43.33H67.26V44.41H65.54V55.44H70.79V53.34H72V56.67Z"/>';
  function qrSvg(text) {
    if (typeof qrcode === "undefined") return "";
    // Level H survives the logo best; long shortlist links drop to L with a smaller
    // logo so the code isn't too dense to scan off the screen.
    const long = text.length > 200, q = qrcode(0, long ? "L" : "H");
    q.addData(text); q.make();
    const m = q.getModuleCount(), n = m + 2 * QR_BORDER, B = QR_BORDER;
    const fins = [[0, 0], [0, m - 7], [m - 7, 0]];
    const hole = Math.round(m * (long ? .14 : .24)) | 1, h0 = (m - hole) / 2, h1 = h0 + hole;
    const skip = (r, c) => fins.some(([fr, fc]) => r >= fr && r < fr + 7 && c >= fc && c < fc + 7) ||
      (r >= h0 - 1 && r <= h1 && c >= h0 - 1 && c <= h1);
    let dots = "";
    for (let r = 0; r < m; r++) for (let c = 0; c < m; c++)
      if (q.isDark(r, c) && !skip(r, c)) dots += `<circle cx="${c + B + .5}" cy="${r + B + .5}" r=".46"/>`;
    const eyes = fins.map(([r, c]) => `<rect x="${c + B + .5}" y="${r + B + .5}" width="6" height="6" fill="none" stroke="${QR_INK}" stroke-width="1"/>` +
      `<rect x="${c + B + 2}" y="${r + B + 2}" width="3" height="3"/>`).join("");
    const pad = .6, size = hole + 2 - 2 * pad, o = h0 - 1 + pad + B;
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${n} ${n}" shape-rendering="geometricPrecision">` +
      `<rect width="${n}" height="${n}" fill="#fff"/><g fill="${QR_INK}">${dots}${eyes}</g>` +
      `<svg x="${o}" y="${o}" width="${size}" height="${size}" viewBox="0 0 100 100">${MONOGRAM}</svg></svg>`;
  }
  function ownerPanel(d) {
    return `<div class="owner"><h4><i class="fas fa-user-pen"></i> Owner — only visible when signed in</h4>
      <div class="tg${d.pick ? " on" : ""}" data-k="pick"><span class="sw"></span>Mark as <b>&nbsp;Owner's pick</b></div>
      <label class="nl">Owner's note <small>(optional — shown to guests, with or without a pick)</small></label>
      <textarea maxlength="500" placeholder="e.g. 'Get the breakfast burrito' or 'Cash only'">${esc(d.note)}</textarea>
      <div class="tg${d.hidden ? " on" : ""}" data-k="hidden" style="margin-top:10px"><span class="sw"></span>Hide from guests</div>
      <button type="button" class="sv">Save</button><span class="err"></span></div>`;
  }
  function open_(s) {
    const d = D[s], ph = d.photos.length;
    dlg.dataset.slug = s;
    dlg.style.cssText = `--c1:${d.c1};--c2:${d.c2}`;
    const note = d.pick || d.note ? `<div class="note${d.pick ? "" : " plain"}"><b><i class="fas ${d.pick ? "fa-star" : "fa-comment"}"></i> ${d.pick ? "Owner's pick" : "Owner's note"}</b>${esc(d.note)}</div>` : "";
    dlg.innerHTML = `<div class="dh" style="${bg(d)}">${ph ? "" : `<i class="fas ${d.icon} big"></i>`}<div><h3>${esc(d.name)}</h3>` +
      `<div class="m">${d.label}${d.price ? " · " + d.price : ""} · ${stars(d.rating, null)}${d.count ? " (" + d.count.toLocaleString() + " reviews)" : ""}</div></div>` +
      `${ph && d.photos[0].by ? `<div class="credit">Photo: ${esc(d.photos[0].by)}</div>` : ""}<button type="button" class="dclose" aria-label="Close"><i class="fas fa-xmark"></i></button></div>
      <div class="dl">${note}${d.summary ? `<p>${esc(d.summary)}</p>` : ""}
        <div class="facts"><span class="ss ${d.st[0]}"><span class="dot"></span>${esc(d.st[1])}</span>${d.dist ? `<span><i class="fas fa-car"></i>${d.dist}</span>` : ""}${d.phone ? `<span><i class="fas fa-phone"></i>${esc(d.phone)}</span>` : ""}</div>
        ${d.amen.length ? `<div class="amen">${d.amen.map(a => `<span><i class="fas ${a[0]}"></i>${a[1]}</span>`).join("")}</div>` : ""}
        <div class="hrs">${d.hours.map(h => `<div class="${h.startsWith(C.today) ? "today" : ""}">${esc(h)}</div>`).join("")}</div>
        ${ph > 1 ? `<div class="gal">${d.photos.slice(1).map((p, i) => `<div style="${bg(d, i + 1)}"></div>`).join("")}</div>` : ""}
        ${C.owner ? ownerPanel(d) : ""}</div>
      <div class="dr">${d.loc ? '<button type="button" class="minw" aria-label="Expand map"><div class="mini" id="rs-mini"></div><span class="mxh"><i class="fas fa-expand"></i> Expand</span></button>' : ""}<div class="qr">${qrSvg(d.maps.replace(/&g_mp=[^&]*/, ""))}</div>
        <div class="cap">Scan for directions, menu &amp; reviews on your phone</div><button type="button" class="save"></button></div>`;
    sync();
    ov.classList.add("show");
    if (d.loc) setTimeout(() => miniMap(d), 30);
  }
  function closeDlg() { shrinkMap(); ov.classList.remove("show"); delete dlg.dataset.slug; }

  dlg.addEventListener("click", e => {
    if (e.target.closest(".dclose")) return closeDlg();
    if (e.target.closest(".mxc")) return shrinkMap();
    if (e.target.closest(".minw")) return expandMap(D[dlg.dataset.slug]);
    if (e.target.closest(".save")) return toggle(dlg.dataset.slug);
    const tg = e.target.closest(".tg");
    if (tg) return tg.classList.toggle("on");
    if (e.target.closest(".sv")) saveOwner(dlg.dataset.slug);
  });

  async function saveOwner(s) {
    const o = dlg.querySelector(".owner"), err = o.querySelector(".err");
    const body = {
      pick: o.querySelector('[data-k="pick"]').classList.contains("on"),
      hidden: o.querySelector('[data-k="hidden"]').classList.contains("on"),
      note: o.querySelector("textarea").value,
    };
    err.textContent = "";
    try {
      const r = await fetch(C.ownerUrl.replace("__slug__", s), {
        method: "POST", headers: {"Content-Type": "application/json", "X-CSRFToken": window.RS_CSRF},
        body: JSON.stringify(body), credentials: "same-origin",
      });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || "Couldn't save");
      const d = await r.json();
      D[s] = d;
      const card = document.querySelector(`.rc[data-slug="${s}"]`), art = card.querySelector(".art");
      card.classList.toggle("hidden", d.hidden);
      card.dataset.tags = d.tags;
      const pick = art.querySelector(".pick");
      if (pick) pick.remove();
      if (d.pick) art.insertAdjacentHTML("afterbegin", '<span class="pick"><i class="fas fa-star"></i> Owner\'s pick</span>');
      if (bigM[s]) bigM[s].setIcon(rIcon(d));
      applyF();
      open_(s);
    } catch (e) {
      err.textContent = e.message;
    }
  }

  ov.addEventListener("click", e => { if (e.target === ov) closeDlg(); });
  sov.addEventListener("click", () => sov.classList.remove("show"));
  $("rs-grid").addEventListener("click", e => {
    const h = e.target.closest(".hb");
    if (h) { e.stopPropagation(); return toggle(h.dataset.h); }
    const c = e.target.closest(".rc");
    if (c) open_(c.dataset.slug);
  });
  $("rs-list").addEventListener("click", e => {
    const x = e.target.closest("[data-x]");
    if (x) return toggle(x.dataset.x);
    const i = e.target.closest(".si");
    if (i) open_(i.dataset.slug);
  });
  $("rs-clear").addEventListener("click", () => { list = []; sync(); });
  // The shortlist page resolves short codes via its published places.json. Use a
  // code only when that file lists the same place; anything newer or changed
  // falls back to the self-contained Name~PlaceID form, so links never break.
  const published = {};
  fetch(C.shortlistUrl + "places.json", {cache: "no-cache"}).then(r => r.ok ? r.json() : {})
    .then(j => Object.assign(published, j.places || {})).catch(() => {});
  const linkItem = d => {
    const p = published[d.code];
    return p && p.n === d.name && p.p === d.pid ? d.code : encodeURIComponent(d.name) + "~" + d.pid;
  };
  $("rs-send").addEventListener("click", () => {
    if (!list.length || typeof qrcode === "undefined") return;
    const url = C.shortlistUrl + "#" + list.map(s => linkItem(D[s])).join(",");  // phone cameras percent-encode "|"
    $("rs-sqr").innerHTML = qrSvg(url);
    sov.classList.add("show");
  });

  // ── Filters: chips within a group combine with the group's and/or ──
  function applyF() {
    const sel = [];
    document.querySelectorAll(".fg").forEach(g => {
      const on = [...g.querySelectorAll(".chip.on")].map(c => c.dataset.f);
      if (on.length) sel.push({m: g.dataset.m, on});
    });
    let n = 0;
    const cards = document.querySelectorAll(".rc");
    cards.forEach(r => {
      const t = r.dataset.tags.split(" ");
      const ok = sel.every(g => g.m === "or" ? g.on.some(f => t.includes(f)) : g.on.every(f => t.includes(f)));
      r.classList.toggle("hide", !ok);
      n += ok;
    });
    $("rs-count").textContent = sel.length ? `${n} of ${cards.length} match` : C.summary;
    $("rs-reset").style.visibility = sel.length ? "visible" : "hidden";
    $("rs-empty").style.display = n ? "none" : "block";
    syncMap();
  }
  document.querySelectorAll(".chip").forEach(c => c.addEventListener("click", () => { c.classList.toggle("on"); applyF(); }));
  $("rs-reset").addEventListener("click", () => { document.querySelectorAll(".chip.on").forEach(c => c.classList.remove("on")); applyF(); });

  // ── Maps ──
  const LODGE = C.lodge, TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  const hasL = () => typeof L !== "undefined";
  const lodgeIcon = () => L.divIcon({className: "", html: '<div class="lpin"><span>BDL</span></div>', iconSize: [34, 34], iconAnchor: [17, 17]});
  const rIcon = d => L.divIcon({className: "", iconSize: [44, 44], iconAnchor: [22, 22],
    html: `<div class="rpin${d.pick ? " pk" : ""}${d.st[0] === "season" ? " off" : ""}" style="--c1:${d.c1};--c2:${d.c2};${bg(d)}">${d.photos.length ? "" : `<i class="fas ${d.icon}"></i>`}</div><div class="rlab">${esc(d.name)}</div>`});
  let mini, big, clus, mx;
  const bigM = {};

  function miniMap(d) {
    if (!hasL() || !$("rs-mini")) return;
    if (mini) mini.remove();
    mini = L.map("rs-mini", {zoomControl: false, attributionControl: false, dragging: false, touchZoom: false,
      scrollWheelZoom: false, doubleClickZoom: false, boxZoom: false, keyboard: false});
    L.tileLayer(TILES).addTo(mini);
    L.marker(LODGE, {icon: lodgeIcon()}).addTo(mini);
    L.marker(d.loc, {icon: L.divIcon({className: "", html: `<div class="rpin sm" style="--c1:${d.c1};--c2:${d.c2}"></div>`, iconSize: [22, 22], iconAnchor: [11, 11]})}).addTo(mini);
    L.polyline([LODGE, d.loc], {color: "#7cc4ff", weight: 2, dashArray: "4 6"}).addTo(mini);
    mini.fitBounds([LODGE, d.loc], {padding: [28, 28]});
  }
  function recentreCtl(fn) {
    const Ctl = L.Control.extend({
      options: {position: "bottomright"},
      onAdd() {
        const bar = L.DomUtil.create("div", "leaflet-bar");
        const a = L.DomUtil.create("a", "recentre", bar);
        a.href = "#"; a.title = "Recentre"; a.setAttribute("role", "button");
        a.innerHTML = '<i class="fas fa-crosshairs"></i>';
        L.DomEvent.disableClickPropagation(bar);
        L.DomEvent.on(a, "click", e => { L.DomEvent.preventDefault(e); fn(); });
        return bar;
      },
    });
    return new Ctl();
  }
  // Tapping the detail mini-map expands it over the whole dialog for zoom/pan.
  function expandMap(d) {
    if (!hasL() || !d || !d.loc || mx) return;
    dlg.scrollTop = 0;
    dlg.classList.add("mxon");
    dlg.insertAdjacentHTML("beforeend", `<div class="mxw"><div id="rs-mx"></div>
      <button type="button" class="mxc"><i class="fas fa-arrow-left"></i> Back to details</button></div>`);
    mx = L.map("rs-mx", {zoomControl: false, maxZoom: 19});
    L.control.zoom({position: "bottomright"}).addTo(mx);
    const fit = () => mx.fitBounds([LODGE, d.loc], {padding: [90, 90]});
    recentreCtl(fit).addTo(mx);
    L.tileLayer(TILES, {attribution: "© OpenStreetMap", maxZoom: 19}).addTo(mx);
    L.polyline([LODGE, d.loc], {color: "#7cc4ff", weight: 3, dashArray: "6 8"}).addTo(mx);
    L.marker(LODGE, {icon: lodgeIcon()}).bindTooltip("Black Diamond Lodge", {permanent: true, direction: "bottom", offset: [0, 14], className: "ltip"}).addTo(mx);
    L.marker(d.loc, {icon: rIcon(d)}).addTo(mx);
    fit();
  }
  function shrinkMap() {
    if (!mx) return;
    mx.remove(); mx = null;
    dlg.querySelector(".mxw")?.remove();
    dlg.classList.remove("mxon");
  }
  function overview() {
    const near = Object.values(D).filter(d => d.loc && L.latLng(d.loc).distanceTo(LODGE) < 2500).map(d => d.loc);
    big.fitBounds([LODGE, ...near], {padding: [60, 60]});
  }
  function bigMap() {
    if (!hasL()) return;
    if (big) { big.invalidateSize(); return; }
    big = L.map("rs-map", {zoomControl: false, maxZoom: 19});
    L.control.zoom({position: "bottomright"}).addTo(big);
    recentreCtl(overview).addTo(big);
    const lowZoom = () => $("rs-map").classList.toggle("lowz", big.getZoom() < 17);
    big.on("zoomend", lowZoom);
    L.tileLayer(TILES, {attribution: "© OpenStreetMap", maxZoom: 19}).addTo(big);
    clus = L.markerClusterGroup({
      maxClusterRadius: 48, showCoverageOnHover: false, spiderfyDistanceMultiplier: 4.5,
      iconCreateFunction: c => {
        const pk = c.getAllChildMarkers().some(m => D[m.slug].pick);
        return L.divIcon({className: "", html: `<div class="rcl${pk ? " pk" : ""}">${c.getChildCount()}</div>`, iconSize: [52, 52], iconAnchor: [26, 26]});
      },
    }).addTo(big);
    L.marker(LODGE, {icon: lodgeIcon()}).bindTooltip("Black Diamond Lodge", {permanent: true, direction: "bottom", offset: [0, 14], className: "ltip"}).addTo(big);
    Object.entries(D).forEach(([s, d]) => {
      if (!d.loc) return;
      bigM[s] = L.marker(d.loc, {icon: rIcon(d)}).on("click", () => open_(s));
      bigM[s].slug = s;
    });
    overview();
    lowZoom();
    syncMap();
  }
  function syncMap() {
    if (!big) return;
    clus.clearLayers();
    clus.addLayers([...document.querySelectorAll(".rc")]
      .filter(r => !r.classList.contains("hide") && !r.classList.contains("hidden") && bigM[r.dataset.slug])
      .map(r => bigM[r.dataset.slug]));
  }
  document.querySelectorAll(".vt button").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll(".vt button").forEach(x => x.classList.toggle("on", x === b));
    const m = b.dataset.v === "map";
    $("rs-grid").style.display = m ? "none" : "";
    $("rs-map").style.display = m ? "" : "none";
    if (m) bigMap();
  }));

  sync();
})();
