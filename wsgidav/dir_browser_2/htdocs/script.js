"use strict";

import { Wunderbaum } from "./wunderbaum.esm.js";
// import { Wunderbaum } from "https://esm.run/wunderbaum@0.14";
// /** @type {import("https://cdn.jsdelivr.net/npm/wunderbaum@0.13.0/dist/wunderbaum.d.ts")} */
import { Toast } from "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/+esm";

// import {foo} from "https://www.jsdelivr.com/package/npm/pdfjs-dist";
import { getNodeResourceUrl, getDAVClient, util } from "./util.js";
import { fileTypeIcons, showPreview, togglePreviewPane } from "./previews.js";
import { registerCommandButtons, commandHtmlTemplateFile, commandHtmlTemplateFolder, downloadFile, uploadFiles, showNotification } from "./widgets.js";

// Cached plugin reference (or null. if it could not be instantiated)
let sharePointPlugin = undefined;

/**
 * Find (and cache) an available ActiveXObject Sharepoint plugin.
 *
 * @returns {ActiveXObject} or null
	*/
function getSharePointPlugin() {
	if (sharePointPlugin !== undefined) {
		return sharePointPlugin;
	}
	sharePointPlugin = null;

	var plugin = document.getElementById("winFirefoxPlugin");

	if (plugin && typeof plugin.EditDocument === "function") {
		window.console && console.log("Using embedded custom SharePoint plugin.");
		sharePointPlugin = plugin;
	} else if ("ActiveXObject" in window) {
		plugin = null;
		try {
			plugin = new ActiveXObject("SharePoint.OpenDocuments.3"); // Office 2007+
		} catch (e) {
			try {
				plugin = new ActiveXObject("SharePoint.OpenDocuments.2"); // Office 2003
			} catch (e2) {
				try {
					plugin = new ActiveXObject("SharePoint.OpenDocuments.1"); // Office 2000/XP
				} catch (e3) {
					window.console && console.warn("Could not create ActiveXObject('SharePoint.OpenDocuments'): (requires IE <= 11 and matching security settings.");
				}
			}
		}
		if (plugin) {
			window.console && console.log("Using native SharePoint plugin.");
			sharePointPlugin = plugin;
		}
	}
	return sharePointPlugin;
}


/**
 * Open an MS Office document either with SharePoint plugin or using the 'ms-' URL prefix.
 *
 * @param {object} opts
	* @returns {boolean} true if the URL could be opened
	*/
function openWebDavDocument(opts) {
	var ofe_link = opts.ofe + opts.href,  // (e.g. 'ms-word:ofe|u|http://server/path/file.docx')
		url = opts.href;

	var plugin = getSharePointPlugin();
	var res = false;

	if (plugin) {
		try {
			res = plugin.EditDocument(url);
			if (res === false) {
				window.console && console.warn("SharePoint plugin.EditDocument(" + url + ") returned false");
			}
		} catch (e) {
			window.console && console.warn("SharePoint plugin.EditDocument(" + url + ") raised an exception", e);
		}
	}
	if (res === false) {
		if (ofe_link) {
			window.console && console.log("Could not use SharePoint plugin: trying " + ofe_link);
			window.open(ofe_link, "_self");
			res = true;
		}
	}
	return res;
}


/**
 * Event delegation handler for clicks on a-tags with class 'msoffice'.
 */
function onClickTable(event) {
	var target = event.target || event.srcElement,
		opts = {
			href: target.href,
			ofe: target.getAttribute("data-ofe")
		};

	if (target.className === "msoffice") {
		if (openWebDavDocument(opts)) {
			// prevent default processing if the document could be opened
			return false;
		}
	}
}

async function loadWbResources(options = {}) {
	options = Object.assign({ path: "/", details: false }, options);
	const client = getDAVClient();

	const resList = await client.getDirectoryContents(options.path, options);
	console.log(resList);

	const nodeList = [];
	for (let res of resList) {
		res.title = res.basename;
		delete res.basename;
		if (res.type === "directory") res.lazy = true;
		nodeList.push(res);
	}
	console.info("getDirectoryContents", nodeList);
	return nodeList;
}


const commandBarFile = util.elemFromHtml(commandHtmlTemplateFile);
const commandBarFolder = util.elemFromHtml(commandHtmlTemplateFolder);

const tree = new Wunderbaum({
	element: "div#tree",
	debugLevel: 5,
	types: {},
	columns: [
		{ id: "*", title: "Path", width: "300px" },
		{ id: "commands", title: " ", width: "100px", sortable: false },
		{ id: "type", title: "Type", width: "100px" },
		{ id: "size", title: "Size", width: "80px", classes: "wb-helper-end" },
		{ id: "lastmod", title: "Modified", width: "250px" },
		// {id: "etag", title: "ETag", width: "80px" },
		{ id: "mime", title: "Mime", width: 1 },
	],
	columnsSortable: true,
	columnsResizable: true,
	navigationModeOption: "row",
	icon: (e) => {
		const ext = e.node.title.split('.').pop().toLowerCase();
		if (fileTypeIcons[ext]) return fileTypeIcons[ext];
	},

	source: loadWbResources(),

	init: function (e) {
		e.tree.setFocus();
		togglePreviewPane(false);
	},
	load: function (e) {
		e.tree.sort({ colId: "*", updateColInfo: true, foldersFirst: true });
	},
	lazyLoad: function (e) {
		const path = e.node.getPath();
		return loadWbResources({ path: path });
	},
	buttonClick: (e) => {
		if (e.command === "sort") {
			e.tree.sort({ colId: e.info.colId, updateColInfo: true, foldersFirst: true });
		}
	},
	activate: (e) => {
		showPreview(e.node);
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
			return true;
		},
		dragEnter: (e) => {
			console.log(e.type, e);
			return true;
		},
		drop: (e) => {
			const dataTransfer = e.dataTransfer;  // Wunderbaum >= 0.13.1
			console.log(e.type, e, dataTransfer.items.length);
			if (dataTransfer.items) {
				// Use DataTransferItemList interface to access the file(s)
				[...dataTransfer.items].forEach((item, i) => {
					// If dropped items aren't files, reject them
					if (item.kind === "file") {
						const file = item.getAsFile();
						console.log(`… file[${i}].name = ${file.name} `);
					}
				});
			} else {
				// Use DataTransfer interface to access the file(s)
				[...e.dataTransfer.files].forEach((file, i) => {
					console.log(`… file[${i}].name = ${file.name}`);
				});
			}
		},
	},
});

registerCommandButtons("body", (e) => {
	const node = e.node;
	console.info("got", `${node}`, e.command, e);
	switch (e.command) {
		case "togglePreview":
			togglePreviewPane(e.isPressed);
			if (e.isPressed) { showPreview(node); } else { showPreview(null); }
			break;
		case "rename":
			node.startEditTitle();
			break;
		case "delete":
			if (confirm(`Delete '${node.getPath()}' from the server?\n\nThis cannot be undone!`)) {
				getDAVClient().deleteFile(node.getPath()).then(() => {
					node.remove();
				});
			}
			break;
		case "upload":
			uploadFiles(node);
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