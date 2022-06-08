
	(() => {
             // Initialize a new TCP connection on port 9980
		const socket = new WebSocket("ws://localhost:9980")
		let buttons = document.querySelectorAll(".touchdesigner");
        buttons.forEach(e=>{
            e.addEventListener("click", function(event){
                console.log('clicked')
                socket.send(`${e.getAttribute("id")} was clicked`)
            });
        })
        // const wipe = document.querySelector("#wipe")
              
		// wipe.onclick = () =>
        //          // Send a control message!
        //         //  socket.send(JSON.stringify({ type: "ctrl:wipe" }))
        //          socket.send("hallo, er is geklikt op een button")
	})()
