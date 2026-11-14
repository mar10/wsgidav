/**
 * Syntax-highlighting text viewer and editor, based on CodeMirror 6.
 *
 * This module is loaded on demand by previews.js (dynamic import), so the
 * CodeMirror code is only fetched when a text file is previewed.
 */
"use strict";

// All CodeMirror packages must share a single copy of these modules, otherwise
// CodeMirror fails with "Unrecognized extension value ... multiple instances".
// esm.sh resolves the shared dependencies to the pinned versions below.
const CM_DEPS = [
  "@codemirror/state@6.7.6",
  "@codemirror/view@6.43.15",
  "@codemirror/language@6.13.1",
  "@lezer/common@1.5.5",
  "@lezer/highlight@1.2.5",
  "@lezer/lr@1.4.12",
].join(",");

/**
 * Return the esm.sh URL of a package that is imported directly.
 *
 * esm.sh builds a separate copy of a module for each distinct `deps` list that
 * is not a subset of its real dependencies. The core packages (that other
 * packages import too) must therefore be requested with exactly the `deps`
 * that esm.sh uses when resolving them as a dependency:
 * `@codemirror/state` has none, `@codemirror/view` only depends on state.
 */
function esm(spec, deps = CM_DEPS) {
  return deps ? `https://esm.sh/${spec}?deps=${deps}` : `https://esm.sh/${spec}`;
}

const [{ basicSetup }, { Compartment, EditorState, Prec }, { EditorView, keymap }, { oneDark }] = await Promise.all([
  import(esm("codemirror@6.0.2")),
  import(esm("@codemirror/state@6.7.6", null)),
  import(esm("@codemirror/view@6.43.15", "@codemirror/state@6.7.6")),
  import(esm("@codemirror/theme-one-dark@6.1.3")),
]);

/** Load a language from `@codemirror/legacy-modes` (StreamLanguage). */
async function legacyMode(file, name) {
  // `language` depends on all other CM_DEPS packages
  const languageDeps = CM_DEPS.split(",")
    .filter((d) => !d.startsWith("@codemirror/language@"))
    .join(",");
  const [{ StreamLanguage }, mod] = await Promise.all([import(esm("@codemirror/language@6.13.1", languageDeps)), import(esm(`@codemirror/legacy-modes@6.5.5/mode/${file}`))]);
  return StreamLanguage.define(mod[name]);
}

// Keys are the `lang` values in previews.js `fileTypeInfo`
const LANGUAGE_LOADERS = {
  css: async () => (await import(esm("@codemirror/lang-css@6.3.1"))).css(),
  html: async () => (await import(esm("@codemirror/lang-html@6.4.12"))).html(),
  javascript: async () => (await import(esm("@codemirror/lang-javascript@6.2.5"))).javascript(),
  jsx: async () => (await import(esm("@codemirror/lang-javascript@6.2.5"))).javascript({ jsx: true }),
  typescript: async () => (await import(esm("@codemirror/lang-javascript@6.2.5"))).javascript({ typescript: true }),
  tsx: async () => (await import(esm("@codemirror/lang-javascript@6.2.5"))).javascript({ jsx: true, typescript: true }),
  json: async () => (await import(esm("@codemirror/lang-json@6.0.2"))).json(),
  markdown: async () => (await import(esm("@codemirror/lang-markdown@6.5.2"))).markdown(),
  python: async () => (await import(esm("@codemirror/lang-python@6.2.1"))).python(),
  xml: async () => (await import(esm("@codemirror/lang-xml@6.1.0"))).xml(),
  yaml: async () => (await import(esm("@codemirror/lang-yaml@6.1.3"))).yaml(),
  powershell: () => legacyMode("powershell.js", "powerShell"),
  properties: () => legacyMode("properties.js", "properties"),
  shell: () => legacyMode("shell.js", "shell"),
  toml: () => legacyMode("toml.js", "toml"),
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
