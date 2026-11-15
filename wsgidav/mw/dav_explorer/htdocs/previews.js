"use strict";

import Split from "split.js";
import { config, getDAVClient, getNodeResourceUrl, getTree, settingsStore } from "./util.js";
import { setCommandButton, showNotification } from "./widgets.js";

const fileTypeInfo = {
  text: {
    cfg: { icon: "bi bi-file-earmark-code", lang: "properties" },
    conf: { icon: "bi bi-file-earmark-code", lang: "properties" },
    csv: { icon: "bi bi-filetype-csv" },
    ini: { icon: "bi bi-file-earmark-code", lang: "properties" },
    log: { icon: "bi bi-file-earmark-text" },
    md: { icon: "bi bi-file-earmark-text", lang: "markdown" },
    mdx: { icon: "bi bi-filetype-mdx", lang: "markdown" },
    toml: { icon: "bi bi-file-earmark-code", lang: "toml" },
    txt: { icon: "bi bi-file-earmark-text" },
    yaml: { icon: "bi bi-filetype-yml", lang: "yaml" },
    yml: { icon: "bi bi-filetype-yml", lang: "yaml" },
  },
  image: {
    ai: { icon: "bi bi-file-earmark-image" },
    bmp: { icon: "bi bi-file-earmark-image" },
    gif: { icon: "bi bi-file-earmark-image" },
    heic: { icon: "bi bi-file-earmark-image" },
    jpg: { icon: "bi bi-file-earmark-image" },
    jpeg: { icon: "bi bi-file-earmark-image" },
    png: { icon: "bi bi-file-earmark-image" },
    psd: { icon: "bi bi-file-earmark-image" },
    raw: { icon: "bi bi-file-earmark-image" },
    svg: { icon: "bi bi-file-earmark-image" },
    tiff: { icon: "bi bi-file-earmark-image" },
  },
  audio: {
    aac: { icon: "bi bi-file-earmark-music" },
    m4p: { icon: "bi bi-file-earmark-music" },
    mp3: { icon: "bi bi-file-earmark-music" },
    wav: { icon: "bi bi-file-earmark-play" },
  },
  video: {
    mov: { icon: "bi bi-file-earmark-play" },
    mp4: { icon: "bi bi-file-earmark-play" },
  },
  pdf: {
    pdf: { icon: "bi bi-file-earmark-pdf" },
  },
  office: {
    // Microsoft Office and Open Document formats
    // Word:
    doc: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word" },
    docm: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word" },
    docx: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word" },
    dot: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word", nft: true },
    dotx: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word", nft: true },
    dotm: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word", nft: true },
    odt: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word" },
    odm: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word" },
    fodt: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word" },
    ott: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word", nft: true },
    oth: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word", nft: true },
    uot: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word" },
    rtf: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word" },
    // Excel:
    xls: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel" },
    xlsm: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel" },
    xlsx: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel" },
    xlt: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel", nft: true },
    xltx: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel", nft: true },
    xltm: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel", nft: true },
    ods: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel" },
    fods: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel" },
    ots: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel", nft: true },
    uos: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel" },
    // PowerPoint:
    ppt: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint" },
    pptm: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint" },
    pptx: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint" },
    ppsx: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint" },
    ppsm: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint" },
    pps: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint" },
    potx: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint", nft: true },
    potm: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint", nft: true },
    pot: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint", nft: true },
    odp: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint" },
    fodp: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint" },
    otp: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint", nft: true },
    uop: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint" },
    key: { icon: "bi bi-filetype-key" },
    //
    odg: { icon: "bi bi-file-earmark-image", protocol: "ms-powerpoint" },
    otg: { icon: "bi bi-file-earmark-image", protocol: "ms-powerpoint", nft: true },
    fodg: { icon: "bi bi-file-earmark-image", protocol: "ms-powerpoint" },

    // Publisher:
    pub: { icon: "bi bi-file-earmark-ppt", protocol: "ms-publisher" },
    // Visio:
    vsd: { icon: "bi bi-file-earmark-diagram", protocol: "ms-visio" },
    vsdx: { icon: "bi bi-file-earmark-diagram", protocol: "ms-visio" },
    // Project:
    mpp: { icon: "bi bi-file-earmark-project", protocol: "ms-project" },
    mpt: { icon: "bi bi-file-earmark-project", protocol: "ms-project" },
    //Access:
    mdb: { icon: "bi bi-file-earmark-database", protocol: "ms-access" },
    accdb: { icon: "bi bi-file-earmark-database", protocol: "ms-access" },
  },
  archive: {
    "7z": { icon: "bi bi-file-earmark-zip" },
    gz: { icon: "bi bi-file-earmark-zip" },
    tar: { icon: "bi bi-file-earmark-zip" },
    zip: { icon: "bi bi-file-earmark-zip" },
  },
  font: {
    otf: { icon: "bi bi-file-earmark-font" },
    ttf: { icon: "bi bi-file-earmark-font" },
    woff: { icon: "bi bi-file-earmark-font" },
  },
  executable: {
    bat: { icon: "bi bi-file-earmark-terminal", text: true },
    exe: { icon: "bi bi-windows" },
    ps1: { icon: "bi bi-file-earmark-terminal", lang: "powershell" },
    sh: { icon: "bi bi-file-earmark-terminal", lang: "shell" },
  },
  code: {
    css: { icon: "bi bi-filetype-css", lang: "css" },
    html: { icon: "bi bi-filetype-html", lang: "html" },
    htm: { icon: "bi bi-filetype-html", lang: "html" },
    js: { icon: "bi bi-filetype-js", lang: "javascript" },
    json: { icon: "bi bi-filetype-json", lang: "json" },
    jsx: { icon: "bi bi-filetype-jsx", lang: "jsx" },
    mjs: { icon: "bi bi-filetype-js", lang: "javascript" },
    php: { icon: "bi bi-filetype-php" },
    py: { icon: "bi bi-filetype-py", lang: "python" },
    rb: { icon: "bi bi-filetype-rb" },
    sass: { icon: "bi bi-filetype-sass" },
    scss: { icon: "bi bi-filetype-scss", lang: "css" },
    sql: { icon: "bi bi-filetype-sql" },
    ts: { icon: "bi bi-filetype-tsx", lang: "typescript" },
    tsx: { icon: "bi bi-filetype-tsx", lang: "tsx" },
    xml: { icon: "bi bi-filetype-xml", lang: "xml" },
    java: { icon: "bi bi-filetype-java" },
  },
  other: {},
};

const fileExtensionMap = {};
for (let [type, extensions] of Object.entries(fileTypeInfo)) {
  for (let [ext, info] of Object.entries(extensions)) {
    let preview;
    switch (type) {
      case "image":
      case "pdf":
        preview = "image";
        break;
      case "text":
      case "code":
        preview = "text";
        break;
      default:
        // E.g. scripts: `lang` (syntax highlighting) or `text` mark plain text files
        if (info.lang || info.text) {
          preview = "text";
        }
    }
    fileExtensionMap[ext] = { icon: info.icon, type: type, preview: preview, lang: info.lang ?? null, protocol: info.protocol, nft: info.nft || false };
  }
}
// console.dir(fileExtensionMap);

export function getFileInfo(name) {
  if (!name || typeof name !== "string") {
    return null;
  }
  const extension = name.split(".").pop().toLowerCase();
  return fileExtensionMap[extension] || null;
}

export function getFileIcon(name) {
  const extension = name.split(".").pop().toLowerCase();
  return fileExtensionMap[extension] ? fileExtensionMap[extension].icon : undefined;
}

/**
 * Get the Office type information for a given file name.
 * @param {string} name - The file name.
 * @returns {object|null} The Office type information or null if not found.
 */
export function getOfficeUrlPrefix(node, options = {}) {
  const { newFromTemplate = false, readonly = false } = options;
  const info = getFileInfo(node.title);
  if (!info || !info.type || info.type !== "office") {
    return null;
  }
  const protocol = info.protocol;
  const operation = newFromTemplate ? "nft" : readonly ? "ofv" : "ofe";
  return info.protocol ? `${protocol}:${operation}|u|${getNodeResourceUrl(node)}` : null;
}

const imgElem = document.querySelector("aside.right img#preview-img");
const textElem = document.querySelector("aside.right div#preview-text");
const folderElem = document.querySelector("aside.right div#preview-folder");
const placeholderElem = document.querySelector("aside.right div#preview-unknown");
const settingsElem = document.querySelector("aside.right div#preview-settings");
const iframeElem = document.querySelector("aside.right iframe#preview-iframe");
// const folderInfo = document.querySelector("aside.right div#preview-folder p.folder-info");
const nodeInfo = document.querySelector("aside.right p.node-info");

const imgPlaceholderEmpty = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
const imgPlaceholderLoadingSvg =
  "data:image/svg+xml;charset=UTF-8," +
  encodeURIComponent(`
	<svg xmlns="http://www.w3.org/2000/svg" width="200" height="150" viewBox="0 0 200 150" fill="none">
	  <rect width="200" height="150" fill="#ddd"/>
	  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#aaa" font-size="20" font-family="Arial, sans-serif">
		Loading image...
	  </text>
	</svg>
  `);
const imgPlaceholderErrorSvg =
  "data:image/svg+xml;charset=UTF-8," +
  encodeURIComponent(`
	<svg xmlns="http://www.w3.org/2000/svg" width="200" height="150" viewBox="0 0 200 150" fill="none">
	  <rect width="200" height="150" fill="#ddd"/>
	  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#aaa" stroke="red" font-size="20" font-family="Arial, sans-serif">
		Error loading image.
	  </text>
	</svg>
  `);
/**
 * Splitter and Preview pane
 */
const splitterSize = [75, 25];
const splitter = Split(["main", "aside.right"], {
  sizes: splitterSize,
  minSize: 5,
  gutterSize: 5,
  onDragEnd: (sizes) => {
    const isOpen = sizes[1] > 5;
    document.querySelector("aside.right").classList.toggle("show", isOpen);
    setCommandButton("togglePreview", { pressed: isOpen });
  },
});

document.querySelector("aside.right img#preview-img").addEventListener("error", (e) => {
  console.warn(`Could not load preview <img src="${e.target.src}">`, e);
});

/**
 * Show or hide the preview pane.
 * Hiding the pane is cancelled if the user does not want to discard unsaved
 * changes in the text editor.
 * @param {boolean} flag
 * @param {object} [options]
 * @param {boolean} [options.refresh=true] Update the preview for the active node
 * @returns {boolean} false if cancelled
 */
export function togglePreviewPane(flag = true, options = {}) {
  const { refresh = true } = options;
  if (!flag && !closeTextEditor()) {
    setCommandButton("togglePreview", { pressed: true });
    return false;
  }
  if (flag) {
    splitter.setSizes(splitterSize);
  } else {
    splitter.collapse(1);
  }
  document.querySelector("aside.right").classList.toggle("show", !!flag);
  setCommandButton("togglePreview", { pressed: !!flag });
  settingsStore.set("showInfoPane", !!flag);
  if (!refresh) {
    // The caller updates the preview
  } else if (flag) {
    const tree = getTree();
    const activeNode = tree.getActiveNode();
    if (activeNode) {
      showPreview(activeNode, { autoOpen: false });
    }
  } else {
    showPreview(null, { autoOpen: false });
  }
  return true;
}

export function isPreviewPaneOpen() {
  return !!document.querySelector("aside.right.show");
}

export function updateNodePreviewInfo(node) {
  if (!node || !nodeInfo) {
    return;
  }

  if (node.type === "directory") {
    let itemCount;
    if (node.isUnloaded()) {
      itemCount = "children not yet loaded";
    } else {
      itemCount = node.children ? node.children.length : 0;
      itemCount = `${itemCount} item${itemCount !== 1 ? "s" : ""}`;
    }
    nodeInfo.textContent = `${node.title} (${itemCount})`;
  } else {
    const sizeKB = node.data.size ? (node.data.size / 1024).toFixed(2) : "Unknown size";
    nodeInfo.textContent = `${node.title} (${sizeKB} KB)`;
    nodeInfo.textContent += node.data.mime ? `, ${node.data.mime}` : "";
  }
}

/** Return a normalized http(s) URL, or null for anything else (javascript:, data:, ...). */
function sanitizeUrl(rawUrl) {
  try {
    const parsed = new URL(rawUrl, window.location.href);
    if (parsed.protocol === "http:" || parsed.protocol === "https:") {
      return parsed.href;
    }
  } catch (e) {
    // invalid URL
  }
  return null;
}

// Incremented on every showPreview() call, so pending async loads can detect
// that they are outdated
let _previewSeq = 0;

// Blob URL of the currently displayed image preview (must be revoked on change)
let _imgObjectUrl = null;

function revokeImageObjectUrl() {
  if (_imgObjectUrl) {
    URL.revokeObjectURL(_imgObjectUrl);
    _imgObjectUrl = null;
  }
}

/* --- Text Preview and Editor --- */

// Requested lock timeout. The lock is refreshed while the editor is open.
// Kept short, so a lock that was not released (e.g. browser crash) expires
// soon. Refreshing at 80% (~96s) still works with Chrome's throttling of
// timers in hidden tabs (about once per minute).
const LOCK_TIMEOUT_SECS = 120;

const textHostElem = textElem.querySelector("div.cm-host");
const textFallbackElem = textElem.querySelector("pre.text-fallback");
const textStatusElem = textElem.querySelector(".text-status");
const textButtons = {
  edit: textElem.querySelector('button[data-text-command="edit"]'),
  save: textElem.querySelector('button[data-text-command="save"]'),
  cancel: textElem.querySelector('button[data-text-command="cancel"]'),
};

// Promise of the lazily loaded editor.js module (CodeMirror)
let _editorModule = null;
// The `TextViewer` instance (created on first use)
let _viewer = null;
// The file that is displayed by `_viewer` (node is null while loading or on errors)
const _text = { node: null, url: null, langExt: null };
// The current edit session (`token` is null if not editing)
const _edit = { node: null, path: null, url: null, token: null, refreshTimer: null, prevSizes: null, starting: false, saving: false };

async function getTextViewer() {
  if (!_editorModule) {
    _editorModule = import("./editor.js").catch((err) => {
      _editorModule = null; // Try again next time
      throw err;
    });
  }
  const mod = await _editorModule;
  if (!_viewer) {
    _viewer = new mod.TextViewer(textHostElem, {
      onSave: () => saveTextEditor(),
      onCancel: () => closeTextEditor(),
      onChange: () => updateTextToolbar(),
    });
  }
  return { viewer: _viewer, mod: mod };
}

/** Return true if a file is open in the text editor (and locked). */
export function isEditingText() {
  return !!_edit.token;
}

function updateTextToolbar() {
  const editing = isEditingText();
  const dirty = editing && !!_viewer?.isDirty();
  const canEdit = !config.readonly && !!_text.node && !_edit.starting;
  textButtons.edit.hidden = editing || !canEdit;
  textButtons.save.hidden = !editing;
  textButtons.cancel.hidden = !editing;
  textButtons.save.disabled = !dirty || _edit.saving;
  textStatusElem.textContent = _edit.starting ? "Locking..." : editing ? `Editing${dirty ? " (modified)" : ""}` : "";
  textElem.classList.toggle("editing", editing);
}

function parseLockTimeout(serverTimeout) {
  const m = /Second-(\d+)/i.exec(String(serverTimeout ?? ""));
  return m ? Number(m[1]) : LOCK_TIMEOUT_SECS;
}

function unlockResource(path, token) {
  return getDAVClient()
    .unlock(path, `<${token}>`)
    .catch((err) => console.warn(`Could not unlock ${path}`, err));
}

async function refreshLock() {
  const { node, url, token } = _edit;
  if (!token) {
    return;
  }
  try {
    // A refresh is a LOCK request without body (the webdav client always sends one)
    const response = await fetch(url, {
      method: "LOCK",
      headers: { If: `(<${token}>)`, Timeout: `Second-${LOCK_TIMEOUT_SECS}` },
    });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
  } catch (err) {
    console.warn("Could not refresh lock", err);
    if (token === _edit.token) {
      showNotification(`Could not refresh the lock on "${node.title}": ${err.message}`, { type: "warning" });
    }
  }
}

/** Make the preview pane wider while editing. */
function widenPreviewPane() {
  _edit.prevSizes = splitter.getSizes();
  if (_edit.prevSizes[1] < 60) {
    splitter.setSizes([40, 60]);
  }
}

function restorePreviewPane() {
  if (_edit.prevSizes) {
    splitter.setSizes(_edit.prevSizes);
    _edit.prevSizes = null;
  }
}

/**
 * Lock the file that is displayed in the text preview and make it editable.
 * @returns {Promise<boolean>} true if the editor is active
 */
export async function startTextEditor(node) {
  if (isEditingText() && _edit.node === node) {
    _viewer.focus();
    return true;
  }
  if (config.readonly || isEditingText() || _edit.starting) {
    return false;
  }
  if (!node || !_viewer || _text.node !== node) {
    showNotification("This file cannot be edited.", { type: "warning" });
    return false;
  }
  const path = node.getPath();
  const url = _text.url;
  let token;
  let timeoutSecs;

  _edit.starting = true;
  updateTextToolbar();
  try {
    try {
      const lock = await getDAVClient().lock(path, { timeout: `Second-${LOCK_TIMEOUT_SECS}` });
      token = lock.token;
      timeoutSecs = parseLockTimeout(lock.serverTimeout);
    } catch (err) {
      const msg = err.status === 423 ? `"${node.title}" is locked by another user or application.` : `Could not lock "${node.title}": ${err.message}`;
      showNotification(msg, { type: "warning" });
      return false;
    }
    // Edit the current version, the preview may be outdated
    let text;
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
      }
      text = await response.text();
    } catch (err) {
      unlockResource(path, token);
      showNotification(`Could not load "${node.title}": ${err.message}`, { type: "error" });
      return false;
    }
    if (_text.node !== node) {
      // Another file was selected in the meantime
      unlockResource(path, token);
      return false;
    }
    Object.assign(_edit, { node: node, path: path, url: url, token: token, saving: false });
    _edit.refreshTimer = setInterval(refreshLock, Math.max(10, timeoutSecs * 0.8) * 1000);
    _viewer.setText(text, _text.langExt);
    _viewer.setEditable(true);
    widenPreviewPane();
    _viewer.focus();
    return true;
  } finally {
    _edit.starting = false;
    updateTextToolbar();
  }
}

/** Store the editor content on the server, using the lock token. */
export async function saveTextEditor() {
  if (!isEditingText() || _edit.saving) {
    return false;
  }
  const { node, path, token } = _edit;
  const doc = _viewer.getDoc();
  const text = doc.toString();
  _edit.saving = true;
  updateTextToolbar();
  try {
    const res = await getDAVClient().putFileContents(path, text, {
      overwrite: true,
      headers: { If: `(<${token}>)`, "Content-Type": "text/plain; charset=utf-8" },
    });
    if (res === false) {
      throw new Error("The server did not overwrite the file");
    }
    // The user may have continued typing while saving
    _viewer.markClean(doc);
    node.data.size = new Blob([text]).size;
    node.data.lastmod = Date.now();
    node.update();
    updateNodePreviewInfo(node);
    showNotification(`Saved "${node.title}".`, { type: "info" });
    return true;
  } catch (err) {
    showNotification(`Failed to save "${node.title}": ${err.message}`, { type: "error" });
    console.error("Failed to save: ", err);
    return false;
  } finally {
    _edit.saving = false;
    updateTextToolbar();
  }
}

/**
 * Leave edit mode and release the lock.
 * Asks the user before unsaved changes are discarded.
 * @param {object} [options]
 * @param {boolean} [options.force=false] Discard changes without asking
 * @param {boolean} [options.unlock=true] Send an UNLOCK request
 * @returns {boolean} false if the user wants to keep editing
 */
export function closeTextEditor(options = {}) {
  const { force = false, unlock = true } = options;
  if (!isEditingText()) {
    return true;
  }
  if (!force && _edit.saving) {
    showNotification("Please wait until the file is saved.", { type: "warning" });
    return false;
  }
  if (!force && _viewer.isDirty() && !confirm(`Discard unsaved changes to "${_edit.node.title}"?`)) {
    _viewer.focus();
    return false;
  }
  const { path, token } = _edit;
  clearInterval(_edit.refreshTimer);
  restorePreviewPane();
  Object.assign(_edit, { node: null, path: null, url: null, token: null, refreshTimer: null, saving: false });
  if (_viewer.isDirty()) {
    _viewer.revert();
  }
  _viewer.setEditable(false);
  updateTextToolbar();
  if (unlock) {
    unlockResource(path, token);
  }
  return true;
}

textElem.querySelector(".text-toolbar").addEventListener("click", (e) => {
  const button = e.target.closest("button[data-text-command]");
  if (!button || button.disabled) {
    return;
  }
  switch (button.dataset.textCommand) {
    case "edit":
      startTextEditor(_text.node);
      break;
    case "save":
      saveTextEditor();
      break;
    case "cancel":
      closeTextEditor();
      break;
  }
});

window.addEventListener("beforeunload", (e) => {
  if (isEditingText() && _viewer.isDirty()) {
    e.preventDefault();
    e.returnValue = ""; // Required by some browsers
  }
});

window.addEventListener("pagehide", () => {
  if (!isEditingText()) {
    return;
  }
  // Best effort: the lock times out if this request fails
  fetch(_edit.url, { method: "UNLOCK", keepalive: true, headers: { "Lock-Token": `<${_edit.token}>` } }).catch(() => {});
  closeTextEditor({ force: true, unlock: false });
});

/**
 * Display a node or URL in the preview pane.
 *
 * @param {object|string|null} urlOrNode
 * @param {object} [options]
 * @param {boolean} [options.autoOpen=false] Open the preview pane if it is hidden
 * @param {boolean} [options.iframe=false] Display the URL in an iframe
 * @param {boolean} [options.edit=false] Open a text file in the editor
 * @param {number} [options.maxSizeKB]
 * @returns {Promise<boolean>} false if nothing is displayed
 */
export async function showPreview(urlOrNode, options = {}) {
  let { autoOpen = false, iframe = false, edit = false, maxSizeKB = settingsStore.get("max_preview_size_kb") } = options;

  if (edit && isEditingText() && urlOrNode === _edit.node) {
    return startTextEditor(urlOrNode); // Already editing: just focus the editor
  }
  if (!closeTextEditor()) {
    return false; // The user wants to keep editing
  }
  const seq = ++_previewSeq;

  imgElem.onload = imgElem.onerror = null;
  imgElem.src = imgPlaceholderEmpty;
  revokeImageObjectUrl();
  _text.node = _text.url = _text.langExt = null;
  textFallbackElem.textContent = "";
  updateTextToolbar();
  if (!urlOrNode) {
    return false;
  }
  if (!isPreviewPaneOpen()) {
    if (autoOpen) {
      togglePreviewPane(true, { refresh: false });
    } else {
      return false;
    }
  }
  const node = !urlOrNode || typeof urlOrNode === "string" ? null : urlOrNode;
  const rawUrl = node ? getNodeResourceUrl(urlOrNode) : urlOrNode;
  const url = urlOrNode === "settings" ? rawUrl : sanitizeUrl(rawUrl);
  if (!url) {
    console.warn("Refusing to preview unsafe URL", rawUrl);
    return false;
  }
  const isFolder = node?.type === "directory";
  let preview = null;

  if (urlOrNode === "settings") {
    preview = "settings";
  } else if (iframe) {
    preview = "iframe";
  } else if (!isFolder) {
    // Derive the preview type from the file name (folders never have a preview)
    preview = getFileInfo(node ? node.title : new URL(url).pathname)?.preview ?? null;
  }
  placeholderElem.replaceChildren(Object.assign(document.createElement("p"), { textContent: "No preview available." }));
  if (preview && node && node.data.size > 1024 * maxSizeKB) {
    // Large files must be previewed explicitly to avoid performance issues.
    // Build the elements via DOM API to prevent XSS.
    const link = Object.assign(document.createElement("a"), { href: url, target: "_blank", rel: "noopener", textContent: "Click here" });
    placeholderElem.replaceChildren(`File is too large (> ${Number(maxSizeKB)} KiB).`, document.createElement("br"), link, " to preview.");
    preview = null;
  }
  if (edit && preview !== "text") {
    showNotification("This file cannot be edited here.", { type: "warning" });
  }

  imgElem.classList.toggle("hidden", preview !== "image");
  textElem.classList.toggle("hidden", preview !== "text");
  settingsElem.classList.toggle("hidden", preview !== "settings");
  folderElem.classList.toggle("hidden", !isFolder);
  placeholderElem.classList.toggle("hidden", isFolder || preview != null);
  iframeElem.classList.toggle("hidden", preview !== "iframe");
  nodeInfo.classList.toggle("hidden", !node);

  switch (preview) {
    case "text": {
      textFallbackElem.textContent = "Loading...";
      textFallbackElem.classList.remove("hidden");
      textHostElem.classList.add("hidden");
      let text;
      let ok = false;
      try {
        // Bypass the browser cache, the file may have been edited
        const response = await fetch(url, { cache: "no-store" });
        ok = response.ok;
        text = ok ? await response.text() : `Could not load preview: ${response.status} ${response.statusText}`;
      } catch (err) {
        text = `Could not load preview: ${err.message}`;
      }
      let viewer = null;
      let langExt = null;
      if (ok) {
        try {
          const res = await getTextViewer();
          viewer = res.viewer;
          langExt = await res.mod.loadLanguage(getFileInfo(node ? node.title : new URL(url).pathname)?.lang);
        } catch (err) {
          // E.g. the CDN is not reachable: display plain text
          console.warn("Could not load the text editor (CodeMirror)", err);
        }
      }
      // Ignore the result if another preview was requested in the meantime
      if (seq !== _previewSeq) {
        break;
      }
      if (viewer) {
        viewer.setText(text, langExt);
        textFallbackElem.textContent = "";
        textFallbackElem.classList.add("hidden");
        textHostElem.classList.remove("hidden");
        Object.assign(_text, { node: node, url: url, langExt: langExt });
      } else {
        textFallbackElem.textContent = text;
      }
      updateTextToolbar();
      if (edit) {
        if (ok && node) {
          await startTextEditor(node);
        } else {
          showNotification("This file cannot be edited.", { type: "warning" });
        }
      }
      break;
    }
    case "image": {
      imgElem.setAttribute("src", imgPlaceholderLoadingSvg);
      // Load the image data via fetch() and display it through a blob URL,
      // so no DOM-derived string is ever assigned to the `src` attribute.
      let objectUrl = null;
      try {
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`${response.status} ${response.statusText}`);
        }
        const blob = await response.blob();
        if (seq !== _previewSeq) {
          break; // Another preview was requested in the meantime
        }
        objectUrl = URL.createObjectURL(blob);
      } catch (err) {
        console.warn("Error loading preview %s", url, err);
        if (seq === _previewSeq) {
          imgElem.src = imgPlaceholderErrorSvg;
        }
        break;
      }
      revokeImageObjectUrl();
      _imgObjectUrl = objectUrl;
      imgElem.onerror = (e) => {
        imgElem.onerror = null;
        console.warn("Error displaying preview %s", url, e);
        imgElem.src = imgPlaceholderErrorSvg;
      };
      imgElem.src = objectUrl;
      break;
    }
    case "iframe": {
      iframeElem.src = "about:blank"; // Reset before setting new src
      // Only embed same-origin pages (e.g. the bundled help page)
      const parsed = new URL(url);
      if (parsed.origin !== window.location.origin) {
        console.warn("Refusing to embed cross-origin URL", url);
        break;
      }
      iframeElem.src = parsed.href;
      break;
    }
  }

  updateNodePreviewInfo(node);

  return true;
}
