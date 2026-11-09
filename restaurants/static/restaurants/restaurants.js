(function () {
  "use strict";
  const D = JSON.parse(document.getElementById("rs-data").textContent);
  const C = JSON.parse(document.getElementById("rs-config").textContent);
  const $ = id => document.getElementById(id);
  const ov = $("rs-ov"), sov = $("rs-sov"), dlg = $("rs-dlg");
  const STORE = "rs-shortlist", IDLE_MS = 30 * 60 * 1000, MAX = 8;
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

  // ── Shortlist: kept in localStorage, cleared after 30 idle minutes ──
  let list = [], touched = Date.now();
  try {
    const saved = JSON.parse(localStorage.getItem(STORE) || "null");
    if (saved && Date.now() - saved.t < IDLE_MS) list = saved.list.filter(s => D[s]);
  } catch (e) { /* ignore */ }
  const persist = () => { try { localStorage.setItem(STORE, JSON.stringify({list, t: touched})); } catch (e) { /* ignore */ } };
  const activity = () => { touched = Date.now(); if (list.length) persist(); };
  ["pointerdown", "keydown"].forEach(ev => document.addEventListener(ev, activity, {passive: true}));
  setInterval(() => { if (list.length && Date.now() - touched > IDLE_MS) { list = []; sync(); } }, 30 * 1000);

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
  function toggle(s) { list = list.includes(s) ? list.filter(x => x !== s) : [s, ...list].slice(0, MAX); touched = Date.now(); sync(); }

  // ── Details ──
  function qrSvg(text) {
    if (typeof qrcode === "undefined") return "";
    const q = qrcode(0, "M"); q.addData(text); q.make();
    return q.createSvgTag({cellSize: 4, margin: 1, scalable: true});
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
      <div class="dr">${d.loc ? '<div class="mini" id="rs-mini"></div>' : ""}<div class="qr">${qrSvg(d.maps)}</div>
        <div class="cap">Scan for directions, menu &amp; reviews on your phone</div><button type="button" class="save"></button></div>`;
    sync();
    ov.classList.add("show");
    if (d.loc) setTimeout(() => miniMap(d), 30);
  }
  function closeDlg() { ov.classList.remove("show"); delete dlg.dataset.slug; }

  dlg.addEventListener("click", e => {
    if (e.target.closest(".dclose")) return closeDlg();
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
  $("rs-send").addEventListener("click", () => {
    if (!list.length || typeof qrcode === "undefined") return;
    const url = C.shortlistUrl + "#" + list.map(s => encodeURIComponent(D[s].name) + "~" + D[s].pid).join("|");
    const q = qrcode(0, "L"); q.addData(url); q.make();
    $("rs-sqr").innerHTML = q.createImgTag(8, 8);
    $("rs-surl").textContent = url;
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
    html: `<div class="rpin${d.pick ? " pk" : ""}" style="--c1:${d.c1};--c2:${d.c2};${bg(d)}">${d.photos.length ? "" : `<i class="fas ${d.icon}"></i>`}</div><div class="rlab">${esc(d.name)}</div>`});
  let mini, big, clus;
  const bigM = {};

  function miniMap(d) {
    if (!hasL() || !$("rs-mini")) return;
    if (mini) mini.remove();
    mini = L.map("rs-mini", {zoomControl: false, attributionControl: false});
    L.tileLayer(TILES).addTo(mini);
    L.marker(LODGE, {icon: lodgeIcon()}).addTo(mini);
    L.marker(d.loc, {icon: L.divIcon({className: "", html: `<div class="rpin sm" style="--c1:${d.c1};--c2:${d.c2}"></div>`, iconSize: [22, 22], iconAnchor: [11, 11]})}).addTo(mini);
    L.polyline([LODGE, d.loc], {color: "#7cc4ff", weight: 2, dashArray: "4 6"}).addTo(mini);
    mini.fitBounds([LODGE, d.loc], {padding: [28, 28]});
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
    const Recentre = L.Control.extend({
      options: {position: "bottomright"},
      onAdd() {
        const bar = L.DomUtil.create("div", "leaflet-bar");
        const a = L.DomUtil.create("a", "recentre", bar);
        a.href = "#"; a.title = "Recentre"; a.setAttribute("role", "button");
        a.innerHTML = '<i class="fas fa-crosshairs"></i>';
        L.DomEvent.disableClickPropagation(bar);
        L.DomEvent.on(a, "click", e => { L.DomEvent.preventDefault(e); overview(); });
        return bar;
      },
    });
    new Recentre().addTo(big);
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
