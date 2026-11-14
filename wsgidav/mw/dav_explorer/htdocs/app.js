"use strict";

import { Wunderbaum, config, getDAVClient, util, getNodeResourceUrl, getTree, isFile, isFolder, isIgnored, isValidResourceName, parseDateToTimestamp, settingsStore } from "./util.js";
import { getFileIcon, getFileInfo, getOfficeUrlPrefix, showPreview, togglePreviewPane, updateNodePreviewInfo } from "./previews.js";
import { addFileToDataTransfer, commandHtmlTemplateFile, commandHtmlTemplateFolder, createFolder, downloadFile, registerCommandButtons, showNotification, uploadFiles, uploadFilesDialog } from "./widgets.js";

// Commands that modify server data are rejected in readonly mode
const WRITE_COMMANDS = new Set(["delete", "newFolder", "newTopFolder", "rename", "upload", "uploadTop"]);

let _wb_clipboard_node = null;
let _wb_clipboard_is_cut = null;

/**
 * Open an MS Office/LibreOffice document the 'ms-' protocol scheme.
 *
 * @param {object} opts
 * @returns {boolean} true if the URL could be opened
 */
function openDocument(node, options = {}) {
  const {
    // Server-side readonly mode always wins over the user setting
    readonly = config.readonly || settingsStore.get("office_readonly"),
    officeSupport = settingsStore.get("office_support"),
  } = options;
  const info = node ? getFileInfo(node.title) : null;
  if (!info || !isFile(node)) {
    return false;
  }
  let url = getOfficeUrlPrefix(node, { readonly: readonly });
  if (officeSupport && url) {
    showNotification(`Opening ${node.title} in Office`, { type: "info" });
    return window.open(url, "_self");
  } else {
    url = getNodeResourceUrl(node);
    return window.open(url, "_blank");
  }
}

async function loadWbResources(options = {}) {
  options = Object.assign({ path: "/", details: false }, options);
  const client = getDAVClient();

  try {
    const resList = await client.getDirectoryContents(options.path, options);

    const nodeList = [];
    for (let res of resList) {
      if (isIgnored(res.basename)) {
        continue;
      }
      res.title = res.basename;
      delete res.basename;
      if (res.type === "directory") res.lazy = true;
      // Convert 'Mon, 07 Apr 2025 19:46:35 GMT' to a unix timestamp
      res.lastmod = parseDateToTimestamp(res.lastmod);
      nodeList.push(res);
    }
    return nodeList;
  } catch (err) {
    console.error("Error loading resources:", err);
    showNotification(`Failed to load resources: ${err.message}`, { type: "error" });
    throw err;
  }
}

const commandBarFile = util.elemFromHtml(commandHtmlTemplateFile);
const commandBarFolder = util.elemFromHtml(commandHtmlTemplateFolder);

async function deleteNode(node) {
  if (!node || node.isRootNode()) {
    return false;
  }
  const path = node.getPath();
  if (!confirm(`Delete '${path}' from the server?\n\nThis cannot be undone!`)) {
    return false;
  }
  try {
    await getDAVClient().deleteFile(path);
    node.remove();
    showNotification(`Deleted "${path}".`, { type: "info" });
    return true;
  } catch (err) {
    showNotification(`Failed to delete "${path}": ${err.message}`, { type: "error" });
    console.error("Failed to delete: ", err);
    return false;
  }
}

function joinPath(parentPath, name) {
  return parentPath.endsWith("/") ? parentPath + name : parentPath + "/" + name;
}

/**
 * Copy or move `sourceNode` next to (or into, if `asChild`) `targetNode`.
 *
 * If the target exists, the user is asked to overwrite it, unless `rename` is
 * set for a copy into the same folder, in which case 'Copy of ...' is used.
 */
async function copyMoveNode(sourceNode, targetNode, isCopy, asChild, rename = false) {
  const client = getDAVClient();
  if (!sourceNode || !targetNode) {
    return false;
  }
  if (!isCopy && (targetNode === sourceNode || targetNode.isDescendantOf(sourceNode))) {
    showNotification(`Cannot move a node into itself or its own descendant.`, { type: "warning" });
    return false;
  }
  const sourcePath = sourceNode.getPath();
  const targetParent = asChild ? targetNode : targetNode.parent;
  let newTitle = sourceNode.title;
  let targetPath = joinPath(targetParent.getPath(), newTitle);
  let overwrite = false;

  try {
    if (await client.exists(targetPath)) {
      if (isCopy && rename && targetParent === sourceNode.parent) {
        // Copy into the same folder: find a free 'Copy of ...' name
        const [title, ext] = sourceNode.title.split(/\.(?=[^.]+$)/);
        newTitle = `Copy of ${sourceNode.title}`;
        for (let i = 2; await client.exists(joinPath(targetParent.getPath(), newTitle)); i++) {
          newTitle = `Copy of ${title} ${i}${ext ? "." + ext : ""}`;
        }
        targetPath = joinPath(targetParent.getPath(), newTitle);
      } else if (window.confirm(`Overwrite ${targetPath}?`)) {
        overwrite = true;
      } else {
        showNotification(`Operation cancelled.`, { type: "warning" });
        return false;
      }
    }
    if (isCopy) {
      await client.copyFile(sourcePath, targetPath, { overwrite: overwrite });
    } else {
      await client.moveFile(sourcePath, targetPath, { overwrite: overwrite });
    }
  } catch (err) {
    const op = isCopy ? "copy" : "move";
    showNotification(`Failed to ${op} ${sourcePath} to ${targetPath}: ${err.message}`, { type: "error" });
    console.error(`Failed to ${op}: `, err);
    return false;
  }

  // Update the tree
  if (overwrite) {
    // The target node already exists: re-sync the parent from the server
    // (this also removes `sourceNode` if it was moved inside that folder)
    if (!isCopy) {
      sourceNode.remove();
    }
    if (targetParent.isRootNode()) {
      getTree().reload({ source: loadWbResources() });
    } else {
      await targetParent.loadLazy(true);
    }
  } else if (isCopy) {
    const data = { title: newTitle, type: sourceNode.type, size: sourceNode.data.size, lastmod: sourceNode.data.lastmod, mime: sourceNode.data.mime };
    if (isFolder(sourceNode)) {
      data.lazy = true;
    }
    if (!asChild || !targetNode.isUnloaded()) {
      targetNode.addNode(data, asChild ? "appendChild" : "after");
    }
  } else if (asChild && targetNode.isUnloaded()) {
    // Target folder will show the node when it is expanded
    sourceNode.remove();
  } else {
    sourceNode.moveTo(targetNode, asChild ? "appendChild" : "after");
  }
  const verb = isCopy ? "Copied" : "Moved";
  showNotification(`${verb} ${sourcePath} to ${targetPath}.`, { type: "info" });
  return true;
}

const _tree = new Wunderbaum({
  element: "div#tree",
  debugLevel: 1,
  types: {},
  columns: [
    { id: "*", title: "Path", width: 2 },
    { id: "commands", title: "Commands", width: "190px", sortable: false },
    { id: "type", title: "Type", width: "100px" },
    { id: "size", title: "Size", width: "80px", classes: "wb-helper-end" },
    { id: "lastmod", title: "Modified", width: "150px", classes: "wb-helper-end" },
    // {id: "etag", title: "ETag", width: "80px" },
    { id: "mime", title: "Mime Type", width: 1 },
  ],
  autoKeys: true,
  columnsResizable: true,
  columnsSortable: true,
  sortFoldersFirst: true,
  navigationModeOption: "row",
  emptyChildListExpandable: true,
  connectTopBreadcrumb: "output#parentPath",

  icon: (e) => {
    return getFileIcon(e.node.title);
  },

  source: loadWbResources(),

  init: function (e) {
    e.tree.sort({ colId: "*", updateColInfo: true });
    e.tree.setFocus();
    togglePreviewPane(settingsStore.get("showInfoPane") ?? true);
  },
  load: function (e) {
    // When loading a lazy branch, apply current sort order if any
    e.node.resort();
  },
  lazyLoad: function (e) {
    const path = e.node.getPath();
    return loadWbResources({ path: path });
  },
  expand: function (e) {
    updateNodePreviewInfo(e.node);
  },
  buttonClick: (e) => {
    if (e.command === "sort") {
      e.tree.sort({ colId: e.info.colId, updateColInfo: true });
    }
  },
  activate: (e) => {
    showPreview(e.node);
  },
  dblclick: (e) => {
    const node = e.node;
    if (isFile(node)) {
      switch (settingsStore.get("dblclick_action")) {
        case "download":
          downloadFile(node);
          break;
        case "nothing":
          break;
        default:
          openDocument(node);
      }
    } else if (isFolder(node) && settingsStore.get("dblclick_action_folders") === "set_root") {
      window.location.href = getNodeResourceUrl(node) + "/";
      return false;
    }
  },
  edit: {
    trigger: config.readonly ? [] : ["clickActive", "F2", "macEnter"],
    apply: (e) => {
      const newValue = e.newValue;
      if (!isValidResourceName(newValue)) {
        throw new util.ValidationError(`Invalid name: "${newValue}"`);
      }
      const sourcePath = e.node.getPath();
      const parentPath = e.node.parent ? e.node.parent.getPath() : "/";
      const targetPath = joinPath(parentPath, newValue);
      return getDAVClient()
        .moveFile(sourcePath, targetPath)
        .catch((err) => {
          showNotification(`Failed to rename "${sourcePath}" to "${targetPath}": ${err.message}`, { type: "error" });
          console.error("Failed to rename: ", err);
          throw err;
        });
    },
  },
  keydown: (e) => {
    const activeNode = e.tree.getActiveNode();
    switch (e.eventName) {
      case "Meta+Backspace":
      case "Delete":
        if (activeNode && !config.readonly) {
          deleteNode(activeNode);
        }
        break;
      case "Escape":
        _wb_clipboard_node = _wb_clipboard_is_cut = null;
        break;
      case "Meta+c":
      case "Control+c":
        _wb_clipboard_node = activeNode;
        _wb_clipboard_is_cut = false;
        break;
      case "Meta+x":
      case "Control+x":
        _wb_clipboard_node = activeNode;
        _wb_clipboard_is_cut = true;
        break;
      case "Meta+v":
      case "Control+v":
        if (_wb_clipboard_node && activeNode && !config.readonly) {
          const asChild = isFolder(activeNode);
          const isCut = _wb_clipboard_is_cut;
          copyMoveNode(_wb_clipboard_node, activeNode, !isCut, asChild, true);
          if (isCut) {
            // A moved node cannot be pasted a second time
            _wb_clipboard_node = _wb_clipboard_is_cut = null;
          }
        }
        break;
    }
  },
  render: function (e) {
    const node = e.node;
    const isDir = node.type === "directory";

    for (const col of Object.values(e.renderColInfosById)) {
      switch (col.id) {
        case "type":
          col.elem.textContent = node.type;
          break;
        case "commands":
          // <a href="ms-word:ofe|u|http://some_WebDav_enabled_address.com/some_Word_document.docx">Open Document in Word</a>
          // https://stackoverflow.com/a/25765784/19166
          if (e.isNew) {
            const cmdBar = isDir ? commandBarFolder : commandBarFile;
            col.elem.appendChild(cmdBar.cloneNode(true));
          }
          break;
        case "size":
          col.elem.textContent = isDir ? "" : node.data.size?.toLocaleString();
          break;
        case "lastmod":
          col.elem.textContent = node.data.lastmod ? new Date(node.data.lastmod).toLocaleString() : "n.a.";
          break;
        default:
          // Assumption: we named column.id === node.data.NAME
          col.elem.textContent = node.data[col.id];
          break;
      }
    }
  },
  dnd: {
    dragStart: (e) => {
      addFileToDataTransfer(e.node, e.event);
      return true;
    },
    dragEnter: (e) => {
      if (config.readonly) {
        return false;
      }
      if (e.node.parent === e.sourceNode?.parent) {
        return isFolder(e.node) ? "over" : false;
      }
      if (isFolder(e.node)) {
        return true;
      }
      return ["before", "after"];
    },
    drop: (e) => {
      const node = e.node;
      const dataTransfer = e.event.dataTransfer;
      if (e.sourceNode) {
        // copy/move a node inside the tree
        const asChild = isFolder(node) && e.region === "over";
        copyMoveNode(e.sourceNode, node, e.suggestedDropEffect === "copy", asChild);
      } else if (dataTransfer.items && dataTransfer.items.length) {
        // drop an external file onto the tree
        const fileArray = [...dataTransfer.items].filter((item) => item.kind === "file").map((item) => item.getAsFile());
        uploadFiles(node, fileArray);
      }
    },
  },
});

const THEME_MODES = ["auto", "light", "dark"];
const THEME_ICONS = { auto: "bi-circle-half", light: "bi-sun", dark: "bi-moon-stars" };
const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");

function applyTheme(mode) {
  const dark = mode === "dark" || (mode === "auto" && darkQuery.matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  const btn = document.querySelector('.wb-button[data-command="toggleTheme"]');
  if (btn) {
    btn.classList.remove(...Object.values(THEME_ICONS));
    btn.classList.add(THEME_ICONS[mode]);
    btn.dataset.themeMode = mode;
    btn.title = `Theme: ${mode} (click to change)`;
  }
}

function getThemeMode() {
  const mode = localStorage.getItem("dav-explorer-theme");
  return THEME_MODES.includes(mode) ? mode : "auto";
}

applyTheme(getThemeMode());
darkQuery.addEventListener("change", () => applyTheme(getThemeMode()));

registerCommandButtons("body", (e) => {
  let node = e.node;
  if (config.readonly && WRITE_COMMANDS.has(e.command)) {
    return;
  }
  switch (e.command) {
    case "togglePreview":
      togglePreviewPane(e.isPressed);
      if (e.isPressed) {
        showPreview(node);
      } else {
        showPreview(null);
      }
      break;
    case "toggleTheme": {
      const next = THEME_MODES[(THEME_MODES.indexOf(getThemeMode()) + 1) % THEME_MODES.length];
      localStorage.setItem("dav-explorer-theme", next);
      applyTheme(next);
      break;
    }
    case "showHelp":
      showPreview(config.htdocs + "/help.html", { autoOpen: true, iframe: true });
      break;
    case "showSettings":
      showPreview("settings", { autoOpen: true });
      break;
    case "rename":
      node.startEditTitle();
      break;
    case "reloadTree":
      getTree().reload({ source: loadWbResources() });
      break;
    case "newTopFolder":
      node = getTree().root;
    // fall through
    case "newFolder": {
      const promptText = node.isRootNode() ? "Name of the new toplevel folder" : `Name of the new subfolder of\n '${node.getPath() + "/"}'`;
      const newName = prompt(promptText, "New Folder");
      if (newName) {
        createFolder(node, newName);
      }
      break;
    }
    case "delete":
      deleteNode(node);
      break;
    case "uploadTop":
      node = getTree().root;
    // fall through
    case "upload":
      uploadFilesDialog(node);
      break;
    case "startOffice":
      openDocument(node);
      break;
    case "download":
      downloadFile(node);
      break;
    case "copyUrl":
      navigator.clipboard
        .writeText(getNodeResourceUrl(node))
        .then(() => {
          showNotification("URL copied to clipboard.", { type: "info" });
        })
        .catch((err) => {
          showNotification("Failed to copy URL.", { type: "error" });
          console.error("Failed to copy URL: ", err);
        });
      break;
  }
});

document.getElementById("resetSettings").addEventListener("click", () => {
  // Keep UI state that is not part of the settings form
  const showInfoPane = settingsStore.get("showInfoPane");
  settingsStore.reset({ ...settingsStore.opts.defaults, showInfoPane: showInfoPane });
  settingsStore.writeToForm();
  showNotification("Settings were reset to defaults.", { type: "info" });
});
