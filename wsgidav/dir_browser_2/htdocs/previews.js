"use strict";

import Split from "https://cdn.jsdelivr.net/npm/split.js@1.6.5/+esm";
import { getNodeResourceUrl, getTree } from "./util.js";
import { setCommandButton } from "./widgets.js";

const fileTypeInfo = {
	text: {
		csv: { icon: "bi bi-filetype-csv" },
		md: { icon: "bi bi-file-earmark-text" },
		mdx: { icon: "bi bi-filetype-mdx" },
		txt: { icon: "bi bi-file-earmark-text" },
		yaml: { icon: "bi bi-filetype-yml" },
		yml: { icon: "bi bi-filetype-yml" },
	},
	image: {
		ai: { icon: "bi bi-file-earmark-image" },
		bmp: { icon: "bi bi-file-earmark-image" },
		gif: { icon: "bi bi-file-earmark-image" },
		heic: { icon: "bi bi-file-earmark-image" },
		jpg: { icon: "bi bi-file-earmark-image" },
		jpeg: { icon: "bi bi-file-earmark-image" },
		png: { icon: "bi bi-file-earmark-image" },
		psd: { icon: "bi bi-file-earmark-image" },
		raw: { icon: "bi bi-file-earmark-image" },
		svg: { icon: "bi bi-file-earmark-image" },
		tiff: { icon: "bi bi-file-earmark-image" },
	},
	audio: {
		aac: { icon: "bi bi-file-earmark-music" },
		m4p: { icon: "bi bi-file-earmark-music" },
		mp3: { icon: "bi bi-file-earmark-music" },
		wav: { icon: "bi bi-file-earmark-play" },
	},
	video: {
		mov: { icon: "bi bi-file-earmark-play" },
		mp4: { icon: "bi bi-file-earmark-play" },
	},
	pdf: {
		pdf: { icon: "bi bi-file-earmark-pdf" },
	},
	office: { // Microsoft Office and Open Document formats
		// Word:
		doc: { icon: "bi bi-file-earmark-word", protocol: "ms-word" },
		docm: { icon: "bi bi-file-earmark-word", protocol: "ms-word" },
		docx: { icon: "bi bi-file-earmark-word", protocol: "ms-word" },
		dot: { icon: "bi bi-file-earmark-word", protocol: "ms-word", nft: true },
		dotx: { icon: "bi bi-file-earmark-word", protocol: "ms-word", nft: true },
		dotm: { icon: "bi bi-file-earmark-word", protocol: "ms-word", nft: true },
		odt: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word" },
		odm: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word" },
		ott: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word", nft: true },
		oth: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word", nft: true },
		uot: { icon: "bi bi-file-earmark-richtext", protocol: "ms-word" },
		// Excel:
		xls: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel" },
		xlsm: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel" },
		xlsx: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel" },
		xlt: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel", nft: true },
		xltx: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel", nft: true },
		xltm: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel", nft: true },
		ods: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel" },
		ots: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel", nft: true },
		uos: { icon: "bi bi-file-earmark-spreadsheet", protocol: "ms-excel" },
		// PowerPoint:
		ppt: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint" },
		pptm: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint" },
		pptx: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint" },
		ppsx: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint" },
		ppsm: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint" },
		potx: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint", nft: true },
		potm: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint", nft: true },
		odp: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint" },
		otp: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint", nft: true },
		uop: { icon: "bi bi-file-earmark-slides", protocol: "ms-powerpoint" },
		key: { icon: "bi bi-filetype-key" },
		// Publisher:
		pub: { icon: "bi bi-file-earmark-ppt", protocol: "ms-publisher" },
		// Visio:
		vsd: { icon: "bi bi-file-earmark-diagram", protocol: "ms-visio" },
		vsdx: { icon: "bi bi-file-earmark-diagram", protocol: "ms-visio" },
		// Project:
		mpp: { icon: "bi bi-file-earmark-project", protocol: "ms-project" },
		mpt: { icon: "bi bi-file-earmark-project", protocol: "ms-project" },
		//Access:
		mdb: { icon: "bi bi-file-earmark-database", protocol: "ms-access" },
		accdb: { icon: "bi bi-file-earmark-database", protocol: "ms-access" },
	},
	archive: {
		"7z": { icon: "bi bi-file-earmark-zip" },
		gz: { icon: "bi bi-file-earmark-zip" },
		tar: { icon: "bi bi-file-earmark-zip" },
		zip: { icon: "bi bi-file-earmark-zip" },
	},
	font: {
		otf: { icon: "bi bi-file-earmark-font" },
		ttf: { icon: "bi bi-file-earmark-font" },
		woff: { icon: "bi bi-file-earmark-font" },
	},
	executable: {
		bat: { icon: "bi bi-file-earmark-terminal" },
		exe: { icon: "bi bi-windows" },
		ps1: { icon: "bi bi-file-earmark-terminal" },
		sh: { icon: "bi bi-file-earmark-terminal" },
	},
	code: {
		css: { icon: "bi bi-filetype-css" },
		html: { icon: "bi bi-filetype-html" },
		js: { icon: "bi bi-filetype-js" },
		json: { icon: "bi bi-filetype-json" },
		jsx: { icon: "bi bi-filetype-jsx" },
		php: { icon: "bi bi-filetype-php" },
		py: { icon: "bi bi-filetype-py" },
		rb: { icon: "bi bi-filetype-rb" },
		sass: { icon: "bi bi-filetype-sass" },
		scss: { icon: "bi bi-filetype-scss" },
		sql: { icon: "bi bi-filetype-sql" },
		tsx: { icon: "bi bi-filetype-tsx" },
		xml: { icon: "bi bi-filetype-xml" },
		java: { icon: "bi bi-filetype-java" },
	},
	other: {},
};


const fileExtensionMap = {};
for (let [type, extensions] of Object.entries(fileTypeInfo)) {
	for (let [ext, info] of Object.entries(extensions)) {
		let preview;
		switch (type) {
			case "image":
			case "pdf":
				preview = "image";
				break;
			case "text":
			case "code":
				preview = "text";
				break;
		}
		fileExtensionMap[ext] = { icon: info.icon, type: type, preview: preview, protocol: info.protocol, nft: info.nft || false };
	}
}
// console.dir(fileExtensionMap);

export function getFileInfo(name) {
	if (!name || typeof name !== "string") {
		return null;
	}
	const extension = name.split('.').pop().toLowerCase();
	return fileExtensionMap[extension] || null;
}

export function getFileIcon(name) {
	const extension = name.split('.').pop().toLowerCase();
	return fileExtensionMap[extension] ? fileExtensionMap[extension].icon : undefined;
}

/**
 * Get the Office type information for a given file name.
 * @param {string} name - The file name.
 * @returns {object|null} The Office type information or null if not found.
 */
export function getOfficeUrlPrefix(node, options = {}) {
	const { newFromTemplate = false, readonly = false } = options;
	const info = getFileInfo(node.title);
	if (!info || !info.type || info.type !== "office") {
		return null;
	}
	const protocol = info.protocol;
	const operation = newFromTemplate ? "nft" : (readonly ? "ofv" : "ofe");
	return info.protocol ? `${protocol}:${operation}|u|${getNodeResourceUrl(node)}` : null;
}



const imgElem = document.querySelector("aside.right img#preview-img");
const textElem = document.querySelector("aside.right pre#preview-text");
const folderElem = document.querySelector("aside.right div#preview-folder");
const placeholderElem = document.querySelector("aside.right div#preview-unknown");
const iframeElem = document.querySelector("aside.right iframe#preview-iframe");


const imgPlaceholderEmpty = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
const imgPlaceholderLoadingSvg = "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(`
	<svg xmlns="http://www.w3.org/2000/svg" width="200" height="150" viewBox="0 0 200 150" fill="none">
	  <rect width="200" height="150" fill="#ddd"/>
	  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#aaa" font-size="20" font-family="Arial, sans-serif">
		Loading image...
	  </text>
	</svg>
  `);
const imgPlaceholderErrorSvg = "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(`
	<svg xmlns="http://www.w3.org/2000/svg" width="200" height="150" viewBox="0 0 200 150" fill="none">
	  <rect width="200" height="150" fill="#ddd"/>
	  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#aaa" stroke="red" font-size="20" font-family="Arial, sans-serif">
		Error loading image.
	  </text>
	</svg>
  `);
/**
 * Splitter and Preview pane
 */
const splitterSize = [75, 25];
const splitter = Split(["main", "aside.right"], {
	sizes: splitterSize,
	minSize: 5,
	gutterSize: 5,
	onDragEnd: (sizes) => {
		const isOpen = sizes[1] > 5;
		document.querySelector("aside.right").classList.toggle("show", isOpen);
		setCommandButton("togglePreview", { pressed: isOpen });
	},
});

document.querySelector("aside.right img#preview-img").addEventListener("error", (e) => {
	console.warn(`Could not load preview <img src="${e.target.src}">`, e);
});

export function togglePreviewPane(flag = true) {
	if (flag) {
		splitter.setSizes(splitterSize);
	} else {
		splitter.collapse(1);
	}
	document.querySelector("aside.right").classList.toggle("show", !!flag);
	setCommandButton("togglePreview", { pressed: !!flag });
	if (flag) {
		const tree = getTree();
		const activeNode = tree.getActiveNode();
		if (activeNode) {
			showPreview(activeNode, { autoOpen: false });
		}
	} else {
		showPreview(null, { autoOpen: false });
	}
}

export function isPreviewPaneOpen() {
	return !!document.querySelector("aside.right.show");
}

export async function showPreview(urlOrNode, options = {}) {
	let { autoOpen = false, iframe = false, maxSize = 500 * 1024 } = options;

	imgElem.src = imgPlaceholderEmpty;
	textElem.textContent = "";
	if (!urlOrNode) {
		return false;
	}
	if (!isPreviewPaneOpen()) {
		if (autoOpen) {
			togglePreviewPane();
		} else {
			return false;
		}
	}
	const node = (!urlOrNode || typeof urlOrNode === "string") ? null : urlOrNode;
	const url = node ? getNodeResourceUrl(urlOrNode) : urlOrNode;
	const isFolder = node?.type === "directory";
	let preview = null;

	if (iframe) {
		preview = "iframe";
	} else {
		const extension = url.split('.').pop().toLowerCase();
		const typeInfo = fileExtensionMap[extension] ?? {};
		preview = typeInfo.preview;
	}
	placeholderElem.innerHTML = "<p>No preview available.</p>";
	console.info(`showPreview(${urlOrNode}, { autoOpen: ${autoOpen}, iframe: ${iframe} })`, preview, node);
	if (preview && node && node.data.size > maxSize) {
		placeholderElem.innerHTML = `File is too large. <a href="${url}" target="_blank">Click here</a> to preview.`;
		preview = null;
	}

	imgElem.classList.toggle("hidden", preview !== "image");
	textElem.classList.toggle("hidden", preview !== "text");
	folderElem.classList.toggle("hidden", !isFolder);
	placeholderElem.classList.toggle("hidden", isFolder || preview != null);
	iframeElem.classList.toggle("hidden", preview !== "iframe");

	switch (preview) {
		case "text":
			textElem.textContent = "Loading...";
			const response = await fetch(url);
			const text = await response.text();
			textElem.textContent = text;
			break;
		case "image":
			imgElem.onload = () => {
				imgElem.onload = null;
				imgElem.setAttribute("src", url);
			};
			imgElem.onerror = (e) => {
				imgElem.onerror = null;
				console.warn("Error loading preview %s", url, e);
				imgElem.src = imgPlaceholderErrorSvg;
			};
			imgElem.setAttribute("src", imgPlaceholderLoadingSvg);
			break;
		case "iframe":
			// const iframe = document.querySelector("aside.right div#preview-iframe iframe");
			// const iframe = iframeElem.querySelector("iframe");
			iframeElem.src = "about:blank"; // Reset before setting new src
			iframeElem.setAttribute("src", url);
			break;
	}
	return true;
}
