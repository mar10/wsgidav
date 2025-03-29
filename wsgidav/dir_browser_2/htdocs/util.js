/**
 * Borrow utility functions from Wunderbaum.
 * https://mar10.github.io/wunderbaum/api/modules/util.html
 */
"use strict";

import { Wunderbaum } from "./wunderbaum.esm.js";

export const util = Wunderbaum.util;

export function getNodeResourceUrl(node) {
    let url = node.getPath();
    url = url.startsWith("/") ? url.slice(1) : url;
    url = window.location.href + url;
    return url;
}