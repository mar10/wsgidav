"use strict";

import { Wunderbaum } from "./wunderbaum.esm.js";
import { util } from "./util.js";

/**
 * Command Buttons & Palette
 */
class ActionButton {
  constructor(command, options = {}) {
    this.command = command;
    this.pressed = !!options.pressed;
    this.disabled = !!options.disabled;
    this.hidden = !!options.hidden;  
  }
}

class ActionButtonBar {
  constructor() {
    this.buttons = {};
  }

  addButton(action) {
    this.buttons[action.command] = action;
  }

  getButton(command) {
    return this.buttons[command] || null;
  }
}

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

/** Register a common handler for all command buttons */
export function registerCommandButtons(parent, handler) {
  const tree = Wunderbaum.getTree();
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
      tree: tree,
      node: Wunderbaum.getNode(target),
      target: target,
    });
    return res;
  });
}

export function setCommandButton(command, options = {}) {
  const { pressed = undefined, icon = undefined, title = undefined, enabled = undefined } = options;
  const buttonElem = document.querySelector(`.wb-button[data-command=${command}]`);
  if (pressed !== undefined && buttonElem.classList.contains("wb-button-toggle")) {
    buttonElem.classList.toggle("wb-pressed", pressed);
  }
  if (icon !== undefined) {
    buttonElem.classList.toggle("bi-" + icon, true);
  }
  if (title !== undefined) {
    buttonElem.setAttribute("title", title);
  }
  if (enabled !== undefined) {
    buttonElem.classList.toggle("disabled", !enabled);
  }
  console.info("command:", command, buttonElem);
}

export function pressCommandButtonGroup(groupCommands, command, options = {}) {
  const { enabled = undefined } = options;
  groupCommands.forEach((cmd) => {
    const buttonElem = document.querySelector(`.wb-button[data-command=${cmd}]`);
    if (pressed !== undefined && buttonElem.classList.contains("wb-button-toggle")) {
      buttonElem.classList.toggle("wb-pressed", pressed);
    }
  });
  console.info("command:", command, buttonElem);
}

