function onLoad() {
//    console.log("loaded.");
}

/* Event delegation handler for clicks on a-tags with class 'msoffice'. */
function onClickTable(event) {
    var target = event.target || event.srcElement,
        href = target.href;

    if( href && target.className === "msoffice" ){
        if( openWithSharePointPlugin(href) ){
            // prevent default processing
            return false;
        }
    }
}

function openWithSharePointPlugin(url) {
    var res = false,
        control = null,
        isFF = false;

    // Get the most recent version of the SharePoint plugin
    if( window.ActiveXObject ){
        try {
            control = new ActiveXObject("SharePoint.OpenDocuments.3"); // Office 2007
        } catch(e) {
            try {
                control = new ActiveXObject("SharePoint.OpenDocuments.2"); // Office 2003
            } catch(e2) {
                try {
                    control = new ActiveXObject("SharePoint.OpenDocuments.1"); // Office 2000/XP
                } catch(e3) {
                    window.console && console.warn("Could not create ActiveXObject('SharePoint.OpenDocuments'). Check your browsers security settings.");
                    return false;
                }
            }
        }
        if( !control ){
            window.console && console.warn("Cannot instantiate the required ActiveX control to open the document. This is most likely because you do not have Office installed or you have an older version of Office.");
        }
    } else {
        window.console && console.log("Non-IE: using FFWinPlugin Plug-in...");
        control = document.getElementById("winFirefoxPlugin");
        isFF = true;
    }

    try {
//      window.console && console.log("SharePoint.OpenDocuments.EditDocument('" + url + "')...");
        res = control.EditDocument(url);
//      window.console && console.log("SharePoint.OpenDocuments.EditDocument('" + url + "')... res = ", res);
        if( !res ){
            window.console && console.warn("SharePoint.OpenDocuments.EditDocument('" + url + "') returned false.");
        }
    } catch (e){
        window.console && console.warn("SharePoint.OpenDocuments.EditDocument('" + url + "') failed.", e);
    }
    return res;
}
