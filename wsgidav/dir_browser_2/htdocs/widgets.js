"use strict";

import { Wunderbaum } from "./wunderbaum.esm.js";
import { util, getNodeResourceUrl, getDAVClient } from "./util.js";

/**
 * Command Buttons & Palette
 */
export const commandHtmlTemplateFile = `
<span class="command-palette">
    <i class="wb-button bi bi-copy" title="Copy link" data-command="copyUrl"></i>
	<i class="wb-button bi bi-cloud-plus disabled" title="Upload file..."></i>
    <i class="wb-button bi bi-folder-plus disabled" title="Creat subfolder..."></i>
	<i class="wb-button bi bi-cloud-download" title="Download file..." data-command="download"></i>
	<i class="wb-button bi bi-windows" title="Open in MS-Office" data-command="startOffice"></i>
	<i class="wb-button bi bi-trash3" title="Delete file" data-command="delete"></i>
	<i class="wb-button bi bi-pencil-square" title="Rename file" data-command="rename"></i>
    <!--	<i class="wb-button bi bi-unlock" title="File is unlocked" data-command="lock"></i> -->
    </span>
    `;
export const commandHtmlTemplateFolder = `
    <span class="command-palette">
    <i class="wb-button bi bi-copy disabled" title="Copy link"></i>
	<i class="wb-button bi bi-cloud-plus" title="Upload file to this folder..." data-command="upload"></i>
	<i class="wb-button bi bi-folder-plus" title="Creat subfolder..." data-command="newFolder"></i>
	<i class="wb-button bi bi-cloud-download disabled" title="Download folder..."></i>
	<i class="wb-button bi bi-windows disabled" title="Open in MS-Office"></i>
	<i class="wb-button bi bi-trash3" title="Delete folder" data-command="delete"></i>
	<i class="wb-button bi bi-pencil-square" title="Rename folder" data-command="rename"></i>
</span>
`;

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
    const { type = "info", duration = 5000 } = options;
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

export async function downloadFile(node, options = {}) {
    const link = document.createElement("a");
    link.href = getNodeResourceUrl(node);
    link.download = node.title;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showNotification("Download started.", { type: "info" });

}

export async function uploadFiles(node, options = {}) {
    const input = document.createElement("input");
    input.type = "file";
    input.multiple = true;

    input.addEventListener("change", async (event) => {
        const files = event.target.files;
        if (files.length === 0) {
            showNotification("No files selected for upload.", { type: "warning" });
            return;
        }

        const client = getDAVClient();
        const uploadPath = node.getPath();

        for (const file of files) {
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
    });

    input.click();
    showNotification("Upload started.");
}