// sample implementation of application/davmount+xml
// dispatcher for Windows Webfolder client
//
// to install/uninstall:
//        wscript davmount.js
//
// to open the webfolder:
//        wscript davmount.js filename
// (where filename refers to an XML document with MIME type
// application/davmount+xml)

var EXTENSION = ".davmount";
var MIMETYPE = "application/davmount+xml";
var REGKW = "WebDAV.mount";
var NS = "xmlns:m='http://purl.org/NET/webdav/mount";

// remove keys/entries from the registry

function regdel(shell, key) {
    try {
        var x = shell.RegRead(key);
        try {
            shell.RegDelete(key);
        } catch(e) {
        	WScript.Echo("Error removing key " + key + ": " + e);
        }
    } catch(e) {
    	// entry not present
    }
}

// methods for registering/unregistering the handler

function install() {
	var WshShell = new ActiveXObject("WScript.Shell");
	if (WshShell == null) {
		WScript.Echo("Couldn't instantiate WScript.Shell object");
		return 2;
	}

	var fso = new ActiveXObject("Scripting.FileSystemObject");
	var RegExt = "HKCR\\" + EXTENSION + "\\";
	var RegMimeType = "HKCR\\MIME\\DataBase\\Content Type\\"
		+ MIMETYPE + "\\";
	var RegKw = "HKCR\\" + REGKW + "\\";
	var extension = null;
	try {
		extension = WshShell.RegRead(RegMimeType + "Extension");
	} catch (e) {
	}

	if (extension == null) {
		var but = WshShell.popup("Install the dispatcher for mime type "
				+ MIMETYPE + "?", 0, MIMETYPE + " installation", 4);
		if (but == 6) {
			try {
				WshShell.RegWrite(RegExt, REGKW);
				WshShell.RegWrite(RegExt + "Content Type", MIMETYPE);
				WshShell.RegWrite(RegMimeType + "Extension", EXTENSION);
				WshShell.RegWrite(RegKw, "WebDAV Mount Request");
				WshShell.RegWrite(RegKw + "DefaultIcon\\",
					"shell32.dll,103");
				var path = fso.getAbsolutePathName("davmount.js");
				WshShell.RegWrite(RegKw + "shell\\open\\command\\",
						"%SystemRoot%\\system32\\wscript.exe /nologo \""
						+ path + "\" \"%1\"", "REG_EXPAND_SZ");
			} catch (e) {
				WScript.Echo("Error writing to registry");
				return 1;
			}
			return 0;
		} else {
			return 1;
		}
	} else {
		var but = WshShell.popup("Remove the dispatcher for mime type "
				+ MIMETYPE + "?", 0, MIMETYPE + " installation", 4);

		if (but == 6) {
			regdel(WshShell, RegExt + "Content Type");
			regdel(WshShell, RegExt);
			regdel(WshShell, RegKw + "shell\\open\\command\\");
			regdel(WshShell, RegKw + "DefaultIcon\\");
			regdel(WshShell, RegKw);
			regdel(WshShell, RegMimeType + "Extension");
			regdel(WshShell, RegMimeType);
			return 0;
		} else {
			return 1;
		}
 	}
}


if (WScript.Arguments.length == 0) {
	// install/uninstall
	WScript.Quit(install());
} else {
	// try to invoke Webfolder

	var inp = new ActiveXObject("MSXML2.DOMDocument");
	var furi = encodeURI(WScript.Arguments(0));
	if (! inp.load(furi)) {
		WScript.Echo("Can't read from '"
				+ WScript.Arguments(0) + "'!");
		WScript.Quit(2);
	}

	inp.setProperty("SelectionLanguage", "XPath");
	inp.setProperty("SelectionNamespaces",
		"xmlns:m='http://purl.org/NET/webdav/mount'");

	var n1 = inp.selectSingleNode("/m:mount/m:url");
	var n2 = inp.selectSingleNode("/m:mount/m:open");

	if (n1 == null) {
		WScript.Echo("<url> element missing.");
		WScript.Quit(2);
	}

	var ie = new ActiveXObject("InternetExplorer.Application");

	ie.Navigate("about:blank");
	var doc = ie.Document;

	var folder = doc.createElement("span");
	folder.addBehavior("#default#httpFolder");

	var result = folder.navigate(n1.text +
			(n2 == null ? "" : n2.text));

	// close the window again when there was no <open> element
	if (n2 == null) ie.Quit();

	if (result != "OK") {
		if (result == "PROTOCOL_NOT_SUPPORTED") {
			WScript.Echo("This site doesn't seem to support WebDAV.");
			WScript.Quit(1);
		} else {
			WScript.Echo("Unexpected status: " + result);
			WScript.Quit(2);
		}
	}
}
