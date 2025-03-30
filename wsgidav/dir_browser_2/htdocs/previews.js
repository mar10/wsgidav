"use strict";

import Split from "https://cdn.jsdelivr.net/npm/split.js@1.6.5/+esm";
import { getNodeResourceUrl } from "./util.js";

const fileTypeIcons = {
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
});

// async function setPreviewImageUrl(url) {
// 	return new Promise(function (resolve, reject) {
// 		var image = new Image();
// 		image.addEventListener('load', resolve);
// 		image.addEventListener('error', reject);
// 		image.src = url;
// 	});
// }
document.querySelector("aside.right img#preview-img").addEventListener("error", (e) => {
	console.error(`Could not load preview <img src=${e.target.src}>`, e);
});

export function togglePreviewPane(flag = true) {
	if (flag) {
		splitter.setSizes(splitterSize);
	} else {
		splitter.collapse(1);
	}
	document.querySelector("aside.right").classList.toggle("show", flag);

}

export function isPreviewPaneOpen() {
	const element = document.querySelector("aside.right.show");
	return !!element;
}

export async function showPreview(urlOrNode, options = {}) {
	let { autoOpen = false } = options;
	const imgElem = document.querySelector("aside.right img#preview-img");
	const textElem = document.querySelector("aside.right pre#preview-text");
	const placeholderElem = document.querySelector("aside.right p#preview-placeholder");

	imgElem.src = "";
	textElem.textContent = "";
	if (!urlOrNode) {
		return false;
	}
	if (!isPreviewPaneOpen()) {
		if (autoOpen) { togglePreviewPane(); } else { return false; }
	}
	const url = (!typeof urlOrNode === "string") ? urlOrNode : getNodeResourceUrl(urlOrNode);

	const extension = url.split('.').pop().toLowerCase();
	const typeInfo = fileExtensionMap[extension] ?? {};
	const preview = typeInfo.preview;
	imgElem.classList.toggle("hidden", preview !== "image");
	textElem.classList.toggle("hidden", preview !== "text");
	placeholderElem.classList.toggle("hidden", preview != null);
	switch (preview) {
		case "text":
			const response = await fetch(url);
			const text = await response.text();
			textElem.textContent = text;
			break;
		case "image":
			imgElem.src = url;
			break;
	}
	return true;
}
