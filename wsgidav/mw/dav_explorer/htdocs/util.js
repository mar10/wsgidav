/**
 * Borrow utility functions from Wunderbaum.
 * https://mar10.github.io/wunderbaum/api/modules/util.html
 */
"use strict";

import { createClient } from "https://esm.run/webdav@5.11.0";
import { PersistentObject } from "https://esm.run/persisto@2.0.2";
// import { Wunderbaum } from "./wunderbaum.esm.js";
import { Wunderbaum } from "https://esm.run/wunderbaum@0.15.0";

// All modules must import Wunderbaum from here, so only one copy is loaded
export { Wunderbaum };
export const util = Wunderbaum.util;

export const config = JSON.parse(document.getElementById("context-data").textContent);

export const settingsStore = new PersistentObject("dav-explorer", {
  // debug: 2,
  store: localStorage,
  attachForm: "#settingsForm",
  // Init default settings from jinja context
  defaults: {
    showInfoPane: config.showInfoPane, // Show the info pane on the right side
    max_preview_size_kb: config.max_preview_size_kb, // 500 KiB;
    office_support: config.office_support, // Assume that clients have MS/LibreOffice installed
    office_readonly: config.readonly, // Open Office documents in readonly mode by default
    dblclick_action: "open", // Double-click on files: 'open', 'download', 'nothing'
    dblclick_action_folders: "expand", // Double-click on folders: 'expand', 'set_root'
  },
});

export function getTree() {
  return Wunderbaum.getTree();
}

export function getActiveNode() {
  return getTree().getActiveNode();
}

export function isFolder(node) {
  return node?.type === "directory";
}

export function isRootFolder(node) {
  return node?.isRootNode();
}

export function isFile(node) {
  return !!(node && node.type !== "directory");
}

/**
 * Return the absolute URL of the collection that is displayed by this page.
 *
 * The result always ends with '/' and has no query string or hash, even if the
 * page was requested as `/folder` or `/folder/?foo#bar`.
 */
export function getBaseUrl() {
  let path = window.location.pathname;
  if (!path.endsWith("/")) {
    path += "/";
  }
  return window.location.origin + path;
}

/** Validate a single path segment (new folder name, rename target). */
export function isValidResourceName(name) {
  return typeof name === "string" && name.trim() !== "" && name !== "." && name !== ".." && !/[\/\\]/.test(name);
}

/** Return the absolute, URL-encoded URL of a node's resource. */
export function getNodeResourceUrl(node) {
  const segments = node
    .getPath()
    .split("/")
    .filter((s) => s !== "")
    .map((s) => encodeURIComponent(s));
  return getBaseUrl() + segments.join("/");
}

let _dav_client = null;

export function getDAVClient() {
  if (_dav_client === null) {
    _dav_client = createClient(getBaseUrl());
  }
  return _dav_client;
}

/**
 * Convert an RFC1123 or ISO 8601 date string to a Unix timestamp (milliseconds since epoch).
 * Returns NaN if parsing fails.
 * @param {string} dateStr
 * @returns {number}
 */
export function parseDateToTimestamp(dateStr) {
  // Date.parse handles both RFC1123 and ISO 8601 in modern browsers
  return Date.parse(dateStr);
}

/** Convert an fnmatch-style pattern (`*`, `?`, `[...]`) to a RegExp. */
function globToRegExp(pattern) {
  let re = "";
  for (let i = 0; i < pattern.length; i++) {
    const c = pattern[i];
    if (c === "*") {
      re += ".*";
    } else if (c === "?") {
      re += ".";
    } else if (c === "[") {
      const end = pattern.indexOf("]", i + 2);
      if (end < 0) {
        re += "\\[";
      } else {
        let cls = pattern.slice(i + 1, end).replace(/\\/g, "\\\\");
        if (cls.startsWith("!")) cls = "^" + cls.slice(1);
        re += `[${cls}]`;
        i = end;
      }
    } else {
      re += c.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }
  }
  return new RegExp(`^${re}$`, "s");
}

const _ignorePatterns = (config.ignore_list || []).map(globToRegExp);

/** Return true if `name` matches one of the configured `ignore_list` patterns. */
export function isIgnored(name) {
  return _ignorePatterns.some((re) => re.test(name));
}
