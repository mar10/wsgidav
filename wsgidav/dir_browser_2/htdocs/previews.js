"use strict";

export const commandHtmlTemplateFile = `
<span class="command-palette">
	<i class="bi bi-cloud-download" title="Download file..." data-command="download"></i>
	<i class="bi bi-windows" title="Open in MS-Office" data-command="startOffice"></i>
	<i class="bi bi-trash3" title="Delete file" data-command="delete"></i>
	<i class="bi bi-pencil-square" title="Rename file" data-command="rename"></i>
</span>
`;
export const commandHtmlTemplateFolder = `
<span class="command-palette">
	<i class="bi bi-cloud-download inactive" title="Download folder..."></i>
	<i class="bi bi-windows inactive" title="Open in MS-Office"></i>
	<i class="bi bi-trash3" title="Delete folder" data-command="delete"></i>
	<i class="bi bi-pencil-square" title="Rename folder" data-command="rename"></i>
</span>
`;

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
