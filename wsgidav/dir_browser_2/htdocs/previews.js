"use strict";

import Split from "https://cdn.jsdelivr.net/npm/split.js@1.6.5/+esm";
import { getNodeResourceUrl, getTree } from "./util.js";
import { setCommandButton } from "./widgets.js";

export const fileTypeIcons = {
	text: {
		csv: "bi bi-filetype-csv",
		md: "bi bi-file-earmark-text",
		mdx: "bi bi-filetype-mdx",
		txt: "bi bi-file-earmark-text",
		yaml: "bi bi-filetype-yml",
		yml: "bi bi-filetype-yml",
	},
	image: {
		ai: "bi bi-file-earmark-image",
		bmp: "bi bi-file-earmark-image",
		gif: "bi bi-file-earmark-image",
		heic: "bi bi-file-earmark-image",
		jpg: "bi bi-file-earmark-image",
		jpeg: "bi bi-file-earmark-image",
		png: "bi bi-file-earmark-image",
		psd: "bi bi-file-earmark-image",
		raw: "bi bi-file-earmark-image",
		svg: "bi bi-file-earmark-image",
		tiff: "bi bi-file-earmark-image",
	},
	audio: {
		aac: "bi bi-file-earmark-music",
		m4p: "bi bi-file-earmark-music",
		mp3: "bi bi-file-earmark-music",
		wav: "bi bi-file-earmark-play",
	},
	video: {
		mov: "bi bi-file-earmark-play",
		mp4: "bi bi-file-earmark-play",
	},
	pdf: {
		pdf: "bi bi-file-earmark-pdf",
	},
	office: {
		doc: "bi bi-file-earmark-richtext",
		docx: "bi bi-file-earmark-richtext",
		key: "bi bi-filetype-key",
		ppt: "bi bi-file-earmark-slides",
		pptx: "bi bi-file-earmark-slides",
		xls: "bi bi-file-earmark-spreadsheet",
		xlsx: "bi bi-file-earmark-spreadsheet",
	},
	archive: {
		"7z": "bi bi-file-earmark-zip",
		gz: "bi bi-file-earmark-zip",
		tar: "bi bi-file-earmark-zip",
		zip: "bi bi-file-earmark-zip",
	},
	font: {
		otf: "bi bi-file-earmark-font",
		ttf: "bi bi-file-earmark-font",
		woff: "bi bi-file-earmark-font",
	},
	executable: {
		bat: "bi bi-file-earmark-terminal",
		exe: "bi bi-windows",
		ps1: "bi bi-file-earmark-terminal",
		sh: "bi bi-file-earmark-terminal",
	},
	code: {
		css: "bi bi-filetype-css",
		html: "bi bi-filetype-html",
		js: "bi bi-filetype-js",
		json: "bi bi-filetype-json",
		jsx: "bi bi-filetype-jsx",
		php: "bi bi-filetype-php",
		py: "bi bi-filetype-py",
		rb: "bi bi-filetype-rb",
		sass: "bi bi-filetype-sass",
		scss: "bi bi-filetype-scss",
		sql: "bi bi-filetype-sql",
		tsx: "bi bi-filetype-tsx",
		xml: "bi bi-filetype-xml",
		java: "bi bi-filetype-java",
	},
	other: {},
};

export const fileExtensionMap = {};
for (let [type, extensions] of Object.entries(fileTypeIcons)) {
	for (let [ext, icon] of Object.entries(extensions)) {
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
		fileExtensionMap[ext] = { icon: icon, type: type, preview: preview };
	}
}
// console.dir(fileExtensionMap);

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
				console.warn(`Error loading preview ${url}`, e);
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
