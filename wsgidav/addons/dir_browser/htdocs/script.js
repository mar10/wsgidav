// Cached plugin reference (or null. if it could not be instantiated)
var sharePointPlugin = undefined;

function onLoad() {
//    console.log("loaded.");
}


/**
 *
 */
function getSharePointPlugin() {
	if( sharePointPlugin !== undefined ) {
		return sharePointPlugin;
	}
	sharePointPlugin = null;

	var plugin = document.getElementById("winFirefoxPlugin");

	if ( plugin && typeof plugin.EditDocument === "function" ) {
		window.console && console.log("Using embedded custom SharePoint plugin.");
		sharePointPlugin = plugin;
	} else if( "ActiveXObject" in window ){
		plugin = null;
		try {
			plugin = new ActiveXObject("SharePoint.OpenDocuments.3"); // Office 2007+
		} catch(e) {
			try {
				plugin = new ActiveXObject("SharePoint.OpenDocuments.2"); // Office 2003
			} catch(e2) {
				try {
					plugin = new ActiveXObject("SharePoint.OpenDocuments.1"); // Office 2000/XP
				} catch(e3) {
					window.console && console.warn("Could not create ActiveXObject('SharePoint.OpenDocuments'): (requires IE <= 11 and check security settings.");
				}
			}
		}
		if( plugin ){
			window.console && console.log("Using native SharePoint plugin.");
			sharePointPlugin = plugin;
		}
	}
	return sharePointPlugin;
}


/**
 *
 * @param {object} opts
 */
function openWebDavDocument(opts) {
	var //webDavPath = opts.webDavPath,
		// URL with a prefix like ''
		ofe_link = opts.ofe + opts.href,  // (e.g. 'ms-word:ofe|u|http://server/path/file.docx')
		url = opts.href;
		// url = window.location.protocol + "//" + window.location.host + opts.href;
		// webDavPlugin = document.getElementById("winFirefoxPlugin"),
		// fileExt = opts.fileName.split(".").pop(),
		// errorMsg = "Could not open '" + webDavPath + "'. check MS Office installation and security settings.";
		// errorMsg = getContext("msg_could_not_open_document_make_sure_program_for_file_type_installed_fmt").replace("{file_ext}", fileExt);

	var plugin = getSharePointPlugin();
	var res = false;

	alert("url " + url + ", " + ofe_link)

	if( plugin ) {
		try {
			res = plugin.EditDocument(url);
			if( res === false ) {
				window.console && console.warn("SharePoint plugin.EditDocument(" + url + ") returned false");
			}
		} catch(e) {
			window.console && console.warn("SharePoint plugin.EditDocument(" + url + ") raised an exception", e);
		}
	}
	if ( res === false ) {
		if( ofe_link ) {
			window.console && console.log("Could not use SharePoint plugin: trying " + ofe_link);
			window.open(ofe_link, "_self");
			return false;
		}
	}
	return res;
}


// /**
//  *
//  * @param {*} url
//  */
// function openWithSharePointPlugin(url) {
//     var res = false,
//         control = null,
//         isFF = false;

//     // Get the most recent version of the SharePoint plugin
//     if( "ActiveXObject" in window ){
//         try {
//             control = new ActiveXObject("SharePoint.OpenDocuments.3"); // Office 2007+
//         } catch(e) {
//             try {
//                 control = new ActiveXObject("SharePoint.OpenDocuments.2"); // Office 2003
//             } catch(e2) {
//                 try {
//                     control = new ActiveXObject("SharePoint.OpenDocuments.1"); // Office 2000/XP
//                 } catch(e3) {
//                     window.console && console.warn("Could not create ActiveXObject('SharePoint.OpenDocuments'). Check your browsers security settings.");
//                     return false;
//                 }
//             }
//         }
//         if( !control ){
//             window.console && console.warn("Cannot instantiate the required ActiveX control to open the document. This is most likely because you do not have Office installed or you have an older version of Office.");
//         }
//     } else {
//         window.console && console.warn("Non-IE: trying FFWinPlugin Plug-in...");
//         control = document.getElementById("winFirefoxPlugin");
//         isFF = true;
//     }

//     try {
//         res = control.EditDocument(url);
//         if( !res ){
//             window.console && console.warn("SharePoint.OpenDocuments.EditDocument('" + url + "') returned false.");
//         }
//     } catch (e){
//         window.console && console.warn("SharePoint.OpenDocuments.EditDocument('" + url + "') failed.", e);
//     }
//     return res;
// }


/* Event delegation handler for clicks on a-tags with class 'msoffice'. */
function onClickTable(event) {
	var target = event.target || event.srcElement,
		opts = {
			href: target.href,
			ofe: target.getAttribute("data-ofe")
		};

    if( target.className === "msoffice" ){
        if( openWebDavDocument(opts) ){
            // prevent default processing
            return false;
        }
    }
}
