"use strict";

import { Wunderbaum } from "./wunderbaum.esm.js";
// import { Wunderbaum } from "https://esm.run/wunderbaum@0.14";
// /** @type {import("https://cdn.jsdelivr.net/npm/wunderbaum@0.13.0/dist/wunderbaum.d.ts")} */

// import {foo} from "https://www.jsdelivr.com/package/npm/pdfjs-dist";
import {
	getDAVClient, util,
	getNodeResourceUrl,
	getTree,
	isFile,
	isFolder,
	parseDateToTimestamp,
} from "./util.js";
import {
	getFileIcon,
	getFileInfo,
	getOfficeUrlPrefix,
	showPreview,
	togglePreviewPane,
} from "./previews.js";
import {
	addFileToDataTransfer,
	commandHtmlTemplateFile,
	commandHtmlTemplateFolder,
	createFolder,
	downloadFile,
	registerCommandButtons,
	showNotification,
	uploadFiles,
	uploadFilesDialog,
} from "./widgets.js";


const davExplorerOptions = {
	showInfoPane: true, // Show the info pane on the right side
	maxPreviewSize: 500 * 1024, // 500 KiB;
	assumeOffice: true, // Assume that clients have MS/LibreOffice installed
	readonlyOffice: false, // Open Office documents in readonly mode by default
}

/**
 * Open an MS Office/LibreOffice document the 'ms-' protocol scheme.
 *
 * @param {object} opts
 * @returns {boolean} true if the URL could be opened
 */;
function openDocument(node, options = {}) {
	const { readonly = false } = options;
	const info = node ? getFileInfo(node.title) : null;
	if (!info || !isFile(node)) {
		return false;
	}
	let url = getOfficeUrlPrefix(node, { readonly: readonly });
	if (url) {
		showNotification(`Opening ${node.title} in Office`, { type: "info" });
	} else {
		url = getNodeResourceUrl(node);
	}
	console.log("Open %s...", url);
	return window.open(url, "_self");
}

async function loadWbResources(options = {}) {
	options = Object.assign({ path: "/", details: false }, options);
	const client = getDAVClient();

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
}

const commandBarFile = util.elemFromHtml(commandHtmlTemplateFile);
const commandBarFolder = util.elemFromHtml(commandHtmlTemplateFolder);

const _tree = new Wunderbaum({
	element: "div#tree",
	debugLevel: 5,
	types: {},
	columns: [
		{ id: "*", title: "Path", width: 2 },
		{ id: "commands", title: " ", width: "140px", sortable: false },
		{ id: "type", title: "Type", width: "100px" },
		{ id: "size", title: "Size", width: "80px", classes: "wb-helper-end" },
		{ id: "lastmod", title: "Modified", width: "150px", classes: "wb-helper-end" },
		// {id: "etag", title: "ETag", width: "80px" },
		{ id: "mime", title: "Mime", width: 1 },
	],
	autoKeys: true,
	columnsResizable: true,
	columnsSortable: true,
	sortFoldersFirst: true,
	navigationModeOption: "row",
	emptyChildListExpandable: true,

	icon: (e) => {
		return getFileIcon(e.node.title);
	},

	source: loadWbResources(),

	init: function (e) {
		e.tree.sort({ colId: "*", updateColInfo: true });
		e.tree.setFocus();
		togglePreviewPane(true);
	},
	load: function (e) {
		// Whe loading a lazy branch, apply current sort order if any
		e.node.resort();
	},
	lazyLoad: function (e) {
		const path = e.node.getPath();
		return loadWbResources({ path: path });
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
		if (isFile(e.node)) { openDocument(e.node); }
	},
	edit: {
		trigger: ["clickActive", "F2", "macEnter"],
		apply: (e) => {
			const oldValue = e.oldValue;
			const newValue = e.newValue;
			e.node.logInfo(`Move to ${newValue}`);
			return getDAVClient().moveFile(oldValue, newValue);
		},
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
					col.elem.textContent = isDir ? "" : node.data.size.toLocaleString();
					break;
				case "lastmod":
					col.elem.textContent = new Date(node.data.lastmod).toLocaleString();
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
				const sourcePath = e.sourceNode.getPath();
				let targetPath;
				if (node.type === "directory" && e.suggestedDropMode === "over") {
					targetPath = node.getPath() + "/" + e.sourceNode.title;
				} else {
					targetPath = node.parent.getPath() + "/" + e.sourceNode.title;
				}
				console.log(e.type, `${e.suggestedDropEffect} ${sourcePath} -> ${targetPath} `, e);
				switch (e.suggestedDropEffect) {
					case "copy":
						getDAVClient().copyFile(sourcePath, targetPath).then(() => {
							node.addNode(
								{ title: `${e.sourceNodeData.title}` },
								e.suggestedDropMode
							);
						});
						break;
					default:
						getDAVClient().moveFile(sourcePath, targetPath).then(() => {
							e.sourceNode.moveTo(node, e.suggestedDropMode);
						});
				}
			} else if (dataTransfer.items && dataTransfer.items.length) {
				// drop an external file onto the tree
				const fileArray = [];
				[...dataTransfer.items].forEach((item, i) => {
					if (item.kind === "file") {
						const file = item.getAsFile();
						// console.log(`  - file[${i}].name = ${file.name} `);
						fileArray.push(file);
					}
				});
				uploadFiles(e.node, fileArray);
			}
		},
	},
});

registerCommandButtons("body", (e) => {
	let node = e.node;
	console.info("got", `${node}`, e.command, e);
	switch (e.command) {
		case "togglePreview":
			togglePreviewPane(e.isPressed);
			if (e.isPressed) { showPreview(node); } else { showPreview(null); }
			break;
		case "showHelp":
			showPreview(":dir_browser/help.html", { autoOpen: true, iframe: true });
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
			const newName = prompt(`Enter the name of the new subfolder of\n '${node.getPath() + "/"}'`);
			if (newName) {
				createFolder(node, newName);
			}
			break;
		case "delete":
			if (confirm(`Delete '${node.getPath()}' from the server?\n\nThis cannot be undone!`)) {
				getDAVClient().deleteFile(node.getPath()).then(() => {
					node.remove();
				});
			}
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
			navigator.clipboard.writeText(getNodeResourceUrl(node))
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
