/**
 * Borrow utility functions from Wunderbaum.
 * https://mar10.github.io/wunderbaum/api/modules/util.html
 */
"use strict";

import { createClient } from "https://esm.run/webdav@5.8.0";
import { Wunderbaum } from "./wunderbaum.esm.js";

export const util = Wunderbaum.util;

export function getTree() {
    return Wunderbaum.getTree();
}

export function getNodeOrActive(node) {
    return node == null ? getTree().getActiveNode() : node;
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

