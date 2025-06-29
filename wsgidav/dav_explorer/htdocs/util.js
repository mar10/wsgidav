/**
 * Borrow utility functions from Wunderbaum.
 * https://mar10.github.io/wunderbaum/api/modules/util.html
 */
"use strict";

import { createClient } from "https://esm.run/webdav@5.8.0";
import { PersistentObject } from "https://esm.run/persisto@2.0.2";
import { Wunderbaum } from "./wunderbaum.esm.js";

export const util = Wunderbaum.util;

export const persist = new PersistentObject("dav-explorer", {
    // Init default settings from jinja variable
    defailts: config || {}
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

export function isFile(node) {
    return !!(node && node.type !== "directory");
}

export function getNodeOrActive(node) {
    return node == null ? getActiveNode() : node;
}

export function getNodeOrTop(node) {
    return node == null ? getTree().root : node;
}

export function getNodeResourceUrl(node) {
    let url = node.getPath();
    url = url.startsWith("/") ? url.slice(1) : url;
    url = window.location.href + url;
    return url;
}

let _dav_client = null;

export function getDAVClient(options = {}) {
    options = Object.assign({ remoteURL: window.location.href }, options);
    if (_dav_client === null) {
        _dav_client = createClient(options.remoteURL);
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

