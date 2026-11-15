/**
 * Syntax-highlighting text viewer and editor, based on CodeMirror 6.
 *
 * This module is loaded on demand by previews.js (dynamic import), so the
 * CodeMirror code is only fetched when a text file is previewed.
 */
"use strict";

// The bare module specifiers are resolved by the import map in app.html, which
// pins every CodeMirror package (and its dependencies) to a single version
// and lets the browser verify the file hashes (SRI).
// CodeMirror needs a single copy of each package, otherwise it fails with
// "Unrecognized extension value ... multiple instances".
// Note: import modules with string literals, so tests can check that the
// import map covers them (see `ENTRY_POINTS` in
// scripts/update_dav_explorer_cdn.py).
const [{ basicSetup }, { Compartment, EditorState, Prec }, { EditorView, keymap }, { oneDark }] = await Promise.all([
  import("codemirror"),
  import("@codemirror/state"),
  import("@codemirror/view"),
  import("@codemirror/theme-one-dark"),
]);

/** Load a language from `@codemirror/legacy-modes` (StreamLanguage). */
async function legacyMode(modulePromise, name) {
  const [{ StreamLanguage }, mod] = await Promise.all([import("@codemirror/language"), modulePromise]);
  return StreamLanguage.define(mod[name]);
}

// Keys are the `lang` values in previews.js `fileTypeInfo`
const LANGUAGE_LOADERS = {
  css: async () => (await import("@codemirror/lang-css")).css(),
  html: async () => (await import("@codemirror/lang-html")).html(),
  javascript: async () => (await import("@codemirror/lang-javascript")).javascript(),
  jsx: async () => (await import("@codemirror/lang-javascript")).javascript({ jsx: true }),
  typescript: async () => (await import("@codemirror/lang-javascript")).javascript({ typescript: true }),
  tsx: async () => (await import("@codemirror/lang-javascript")).javascript({ jsx: true, typescript: true }),
  json: async () => (await import("@codemirror/lang-json")).json(),
  markdown: async () => (await import("@codemirror/lang-markdown")).markdown(),
  python: async () => (await import("@codemirror/lang-python")).python(),
  xml: async () => (await import("@codemirror/lang-xml")).xml(),
  yaml: async () => (await import("@codemirror/lang-yaml")).yaml(),
  powershell: () => legacyMode(import("@codemirror/legacy-modes/mode/powershell.js"), "powerShell"),
  properties: () => legacyMode(import("@codemirror/legacy-modes/mode/properties.js"), "properties"),
  shell: () => legacyMode(import("@codemirror/legacy-modes/mode/shell.js"), "shell"),
  toml: () => legacyMode(import("@codemirror/legacy-modes/mode/toml.js"), "toml"),
};

const _languageCache = new Map();

/**
 * Return the CodeMirror language extension for a `lang` name, or null.
 * Never throws: if a language cannot be loaded, the text is shown without
 * highlighting.
 */
export async function loadLanguage(lang) {
  const loader = lang ? LANGUAGE_LOADERS[lang] : null;
  if (!loader) {
    return null;
  }
  if (!_languageCache.has(lang)) {
    _languageCache.set(
      lang,
      loader().catch((err) => {
        console.warn(`Could not load CodeMirror language '${lang}'`, err);
        _languageCache.delete(lang); // Try again next time
        return null;
      })
    );
  }
  return _languageCache.get(lang);
}

function isDarkTheme() {
  return document.documentElement.dataset.theme === "dark";
}

/**
 * A CodeMirror view that is readonly by default and can be switched to edit mode.
 */
export class TextViewer {
  /**
   * @param {Element} parent
   * @param {object} [options]
   * @param {function} [options.onSave] Called on Ctrl/Cmd+S in edit mode
   * @param {function} [options.onCancel] Called on Escape in edit mode
   * @param {function} [options.onChange] Called with `isDirty` when the text changes
   */
  constructor(parent, options = {}) {
    this.onSave = options.onSave ?? null;
    this.onCancel = options.onCancel ?? null;
    this.onChange = options.onChange ?? null;
    this.editable = false;
    this._languageConf = new Compartment();
    this._editableConf = new Compartment();
    this._themeConf = new Compartment();
    this._langExt = null;
    this.view = new EditorView({ parent: parent, state: this._createState("") });
    this._cleanDoc = this.view.state.doc;

    // Follow the explorer's light/dark theme
    this._themeObserver = new MutationObserver(() => {
      this.view.dispatch({ effects: this._themeConf.reconfigure(this._themeExt()) });
    });
    this._themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  }

  _themeExt() {
    return isDarkTheme() ? oneDark : [];
  }

  _editableExt() {
    // Readonly mode still allows selecting, copying, and searching
    return EditorState.readOnly.of(!this.editable);
  }

  _createState(text) {
    return EditorState.create({
      doc: text,
      extensions: [
        Prec.high(
          keymap.of([
            {
              key: "Mod-s",
              preventDefault: true,
              run: () => {
                if (this.editable) {
                  this.onSave?.();
                }
                return true; // Never open the browser's "Save page" dialog
              },
            },
          ])
        ),
        basicSetup,
        // Lower precedence than basicSetup, so Escape closes the search panel
        // or autocompletion first
        keymap.of([
          {
            key: "Escape",
            run: () => {
              if (!this.editable) {
                return false;
              }
              this.onCancel?.();
              return true;
            },
          },
        ]),
        this._languageConf.of(this._langExt ?? []),
        this._editableConf.of(this._editableExt()),
        this._themeConf.of(this._themeExt()),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            this.onChange?.(this.isDirty());
          }
        }),
      ],
    });
  }

  /** Replace the content (resets undo history and the dirty state). */
  setText(text, langExt = null) {
    this._langExt = langExt;
    this.view.setState(this._createState(text ?? ""));
    this._cleanDoc = this.view.state.doc;
  }

  getText() {
    return this.view.state.doc.toString();
  }

  /** Return the current (immutable) document, e.g. to pass it to `markClean()` later. */
  getDoc() {
    return this.view.state.doc;
  }

  setEditable(flag) {
    this.editable = !!flag;
    this.view.dispatch({ effects: this._editableConf.reconfigure(this._editableExt()) });
  }

  isDirty() {
    return !this.view.state.doc.eq(this._cleanDoc);
  }

  /** Mark `doc` (default: the current content) as saved. */
  markClean(doc = this.view.state.doc) {
    this._cleanDoc = doc;
    this.onChange?.(this.isDirty());
  }

  /** Discard all changes since the last `setText()` or `markClean()`. */
  revert() {
    this.setText(this._cleanDoc.toString(), this._langExt);
  }

  focus() {
    this.view.focus();
  }

  destroy() {
    this._themeObserver.disconnect();
    this.view.destroy();
  }
}
