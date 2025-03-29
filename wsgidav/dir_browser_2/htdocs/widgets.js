"use strict";

import { Wunderbaum } from "./wunderbaum.esm.js";
import { util } from "./util.js";

/**
 * Command Buttons & Palette
 */
export const commandHtmlTemplateFile = `
<span class="command-palette">
    <i class="wb-button bi bi-copy" title="Copy link" data-command="copyUrl"></i>
	<i class="wb-button bi bi-cloud-download" title="Download file..." data-command="download"></i>
	<i class="wb-button bi bi-windows" title="Open in MS-Office" data-command="startOffice"></i>
	<i class="wb-button bi bi-trash3" title="Delete file" data-command="delete"></i>
	<i class="wb-button bi bi-pencil-square" title="Rename file" data-command="rename"></i>
	<i class="wb-button bi bi-unlock" title="File is unlocked" data-command="lock"></i>
</span>
`;
export const commandHtmlTemplateFolder = `
<span class="command-palette">
    <i class="wb-button bi bi-copy disabled" title="Copy link"></i>
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
