"use strict";

import { Wunderbaum, util, getNodeResourceUrl, getDAVClient, getActiveNode, getTree, isFile, isFolder, isRootFolder, isValidResourceName } from "./util.js";

/**
 * Command Buttons & Row Actions
 */
// Buttons marked with `data-write` are hidden in readonly mode (see app.css).
// Each row shows one quick action and a button that opens the context menu.
export const rowActionsHtmlTemplateFile = `
<span class="row-actions">
  <i class="wb-button bi bi-cloud-download" role="button" title="Download file" aria-label="Download file" data-command="download"></i>
  <i class="wb-button bi bi-three-dots-vertical" role="button" title="More actions..." aria-label="More actions" aria-haspopup="menu" data-command="showMenu"></i>
</span>
`;
export const rowActionsHtmlTemplateFolder = `
<span class="row-actions">
  <i class="wb-button bi bi-cloud-plus" role="button" title="Upload files to this folder..." aria-label="Upload files to this folder" data-command="upload" data-write></i>
  <i class="wb-button bi bi-three-dots-vertical" role="button" title="More actions..." aria-label="More actions" aria-haspopup="menu" data-command="showMenu"></i>
</span>
`;

/* --- */

export function registerCommandButtons(parent, handler) {
  util.onEvent(parent, "click", "i.wb-button:not(.disabled)", (e) => {
    // console.info("click", e, e.target);
    const target = e.target;
    let isPressed;
    if (target.classList.contains("wb-button-toggle")) {
      isPressed = target.classList.toggle("wb-pressed");
    }
    const res = handler({
      event: e,
      isPressed: isPressed,
      command: target.dataset.command,
      tree: Wunderbaum.getTree(),
      node: Wunderbaum.getNode(target),
      target: target,
    });
    return res;
  });
}

export function setCommandButton(command, options = {}) {
  const { pressed = undefined } = options;
  const escapedCommand = typeof CSS !== "undefined" && typeof CSS.escape === "function" ? CSS.escape(String(command)) : String(command).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  const buttonElem = document.querySelector(`.wb-button[data-command="${escapedCommand}"]`);
  if (!buttonElem) {
    console.info("command:", command, "button element not found");
    return;
  }
  if (pressed !== undefined && buttonElem.classList.contains("wb-button-toggle")) {
    buttonElem.classList.toggle("wb-pressed", pressed);
  }
}

/* --- Context Menu --- */

const _menu = {
  elem: null,
  anchor: null,
  onSelect: null,
  onClose: null,
  // Set when a pointerdown on the anchor closed the menu, so the following
  // click on the same anchor toggles the menu instead of reopening it
  closedByAnchor: null,
  closedAt: 0,
};

function getMenuElem() {
  if (_menu.elem) {
    return _menu.elem;
  }
  const elem = document.createElement("div");
  elem.id = "contextMenu";
  elem.className = "context-menu";
  elem.setAttribute("role", "menu");
  elem.hidden = true;
  document.body.appendChild(elem);
  _menu.elem = elem;

  elem.addEventListener("click", (e) => {
    const itemElem = e.target.closest("button.context-menu-item");
    if (!itemElem || itemElem.disabled) {
      return;
    }
    const item = itemElem._menuItem;
    const onSelect = _menu.onSelect;
    closeContextMenu({ restoreFocus: true });
    onSelect?.(item);
  });
  // Mouse and keyboard highlight the same item
  elem.addEventListener("pointermove", (e) => {
    const itemElem = e.target.closest("button.context-menu-item:not(:disabled)");
    if (itemElem && document.activeElement !== itemElem) {
      itemElem.focus();
    }
  });
  elem.addEventListener("keydown", (e) => {
    const items = [...elem.querySelectorAll("button.context-menu-item:not(:disabled)")];
    const idx = items.indexOf(document.activeElement);
    let next = null;
    switch (e.key) {
      case "ArrowDown":
        next = items[(idx + 1) % items.length];
        break;
      case "ArrowUp":
        next = items[(idx - 1 + items.length) % items.length];
        break;
      case "Home":
        next = items[0];
        break;
      case "End":
        next = items[items.length - 1];
        break;
      case "Escape":
      case "Tab":
        closeContextMenu({ restoreFocus: true });
        break;
      default:
        return; // Enter and Space trigger a click on the focused button
    }
    e.preventDefault();
    e.stopPropagation();
    next?.focus();
  });
  // Do not open the native context menu on top of ours
  elem.addEventListener("contextmenu", (e) => e.preventDefault());

  // Light dismiss
  document.addEventListener(
    "pointerdown",
    (e) => {
      if (elem.hidden || elem.contains(e.target)) {
        return;
      }
      _menu.closedByAnchor = _menu.anchor?.contains(e.target) ? _menu.anchor : null;
      _menu.closedAt = Date.now();
      closeContextMenu();
    },
    true
  );
  document.addEventListener(
    "scroll",
    (e) => {
      if (!elem.hidden && !elem.contains(e.target)) {
        closeContextMenu();
      }
    },
    true
  );
  window.addEventListener("resize", () => closeContextMenu());
  window.addEventListener("blur", () => closeContextMenu());
  return elem;
}

export function isContextMenuOpen() {
  return !!_menu.elem && !_menu.elem.hidden;
}

export function closeContextMenu(options = {}) {
  const { restoreFocus = false } = options;
  if (!isContextMenuOpen()) {
    return;
  }
  const onClose = _menu.onClose;
  _menu.elem.hidden = true;
  _menu.elem.replaceChildren();
  _menu.anchor?.setAttribute("aria-expanded", "false");
  _menu.anchor = _menu.onSelect = _menu.onClose = null;
  if (restoreFocus) {
    onClose?.();
  }
}

/**
 * Show a context menu at a pointer position or below an anchor element.
 *
 * @param {Array<object|string>} items `{command, label, icon, shortcut, disabled, danger}`
 *     or "-" for a separator.
 * @param {object} options
 * @param {number} [options.x] Viewport position (used if no `anchor` is given)
 * @param {number} [options.y]
 * @param {Element} [options.anchor] Align the menu to this element
 * @param {string} [options.align] "start" (default) or "end" (right-aligned to anchor)
 * @param {string} [options.label] Accessible name of the menu
 * @param {function} [options.onSelect] Called with the selected item
 * @param {function} [options.onClose] Called to restore the focus when the menu
 *     is closed by keyboard or after selecting an item
 */
export function showContextMenu(items, options = {}) {
  const { x = 0, y = 0, anchor = null, align = "start", label = "Actions", onSelect = null, onClose = null } = options;
  const elem = getMenuElem();

  if (anchor && anchor === _menu.closedByAnchor && Date.now() - _menu.closedAt < 1000) {
    // The click on the anchor that closed this menu should not reopen it
    _menu.closedByAnchor = null;
    return;
  }
  _menu.closedByAnchor = null;
  closeContextMenu();

  // Drop leading, trailing, and repeated separators
  const cleaned = [];
  for (const item of items) {
    if (item === "-" && (cleaned.length === 0 || cleaned[cleaned.length - 1] === "-")) {
      continue;
    }
    cleaned.push(item);
  }
  while (cleaned[cleaned.length - 1] === "-") {
    cleaned.pop();
  }
  if (cleaned.length === 0) {
    return;
  }

  for (const item of cleaned) {
    if (item === "-") {
      const sep = document.createElement("div");
      sep.className = "context-menu-separator";
      sep.setAttribute("role", "separator");
      elem.appendChild(sep);
      continue;
    }
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "context-menu-item" + (item.danger ? " danger" : "");
    btn.setAttribute("role", "menuitem");
    btn.dataset.command = item.command;
    btn.disabled = !!item.disabled;
    btn._menuItem = item;

    const icon = document.createElement("i");
    icon.className = `bi ${item.icon || ""}`;
    icon.setAttribute("aria-hidden", "true");
    const text = document.createElement("span");
    text.className = "label";
    text.textContent = item.label;
    btn.append(icon, text);
    if (item.shortcut) {
      const kbd = document.createElement("kbd");
      kbd.textContent = item.shortcut;
      btn.appendChild(kbd);
      btn.setAttribute("aria-keyshortcuts", item.shortcut);
    }
    elem.appendChild(btn);
  }
  elem.setAttribute("aria-label", label);
  _menu.anchor = anchor;
  _menu.onSelect = onSelect;
  _menu.onClose = onClose;
  anchor?.setAttribute("aria-expanded", "true");

  // Measure, then keep the menu inside the viewport
  elem.style.visibility = "hidden";
  elem.hidden = false;
  const { offsetWidth: w, offsetHeight: h } = elem;
  const vw = document.documentElement.clientWidth;
  const vh = document.documentElement.clientHeight;
  let left = x;
  let top = y;
  if (anchor) {
    const r = anchor.getBoundingClientRect();
    left = align === "end" ? r.right - w : r.left;
    top = r.bottom + 2;
    if (top + h > vh) {
      top = r.top - h - 2;
    }
  } else {
    if (left + w > vw) {
      left -= w;
    }
    if (top + h > vh) {
      top -= h;
    }
  }
  const margin = 4;
  elem.style.left = `${Math.max(margin, Math.min(left, vw - w - margin))}px`;
  elem.style.top = `${Math.max(margin, Math.min(top, vh - h - margin))}px`;
  elem.style.visibility = "";

  elem.querySelector("button.context-menu-item:not(:disabled)")?.focus();
}

let _notificationTimeoutId = null;
let _notificationResolve = null;

export async function showNotification(message, options = {}) {
  const durationMap = { info: 5000, warning: 10000, error: 20000 };
  let { type = "info", duration = undefined } = options;
  if (!durationMap[type]) {
    type = "error";
  }
  duration ??= durationMap[type];

  const notification = document.getElementById("notification");

  // Set content with close button
  notification.innerHTML = '<span class="notification-message"></span><span class="notification-close" title="Dismiss">&times;</span>';
  notification.className = `notification ${type}`;
  notification.style.display = "inline";
  // Prevent XSS by setting textContent instead of innerHTML
  notification.querySelector(".notification-message").textContent = message;

  // A new message replaces the previous one: cancel its pending timer, so it
  // does not hide this message early
  if (_notificationTimeoutId) {
    clearTimeout(_notificationTimeoutId);
    _notificationTimeoutId = null;
  }
  _notificationResolve?.();

  return new Promise((resolve) => {
    _notificationResolve = resolve;
    const hideNotification = () => {
      if (_notificationResolve !== resolve) {
        return; // Already replaced by a newer notification
      }
      clearTimeout(_notificationTimeoutId);
      _notificationTimeoutId = null;
      _notificationResolve = null;
      notification.style.display = "none";
      resolve();
    };
    notification.querySelector(".notification-close").addEventListener("click", hideNotification);
    _notificationTimeoutId = setTimeout(hideNotification, duration);
  });
}

/** Download the file with or without prompting */
export async function downloadFile(node, options = {}) {
  let { dialog = true } = options;
  if (dialog && !("showDirectoryPicker" in window)) {
    console.warn("Download dialog not available in this browser: using default folder.");
    dialog = false;
  }
  if (dialog) {
    return downloadFileToFolder(node);
  }
  const link = document.createElement("a");
  link.href = getNodeResourceUrl(node);
  link.download = node.title;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showNotification("Download started...", { type: "info" });
}

async function downloadFileToFolder(node, options = {}) {
  const fileUrl = getNodeResourceUrl(node);
  try {
    const response = await fetch(fileUrl);
    if (!response.ok) throw new Error(`Failed to fetch file: ${response.statusText}`);

    const blob = await response.blob();
    const fileName = node.title;
    // const fileName = fileUrl.split("/").pop(); // Extract file name from URL

    // Request the user to select a folder
    const handle = await window.showDirectoryPicker();
    const fileHandle = await handle.getFileHandle(fileName, { create: true });

    showNotification("Download started...", { type: "info" });
    // Write the file to the selected folder
    const writable = await fileHandle.createWritable();
    await writable.write(blob);
    await writable.close();
    showNotification("Download ok.", { type: "info" });

    // alert(`File downloaded successfully to ${handle.name}`);
  } catch (error) {
    console.error("Error downloading file:", error);
  }
}

// function supportsDownloadURL() {
//   // 'DownloadURL' is ignored by Safari and Firefox
//   return /Chrome|Chromium|Edg/.test(navigator.userAgent) && !/Firefox|Safari/.test(navigator.userAgent);
// }

export async function addFileToDataTransfer(node, dragStartEvent) {
  if (!isFile(node)) {
    return false;
  }
  const dt = dragStartEvent.dataTransfer;
  const fileUrl = getNodeResourceUrl(node);
  const name = node.title;
  const mime = node.data.mime || "text/plain";

  try {
    dt.setData("DownloadURL", `${mime}:${name}:${fileUrl}`);
  } catch (error) {
    // DownloadURL not supported: use a temporary fetch
    const response = await fetch(fileUrl);
    const blob = await response.blob();
    const file = new File([blob], name, { type: mime });
    dt.effectAllowed = "copy";
    dt.items.add(file);
  }
  return true;
}

/** Drop external file(s) into a directory (use node's parent if node is a file) */
export async function uploadFiles(node, fileArray, options = {}) {
  const { overwrite = false, _isReplacing = false } = options;
  const client = getDAVClient();

  // `node` should be the parent of the uploaded files.
  // We accept either the tree's system root or a directory. If the node is
  // a file, use its parent folder node
  if (isFile(node)) {
    node = node.parent;
  } else if (!isFolder(node) && !isRootFolder(node)) {
    throw new Error("No active directory.");
  }
  const uploadPath = node.getPath();

  // showNotification("Upload started...");
  for (const file of fileArray) {
    try {
      const filePath = `${uploadPath}/${file.name}`;
      const data = await file.arrayBuffer();
      const res = await client.putFileContents(filePath, data, {
        overwrite: overwrite,
      });
      if (res === true) {
        if (_isReplacing) {
          showNotification(`Replaced '${file.name}'.`);
        } else {
          showNotification(`Uploaded '${file.name}'.`);
          if (!node.isUnloaded()) {
            node.addChildren({ title: file.name, type: "file", size: file.size });
          }
        }
      } else if (!overwrite && !_isReplacing) {
        const retry = confirm(`File "${file.name}" already exists. Do you want to overwrite it?`);
        if (retry) {
          await uploadFiles(node, [file], { overwrite: true, _isReplacing: true });
        } else {
          showNotification(`Skipped '${file.name}'.`, { type: "info" });
        }
        // Continue with the remaining files
      } else {
        showNotification(`Failed to upload '${file.name}'.`, { type: "error" });
        console.error("Upload failed: ", res);
      }
    } catch (error) {
      showNotification(`Failed to upload '${file.name}'.`, { type: "error" });
      console.error("Upload error:", error);
    }
  }
}

export async function uploadFilesDialog(node, options = {}) {
  const input = document.createElement("input");
  input.type = "file";
  input.multiple = true;

  input.addEventListener("change", async (event) => {
    const fileArray = event.target.files;
    if (fileArray.length === 0) {
      showNotification("No files selected for upload.", { type: "warning" });
      return false;
    }
    return uploadFiles(node, fileArray, options);
  });
  input.click();
}

export async function createFolder(node, newName, options = {}) {
  if (!isValidResourceName(newName)) {
    showNotification(`Invalid folder name: "${newName}".`, { type: "warning" });
    return false;
  }
  const client = getDAVClient();
  const path = node.getPath();
  const filePath = `${path}/${newName}`;

  try {
    await client.createDirectory(filePath);
    showNotification(`Created folder "${filePath}/".`);
    if (!node.isUnloaded()) {
      // An empty, already loaded folder
      node.addChildren({ title: newName, type: "directory", children: [] });
    }
  } catch (err) {
    if (err.status === 405) {
      showNotification(`Folder "${filePath}" already exists.`, { type: "warning" });
    } else {
      showNotification(`Failed to create folder "${filePath}/": ${err.message}`, { type: "error" });
    }
    console.error("Failed to create folder: ", err);
  }
}

/* --- Dropzone --- */

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");

dropzone.addEventListener("click", () => fileInput.click());

dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropzone.classList.add("dragover");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("dragover");
});

dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("dragover");
  const files = event.dataTransfer.files;
  uploadFiles(getActiveNode() ?? getTree().root, files);
});

fileInput.addEventListener("change", () => {
  const files = fileInput.files;
  uploadFiles(getActiveNode() ?? getTree().root, files);
});
