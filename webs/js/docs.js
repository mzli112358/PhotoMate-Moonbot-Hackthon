const catalogEl = document.getElementById("docCatalog");
const tocEl = document.getElementById("docToc");
const articleEl = document.getElementById("docArticle");

let currentDocId = "overview";

function getDocIdFromUrl() {
  const params = new URLSearchParams(location.search);
  return params.get("id") || "overview";
}

function setDocIdInUrl(docId) {
  const url = new URL(location.href);
  url.searchParams.set("id", docId);
  history.replaceState({}, "", url);
}

async function fetchCatalog() {
  const res = await fetch("/api/docs/catalog");
  if (!res.ok) throw new Error("目录加载失败");
  return res.json();
}

async function fetchDocument(docId) {
  const res = await fetch(`/api/docs/${encodeURIComponent(docId)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "文档加载失败");
  }
  return res.json();
}

function renderCatalog(items, activeId) {
  catalogEl.innerHTML = "";
  items.forEach((item) => {
    const a = document.createElement("a");
    a.href = `/docs?id=${encodeURIComponent(item.id)}`;
    a.textContent = item.title;
    a.classList.toggle("active", item.id === activeId);
    a.addEventListener("click", (e) => {
      e.preventDefault();
      loadDocument(item.id);
    });
    catalogEl.appendChild(a);
  });
}

function renderToc(toc, docTitle) {
  tocEl.innerHTML = "";
  if (!toc || !toc.length) return;

  const label = document.createElement("p");
  label.className = "doc-toc-label";
  label.textContent = "本章";
  tocEl.appendChild(label);

  toc.forEach((item) => {
    const a = document.createElement("a");
    a.href = `#${item.id}`;
    a.textContent = item.title;
    a.className = `level-${item.level}`;
    a.addEventListener("click", (e) => {
      e.preventDefault();
      const el = document.getElementById(item.id);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
      setActiveToc(item.id);
    });
    tocEl.appendChild(a);
  });
}

function setActiveToc(id) {
  tocEl.querySelectorAll("a").forEach((a) => {
    a.classList.toggle("active", a.getAttribute("href") === `#${id}`);
  });
}

function setupScrollSpy(toc) {
  if (!toc.length) return;
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          setActiveToc(entry.target.id);
        }
      });
    },
    { rootMargin: "-20% 0px -70% 0px", threshold: 0 }
  );
  toc.forEach((item) => {
    const el = document.getElementById(item.id);
    if (el) observer.observe(el);
  });
}

async function loadDocument(docId) {
  currentDocId = docId;
  setDocIdInUrl(docId);
  articleEl.innerHTML = '<p class="doc-loading">加载中…</p>';

  try {
    const [catalog, doc] = await Promise.all([
      fetchCatalog(),
      fetchDocument(docId),
    ]);
    renderCatalog(catalog, docId);
    articleEl.innerHTML = `<h1>${escapeHtml(doc.title)}</h1>${doc.html}`;
    renderToc(doc.toc, doc.title);
    setupScrollSpy(doc.toc);
    if (docId === "overview") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  } catch (err) {
    articleEl.innerHTML = `<p class="doc-muted">${escapeHtml(String(err.message || err))}</p>`;
  }
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

loadDocument(getDocIdFromUrl());

window.addEventListener("popstate", () => {
  loadDocument(getDocIdFromUrl());
});
