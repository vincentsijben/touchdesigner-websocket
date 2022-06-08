
(() => {
    let port = 9980;
    const socket = new WebSocket(`ws://localhost:${port}`)
    let buttons = document.querySelectorAll(".touchdesigner");
    buttons.forEach(e => {
        e.addEventListener("click", function (event) {
            let data_touchdesigner = e.getAttribute("data-touchdesigner");
            if (data_touchdesigner === null) data_touchdesigner = e.getAttribute("id");
            socket.send(data_touchdesigner);
        });
    })
})()
