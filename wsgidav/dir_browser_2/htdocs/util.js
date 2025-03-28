/**
 * Borrow utility functions from Wunderbaum.
 * https://mar10.github.io/wunderbaum/api/modules/util.html
 */
"use strict";

import { Wunderbaum } from "./wunderbaum.esm.js";

export const util = Wunderbaum.util;
export function getNodeResourceUrl(node) {
    let path = node.getPath();
    path = window.location.href + path;
    return path;
}