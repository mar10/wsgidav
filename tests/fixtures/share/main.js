(function () {
  console.log("main.js loaded.");
  console.log("Loading 'data.json'...", window.origin, window.location);
  fetch("data.json")
    .then((response) => {
      return response.json();
    })
    .then((data) => {
      console.log("Loading 'data.json': ", data);
    });

  // Calling a cross-origin target with a non-tandrad header should trigger a
  // preflight request:
  fetch("//localhost:5000/data.json", {
    headers: { "X-PINGOTHER": "pingpong" },
  })
    .then((response) => {
      return response.json();
    })
    .then((data) => {
      console.log("Loading 'data.json' from :5000: ", data);
    });
})();
