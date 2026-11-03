"use strict";

// import { Wunderbaum } from "./wunderbaum.esm.js";
import { Wunderbaum } from "https://esm.run/wunderbaum@0.14";

import { config, getDAVClient, util, getNodeResourceUrl, getTree, isFile, isFolder, parseDateToTimestamp, settingsStore } from "./util.js";
import { getFileIcon, getFileInfo, getOfficeUrlPrefix, showPreview, togglePreviewPane, updateNodePreviewInfo } from "./previews.js";
import { addFileToDataTransfer, commandHtmlTemplateFile, commandHtmlTemplateFolder, createFolder, downloadFile, registerCommandButtons, showNotification, uploadFiles, uploadFilesDialog } from "./widgets.js";

let _wb_clipboard_node = null;
let _wb_clipboard_is_cut = null;

/**
 * Open an MS Office/LibreOffice document the 'ms-' protocol scheme.
 *
 * @param {object} opts
 * @returns {boolean} true if the URL could be opened
 */ function openDocument(node, options = {}) {
  const { readonly = config.readonly, officeSupport = settingsStore.get("office_support") } = options;
  const info = node ? getFileInfo(node.title) : null;
  if (!info || !isFile(node)) {
    return false;
  }
  let url = getOfficeUrlPrefix(node, { readonly: readonly });
  console.log("Open %s...", url);
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
      res.title = res.basename;
      delete res.basename;
      if (res.type === "directory") res.lazy = true;
      // Convert 'Mon, 07 Apr 2025 19:46:35 GMT' to a unix timestamp
      res.lastmod = parseDateToTimestamp(res.lastmod);
      nodeList.push(res);
    }
    // console.info("getDirectoryContents", nodeList);
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
  if (confirm(`Delete '${node.getPath()}' from the server?\n\nThis cannot be undone!`)) {
    getDAVClient()
      .deleteFile(node.getPath())
      .then(() => {
        node.remove();
      })
      .catch((err) => {
        showNotification(`Failed to delete "${node.getPath()}": ${err.message}`, { type: "error" });
        console.error("Failed to delete: ", err);
      });
  }
}

async function copyMoveNode(sourceNode, targetNode, isCopy, asChild, rename) {
  const client = getDAVClient();
  if (!isCopy && targetNode.isDescendantOf(sourceNode)) {
    showNotification(`Cannot move a node into its own descendant.`, { type: "warning" });
    return false;
  }
  const sourcePath = sourceNode.getPath();
  const targetParent = asChild ? targetNode : targetNode.parent;
  let targetPath = targetParent.getPath() + "/" + sourceNode.title;
  const targetExists = await client.exists(targetPath);
  let newTitle = sourceNode.title;
  if (targetExists) {
    const [title, ext] = sourceNode.title.split(/\.(?=[^\.]+$)/);
    if (isCopy && !asChild && rename) {
      newTitle = `Copy of ${sourceNode.title}`;

      let exists = true;
      let i = 1;
      while (exists) {
        exists = targetParent.children.some((sibling) => sibling.title === newTitle);
        if (exists) {
          i++;
          newTitle = `Copy of ${title} ${i}${ext ? "." + ext : ""}`;
        }
      }
      targetPath = targetParent.getPath() + "/" + newTitle;
    } else {
      if (!window.confirm(`Overwrite ${targetPath}?`)) {
        showNotification(`Operation cancelled.`, { type: "warning" });
        return false;
      }
      // overwrite the existing target
    }
  }
  if (isCopy) {
    await client
      .copyFile(sourcePath, targetPath)
      .then(() => {
        targetNode.addNode({ title: newTitle, type: sourceNode.type, size: sourceNode.size }, asChild ? "appendChild" : "after");
        showNotification(`Copied ${sourcePath} to ${targetPath}.`, { type: "info" });
      })
      .catch((err) => {
        showNotification(`Failed to copy ${sourcePath} to ${targetPath}: ${err.message}`, { type: "error" });
        return false;
      });
  } else {
    await client
      .moveFile(sourcePath, targetPath)
      .then(() => {
        sourceNode.moveTo(targetNode, asChild ? "appendChild" : "after");
        showNotification(`Moved ${sourcePath} to ${targetPath}.`, { type: "info" });
      })
      .catch((err) => {
        showNotification(`Failed to move ${sourcePath} to ${targetPath}: ${err.message}`, { type: "error" });
        return false;
      });
  }

  if (targetExists) {
    targetNode.loadLazy(true);
  }
  return true;
}

const _tree = new Wunderbaum({
  element: "div#tree",
  debugLevel: 5,
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
    if (isFile(e.node)) {
      openDocument(e.node);
    }
  },
  edit: {
    trigger: ["clickActive", "F2", "macEnter"],
    apply: (e) => {
      const newValue = e.newValue;
      const sourcePath = e.node.getPath();
      const parentPath = e.node.parent ? e.node.parent.getPath() : "/";
      const targetPath = parentPath.endsWith("/") ? parentPath + newValue : parentPath + "/" + newValue;
      e.node.logInfo(`Move to ${newValue}`);
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
    console.log(`Keydown event: ${e.eventName}`);
    switch (e.eventName) {
      case "Meta+Backspace":
      case "Delete":
        deleteNode(e.tree.getActiveNode());
        break;
      case "Escape":
        _wb_clipboard_node = _wb_clipboard_is_cut = null;
        break;
      case "Command+c":
      case "Control+c":
        _wb_clipboard_node = e.tree.getActiveNode();
        _wb_clipboard_is_cut = false;
        break;
      case "Control+x":
        _wb_clipboard_node = e.tree.getActiveNode();
        _wb_clipboard_is_cut = true;
        break;
      case "Alt+Command+v":
      case "Command+v":
        _wb_clipboard_is_cut = !!e.event.altKey;
      // fall through to handle the paste operation
      case "Control+v":
        if (_wb_clipboard_node) {
          const targetNode = e.tree.getActiveNode();
          const asChild = targetNode.type === "directory";
          copyMoveNode(_wb_clipboard_node, targetNode, !_wb_clipboard_is_cut, asChild, true);
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
      console.log(e.type, e);
      addFileToDataTransfer(e.node, e.event);
      return true;
    },
    dragEnter: (e) => {
      // console.log(e.type, e);
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
      console.log(e.type, e, dataTransfer.items?.length);
      if (e.sourceNode) {
        // copy/move a node inside the tree
        const asChild = node.type === "directory" && e.region === "over";
        switch (e.suggestedDropEffect) {
          case "copy":
            copyMoveNode(e.sourceNode, node, true, e.suggestedDropMode, asChild);
            break;
          default:
            copyMoveNode(e.sourceNode, node, false, e.suggestedDropMode, asChild);
            break;
        }
      } else if (dataTransfer.items && dataTransfer.items.length) {
        // drop an external file onto the tree
        const fileArray = [];
        [...dataTransfer.items].forEach((item, i) => {
          if (item.kind === "file") {
            const file = item.getAsFile();
            fileArray.push(file);
          }
        });
        uploadFiles(e.node, fileArray);
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
  console.info("got", `${node}`, e.command, e);
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
    case "newFolder":
      const promptText = node.isRootNode() ? "Name of the new toplevel folder" : `Name of the new subfolder of\n '${node.getPath() + "/"}'`;
      const newName = prompt(promptText, "New Folder");
      if (newName) {
        createFolder(node, newName);
      }
      break;
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
