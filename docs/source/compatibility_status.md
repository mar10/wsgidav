| Feature                 | Windows | macOS/Safari | Linux | Edge | Chrome | FF  |
| ----------------------- | ------- | ------------ | ----- | ---- | ------ | --- |
| Drag browser -> desktop | OK      | (1)          |       |      |        |     |
| Drag desktop -> browser |         |              |       |      |        |     |
| Drag browser -> browser |         |              |       |      |        |     |
| Native PDF preview      |         |              |       |      | ?      | ?   |
| Edit OpenOffice         |         |              |       |      | ?      | ?   |
| Edit MS Office          |         |              |       |      | ?      | ?   |

## Drag / Drop

### (1) Drag browser -> desktop

Works on Windows and Linux, but may have limitations on macOS/Safari.
Safari creates a `.webloc` file instead of the actual file.
Firefox on macOS creates a `.webloc` file instead of the actual file.
Chromium on macOS works.
Edge on macOS works.

Only Chromium based browsers (Chrome, Edge, ...) support the `DownloadURL`
drag type that creates the actual file. Safari and Firefox drop a link to the
file instead, and DAV Explorer shows a one-time hint when this happens.

### Drag desktop -> browser

### Drag browser -> browser

## Edit / Preview

### Edit OpenOffice

### Edit MS Office

### Native PDF preview
