"use strict";

import { Wunderbaum, util, getNodeResourceUrl, getDAVClient, getActiveNode, getTree, isFile, isFolder, isRootFolder, isValidResourceName } from "./util.js";

/**
 * Command Buttons & Palette
 */
// Buttons marked with `data-write` are hidden in readonly mode (see app.css)
export const commandHtmlTemplateFile = `
<span class="command-palette">
  <i class="wb-button bi bi-copy" title="Copy link" data-command="copyUrl"></i>
  <i class="wb-button bi bi-cloud-plus disabled" title="Upload file..." data-write></i>
  <i class="wb-button bi bi-folder-plus disabled" title="Create subfolder..." data-write></i>
  <i class="wb-button bi bi-cloud-download" title="Download file..." data-command="download"></i>
  <i class="wb-button bi bi-windows" title="Open in MS-Office" data-command="startOffice"></i>
  <i class="wb-button bi bi-trash3 alert" title="Delete file" data-command="delete" data-write></i>
  <i class="wb-button bi bi-pencil-square" title="Rename file" data-command="rename" data-write></i>
</span>
`;
export const commandHtmlTemplateFolder = `
<span class="command-palette">
  <i class="wb-button bi bi-copy" title="Copy link" data-command="copyUrl"></i>
  <i class="wb-button bi bi-cloud-plus" title="Upload file to this folder..." data-command="upload" data-write></i>
  <i class="wb-button bi bi-folder-plus" title="Create subfolder..." data-command="newFolder" data-write></i>
  <i class="wb-button bi bi-cloud-download disabled" title="Download folder..."></i>
  <i class="wb-button bi bi-windows disabled" title="Open in MS-Office"></i>
  <i class="wb-button bi bi-trash3 alert" title="Delete folder" data-command="delete" data-write></i>
  <i class="wb-button bi bi-pencil-square" title="Rename folder" data-command="rename" data-write></i>
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
