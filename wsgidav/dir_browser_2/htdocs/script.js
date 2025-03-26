"use strict";

import { Wunderbaum } from "https://esm.run/wunderbaum@0.13";
// /** @type {import("https://cdn.jsdelivr.net/npm/wunderbaum@0.13.0/dist/wunderbaum.d.ts")} */
import { createClient } from "https://esm.run/webdav@5.8.0";

// Cached plugin reference (or null. if it could not be instantiated)
let sharePointPlugin = undefined;
let _client = null;


const fileTypeIcons = {
	aac: "bi bi-filetype-aac",
	ai: "bi bi-filetype-ai",
	bmp: "bi bi-filetype-bmp",
	cs: "bi bi-filetype-cs",
	css: "bi bi-filetype-css",
	csv: "bi bi-filetype-csv",
	doc: "bi bi-filetype-doc",
	docx: "bi bi-filetype-docx",
	exe: "bi bi-filetype-exe",
	gif: "bi bi-filetype-gif",
	heic: "bi bi-filetype-heic",
	html: "bi bi-filetype-html",
	java: "bi bi-filetype-java",
	jpg: "bi bi-filetype-jpg",
	js: "bi bi-filetype-js",
	json: "bi bi-filetype-json",
	jsx: "bi bi-filetype-jsx",
	key: "bi bi-filetype-key",
	m4p: "bi bi-filetype-m4p",
	md: "bi bi-filetype-md",
	mdx: "bi bi-filetype-mdx",
	mov: "bi bi-filetype-mov",
	mp3: "bi bi-filetype-mp3",
	mp4: "bi bi-filetype-mp4",
	otf: "bi bi-filetype-otf",
	pdf: "bi bi-filetype-pdf",
	php: "bi bi-filetype-php",
	png: "bi bi-filetype-png",
	ppt: "bi bi-filetype-ppt",
	pptx: "bi bi-filetype-pptx",
	psd: "bi bi-filetype-psd",
	py: "bi bi-filetype-py",
	raw: "bi bi-filetype-raw",
	rb: "bi bi-filetype-rb",
	sass: "bi bi-filetype-sass",
	scss: "bi bi-filetype-scss",
	sh: "bi bi-filetype-sh",
	sql: "bi bi-filetype-sql",
	svg: "bi bi-filetype-svg",
	tiff: "bi bi-filetype-tiff",
	tsx: "bi bi-filetype-tsx",
	ttf: "bi bi-filetype-ttf",
	txt: "bi bi-filetype-txt",
	wav: "bi bi-filetype-wav",
	woff: "bi bi-filetype-woff",
	xls: "bi bi-filetype-xls",
	xlsx: "bi bi-filetype-xlsx",
	xml: "bi bi-filetype-xml",
	yaml: "bi bi-filetype-yml",
	yml: "bi bi-filetype-yml",
};

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

function getClient(options = {}) {
	options = Object.assign({ remoteURL: window.location.href }, options);
	if (_client === null) {
		_client = createClient(options.remoteURL);
	}
	return _client;
}

async function loadWbResources(options = {}) {
	options = Object.assign({ path: "/" }, options);
	const client = getClient();

	const resList = await client.getDirectoryContents(options.path);
	console.log(resList)

	const nodeList = [];
	for (let res of resList) {
		res.title = res.basename;
		delete res.basename;
		if (res.type === "directory") res.lazy = true;
		nodeList.push(res)
	}
	console.info("getDirectoryContents", nodeList)
	return nodeList;
}
function nodeSorter(a, b) {
	a = (a.type === "directory" ? "0" : "1") + a.title.toLowerCase();
	b = (b.type === "directory" ? "0" : "1") + b.title.toLowerCase();
	return a < b ? -1 : 1;

}

// Execute on startup
document.addEventListener("DOMContentLoaded", function () {
	const tree = new Wunderbaum({
		element: "div#tree",
		types: {},
		columns: [
			{ id: "*", title: "Path", width: "300px" },
			{ id: "type", title: "Type", width: "100px" },
			{ id: "size", title: "Size", width: "80px", classes: "wb-helper-end" },
			{ id: "lastmod", title: "Modified", width: "250px" },
			// { id: "etag", title: "ETag", width: "80px" },
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
		},
		load: function (e) {
			e.node.sortChildren(nodeSorter);
		},
		lazyLoad: function (e) {
			const path = e.node.getPath();
			return loadWbResources({ path: path });
		},

		render: function (e) {
			const node = e.node;

			for (const col of Object.values(e.renderColInfosById)) {
				switch (col.id) {
					case "type":
						col.elem.textContent = node.type;
						break;
					case "size":
						col.elem.textContent = node.type === "directory" ? "" : node.data.size.toLocaleString();
						break;
					default:
						// Assumption: we named column.id === node.data.NAME
						col.elem.textContent = node.data[col.id];
						break;
				}
			}
		},
	});


});