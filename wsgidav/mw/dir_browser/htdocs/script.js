// Cached plugin reference (or null. if it could not be instantiated)
var sharePointPlugin = undefined;

function onLoad() {
//    console.log("loaded.");
}


/**
 * Find (and cache) an available ActiveXObject Sharepoint plugin.
 *
 * @returns {ActiveXObject} or null
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
					window.console && console.warn("Could not create ActiveXObject('SharePoint.OpenDocuments'): (requires IE <= 11 and matching security settings.");
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
 * Open an MS Office document either with SharePoint plugin or using the 'ms-' URL prefix.
 *
 * @param {object} opts
 * @returns {boolean} true if the URL could be opened
 */
function openWebDavDocument(opts) {
	var ofe_link = opts.ofe + opts.href,  // (e.g. 'ms-word:ofe|u|http://server/path/file.docx')
		url = opts.href;

	var plugin = getSharePointPlugin();
	var res = false;

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
			res = true;
		}
	}
	return res;
}


/**
 * Event delegation handler for clicks on a-tags with class 'msoffice'.
 */
function onClickTable(event) {
	var target = event.target || event.srcElement,
		opts = {
			href: target.href,
			ofe: target.getAttribute("data-ofe")
		};

    if( target.className === "msoffice" ){
        if( openWebDavDocument(opts) ){
            // prevent default processing if the document could be opened
            return false;
        }
    }
}
