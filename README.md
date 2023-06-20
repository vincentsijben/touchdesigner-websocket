# touchdesigner-websocket
This repo includes some example files to create a UI in Adobe XD to control a text component in TouchDesigner by using websockets.

Open `touchdesigner.xd` and install plugin "Web Export" from Velara 3.
When installed, select any element and choose **Plugins -> Web Export -> Element options**.

Add the class `touchdesigner` to any element you want to click and send the websocket message from.
In the attributes field, add `data-touchdesigner="mydata"`. The string `mydata` will be sent if you click the button in the final result. You can check the hyperlink, orange and blue buttons ánd the image to see some added element options.
If you omit this data-touchdesigner attribute, the generated id from the xd component will be sent (or you can put the id in yourself, again in Element Options.

When you're done selecting and adding meta data to your elements, go to **Plugins - Web Export - Export artboard**. The `index.html` you'll find in this repo is an example export.

In the upper right corner you can see a text element with "TouchDesigner code". This is being replaced with actual Javascript code (see Element optins - Markup inside) when exported. 

This code is injected:
```
<script>
			(() => {
				let url_touchdesigner = "ws://localhost:9980";
				const socket = new WebSocket(url_touchdesigner);
				socket.onopen = function (evt) {
					console.log(`WebSocket ${url_touchdesigner} is open.`);
					let buttons = document.querySelectorAll(".touchdesigner");
					buttons.forEach(b => {
						b.addEventListener("click", function (event) {
							let data_touchdesigner = b.getAttribute("data-touchdesigner");
							if (data_touchdesigner === null) data_touchdesigner = b.getAttribute("id");
							socket.send(data_touchdesigner);
							console.log(`sent to TouchDesigner: ${data_touchdesigner}`);
						});
					})
				};
			})()
		</script>
```

Open `webserver.toe` in TouchDesigner and open the `index.html` in your browser. Click button1 and you'll see component text1 change.
