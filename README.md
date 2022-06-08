# touchdesigner-websocket
This repo includes some example files to create a UI in Adobe XD (and eventually exported as HTML), to control a text component in TouchDesigner by using websockets.

Open `touchdesigner.xd` and install plugin "Web Export" from Velara 3.
When installed, select any element and choose **Plugins -> Web Export -> Element options**.

Add the class `touchdesigner` to any element you want to click and send the websocket message from.
In the attributes field, add `data-touchdesigner="mydata"`. The string `mydata` will be sent if you click the button in the final result. You can check the blue button to see some added element options.
If you omit this data-touchdesigner attribute, the generated id from the xd component will be sent.

When you're done selecting and adding meta data to your elements, go to **Plugins - Web Export - Export artboard**. The `index.html` you'll find in this repo is an example export.

In your exported `index.html` add the following line just before the `</body>`:`<script src="touchdesigner.js"></script>`.
Every time you export, you'll overwrite existing code and you'll have to add this script line again.

Open `webserver.toe` in TouchDesigner and open the `index.html` in your browser. Click button1 and you'll see component text1 change.