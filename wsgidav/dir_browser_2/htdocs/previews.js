"use strict";

import Split from "https://cdn.jsdelivr.net/npm/split.js@1.6.5/+esm";

export const fileTypeIcons = {
	"7z": "bi bi-file-earmark-zip",
	aac: "bi bi-file-earmark-music",  //"bi bi-filetype-aac",
	ai: "bi bi-file-earmark-image", //"bi bi-filetype-ai",
	bat: "bi bi-file-earmark-terminal", //"bi bi-filetype-sh",
	bmp: "bi bi-file-earmark-image",  // "bi bi-filetype-bmp",
	cs: "bi bi-filetype-cs",
	css: "bi bi-filetype-css",
	csv: "bi bi-filetype-csv",
	doc: "bi bi-file-earmark-richtext", // "bi bi-filetype-doc",
	docx: "bi bi-file-earmark-richtext", //"bi bi-filetype-docx",
	exe: "bi bi-windows",//"bi bi-filetype-exe",
	gif: "bi bi-file-earmark-image",  // "bi bi-filetype-gif",
	gz: "bi bi-file-earmark-zip",
	heic: "bi bi-file-earmark-image",  // "bi bi-filetype-heic",
	html: "bi bi-filetype-html",
	java: "bi bi-filetype-java",
	jpg: "bi bi-file-earmark-image",  // "bi bi-filetype-jpg",
	js: "bi bi-filetype-js",
	json: "bi bi-filetype-json",
	jsx: "bi bi-filetype-jsx",
	key: "bi bi-filetype-key",
	m4p: "bi bi-file-earmark-music",  //"bi bi-filetype-m4p",
	md: "bi bi-file-earmark-text", //"bi bi-filetype-md",
	mdx: "bi bi-filetype-mdx",
	mov: "bi bi-file-earmark-play",  // "bi bi-filetype-mov",
	mp3: "bi bi-file-earmark-music",  //"bi bi-filetype-mp3",
	mp4: "bi bi-file-earmark-play", //"bi bi-filetype-mp4",
	otf: "bi bi-file-earmark-font", //"bi bi-filetype-otf",
	pdf: "bi bi-file-earmark-pdf",//"bi bi-filetype-pdf",
	php: "bi bi-filetype-php",
	png: "bi bi-file-earmark-image",  // "bi bi-filetype-png",
	ppt: "bi bi-file-earmark-slides", //"bi bi-filetype-ppt",
	pptx: "bi bi-file-earmark-slides",//"bi bi-filetype-pptx",
	ps1: "bi bi-file-earmark-terminal", //"bi bi-filetype-sh",
	psd: "bi bi-file-earmark-image",  //"bi bi-filetype-psd",
	py: "bi bi-filetype-py",
	raw: "bi bi-file-earmark-image",//"bi bi-filetype-raw",
	rb: "bi bi-filetype-rb",
	sass: "bi bi-filetype-sass",
	scss: "bi bi-filetype-scss",
	sh: "bi bi-file-earmark-terminal", //"bi bi-filetype-sh",
	sql: "bi bi-filetype-sql",
	svg: "bi bi-file-earmark-image", //"bi bi-filetype-svg",
	tar: "bi bi-file-earmark-zip",
	tiff: "bi bi-file-earmark-image",  //"bi bi-filetype-tiff",
	tsx: "bi bi-filetype-tsx",
	ttf: "bi bi-file-earmark-font", //"bi bi-filetype-ttf",
	txt: "bi bi-file-earmark-text", //"bi bi-filetype-txt",
	wav: "bi bi-file-earmark-play",  //"bi bi-filetype-wav",
	woff: "bi bi-file-earmark-font", //"bi bi-filetype-woff",
	xls: "bi bi-file-earmark-spreadsheet",//"bi bi-filetype-xls",
	xlsx: "bi bi-file-earmark-spreadsheet",//"bi bi-filetype-xlsx",
	xml: "bi bi-filetype-xml",
	yaml: "bi bi-filetype-yml",
	yml: "bi bi-filetype-yml",
	zip: "bi bi-file-earmark-zip",
};

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
	let url = (!typeof urlOrNode === "string") ? urlOrNode : urlOrNode.getPath();
	url = url.startsWith("/") ? url.slice(1) : url;
	url = window.location.href + url;

	const extension = url.split('.').pop().toLowerCase();
	const isImage = ["jpg", "jpeg", "png", "gif", "bmp", "svg", "tiff", "heic", "raw", "psd", "pdf"].includes(extension);
	const isText = ["txt", "md", "ini", "json", "xml", "html", "css", "js", "jsx", "ts", "tsx", "yaml", "yml", "csv"].includes(extension);
	imgElem.classList.toggle("hidden", !isImage);
	textElem.classList.toggle("hidden", !isText);
	placeholderElem.classList.toggle("hidden", (isImage || isText));
	if (isImage) {
		imgElem.onload = () => {
			imgElem.onload = null;
			imgElem.setAttribute("src", url);
		};
		imgElem.onerror = (e) => {
			imgElem.onerror = null;
			console.error(`Error loading preview ${url}`, e);
			imgElem.src = imgPlaceholderErrorSvg;
		};
		imgElem.setAttribute("src", imgPlaceholderLoadingSvg);
	} else if (isText) {
		textElem.textContent = "Loading...";
		const response = await fetch(url);
		const text = await response.text();
		textElem.textContent = text;
	}
	return true;
}
