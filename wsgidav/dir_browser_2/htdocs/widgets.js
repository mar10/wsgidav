"use strict";

import { Wunderbaum } from "./wunderbaum.esm.js";
import { util, getNodeResourceUrl, getDAVClient, getNodeOrActive, getActiveNode, isFile, isFolder } from "./util.js";

/**
 * Command Buttons & Palette
 */
export const commandHtmlTemplateFile = `
<span class="command-palette">
    <i class="wb-button bi bi-copy" title="Copy link" data-command="copyUrl"></i>
	<i class="wb-button bi bi-cloud-plus disabled" title="Upload file..."></i>
    <i class="wb-button bi bi-folder-plus disabled" title="Create subfolder..."></i>
	<i class="wb-button bi bi-cloud-download" title="Download file..." data-command="download"></i>
	<i class="wb-button bi bi-windows" title="Open in MS-Office" data-command="startOffice"></i>
	<i class="wb-button bi bi-trash3 alert" title="Delete file" data-command="delete"></i>
	<i class="wb-button bi bi-pencil-square" title="Rename file" data-command="rename"></i>
    <!--	<i class="wb-button bi bi-unlock" title="File is unlocked" data-command="lock"></i> -->
    </span>
    `;
export const commandHtmlTemplateFolder = `
    <span class="command-palette">
    <i class="wb-button bi bi-copy disabled" title="Copy link"></i>
	<i class="wb-button bi bi-cloud-plus" title="Upload file to this folder..." data-command="upload"></i>
	<i class="wb-button bi bi-folder-plus" title="Create subfolder..." data-command="newFolder"></i>
	<i class="wb-button bi bi-cloud-download disabled" title="Download folder..."></i>
	<i class="wb-button bi bi-windows disabled" title="Open in MS-Office"></i>
	<i class="wb-button bi bi-trash3 alert" title="Delete folder" data-command="delete"></i>
	<i class="wb-button bi bi-pencil-square" title="Rename folder" data-command="rename"></i>
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
// export function setCommandButton(command, options = {}) {
//     const { pressed = undefined, icon = undefined } = options;
//     const buttonElem = document.querySelector(`.wb-button[data-cmd=${command}]`);
//     console.info("command:", buttonElem);

// }

export async function showNotification(message, options = {}) {
  const durationMap = { info: 5000, warning: 10000, error: 20000 };
  let { type = "info", duration = undefined } = options;
  if (!durationMap[type]) {
    type = "error";
  }
  duration ??= durationMap[type];

  const notification = document.getElementById("notification");
  notification.textContent = message;
  notification.className = `notification ${type}`;
  notification.style.display = "inline";
  return new Promise((resolve) => {
    setTimeout(() => {
      notification.style.display = "none";
      resolve();
    }, duration);
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

function supportsDownloadURL() {
  // 'DownloadURL' is ignored by Safari and Firefox
  return /Chrome|Chromium|Edg/.test(navigator.userAgent) && !/Firefox|Safari/.test(navigator.userAgent);
}

export async function addFileToDataTransfer(node, dragStartEvent) {
  if (!isFile(node)) {
    return false;
  }
  const dt = dragStartEvent.dataTransfer;
  const fileUrl = getNodeResourceUrl(node);
  const name = node.title;
  const mime = node.data.mime || "text/plain";

  if (supportsDownloadURL()) {
    console.info("Drag file using DownloadURL");
    dt.setData("DownloadURL", `${mime}:${name}:${fileUrl}`);
  } else {
    console.warn("Drag file using temporary fetch (DownloadURL not supported)");
    const response = await fetch(fileUrl);
    const blob = await response.blob();
    const file = new File([blob], name, { type: mime });
    dt.effectAllowed = "copy";
    dt.items.add(file);
  }
  return true;
}

/** */
// export async function downloadFile(node, options = {}) {
//     let { dialog = true, allowFolders = true } = options;
//     if (dialog && !("showSaveFilePicker" in window)) {
//         console.warn("Download dialog not available in this browser: using default folder.");
//         dialog = false;
//     }
//     if (!dialog) {
//         const link = document.createElement("a");
//         link.href = getNodeResourceUrl(node);
//         link.download = node.title;
//         document.body.appendChild(link);
//         link.click();
//         document.body.removeChild(link);
//         showNotification("Download started...");
//         return;
//     }
//     // Create a hidden input element for folder selection
//     const input = document.createElement("input");
//     input.type = "file";
//     input.webkitdirectory = allowFolders; // Allow folder selection
//     input.style.display = "none";

//     // Listen for folder selection
//     input.addEventListener("change", async (event) => {
//         const files = event.target.files;
//         if (files.length === 0) {
//             console.warn("No folder selected.");
//             return;
//         }
//         // Get the selected folder path (browser restrictions apply)
//         const folderPath = files[0].webkitRelativePath.split("/")[0];
//         console.log(`Selected folder: ${folderPath}`);

//         // Download the file to the selected folder
//         const fileUrl = getNodeResourceUrl(node); // Get the file's URL
//         const response = await fetch(fileUrl);
//         const blob = await response.blob();
//         showNotification("Download started...");

//         const handle = await window.showSaveFilePicker({
//             suggestedName: node.title,
//         });
//         const writable = await handle.createWritable();
//         await writable.write(blob);
//         await writable.close();
//         console.log(`File downloaded to: ${handle.name}`);
//     });

//     // Trigger the folder selection dialog
//     document.body.appendChild(input);
//     input.click();
//     document.body.removeChild(input);
// }

/** Drop axternal file(s) into a directory (use node's parent if node is a file) */
export async function uploadFiles(node, fileArray, options = {}) {
  const client = getDAVClient();
  const uploadPath = node.getPath();

  // `node` should be the parent of the uploaded files.
  // We accept either the tree's system root or a directory. If the node is
  // a file, use its parent folder node
  if (node.parent != null) {
    if (isFile(node)) node = node.parent;
    if (!isFolder(node)) throw new Error("No active directory.");
  }

  showNotification("Upload started.");
  for (const file of fileArray) {
    try {
      const filePath = `${uploadPath}/${file.name}`;
      const data = await file.arrayBuffer();
      // console.log("data", data);
      // if(client.exists())
      await client.putFileContents(filePath, data, { overwrite: false });
      showNotification(`Uploaded '${file.name}' successfully.`);
      if (!node.isUnloaded()) {
        node.addChildren({ title: file.name, type: "file", size: file.size });
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

export async function deleteResource(node, options = {}) {
  try {
    await getDAVClient().deleteFile(node.getPath());
    showNotification(`Deleted "/${node.getPath()}".`);
    node.remove();
  } catch (e) {
    showNotification("Failed to delete.", { type: "error" });
    console.error("Failed to delete: ", err);
  }
}

export async function createFolder(node, newName, options = {}) {
  const client = getDAVClient();
  const path = node.getPath();

  const filePath = `${path}/${newName}`;
  await client.createDirectory(filePath);
  showNotification(`Created "${filePath}/".`);
  if (!node.isUnloaded()) {
    node.addChildren({ title: newName, type: "directory" });
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
  uploadFiles(getActiveNode(), files);
});

fileInput.addEventListener("change", () => {
  const files = fileInput.files;
  uploadFiles(getActiveNode(), files);
});
