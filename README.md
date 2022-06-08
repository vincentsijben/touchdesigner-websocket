# touchdesigner-websocket

Open `touchdesigner.xd` and install plugin "Web Export" from Velara 3.
When installed, select any element and choose **Plugins -> Web Export -> Element options**.

Add the class `touchdesigner` to any element you want to click and send the websocket message from.
In the attributes field, add `data-touchdesigner="mydata"`. The string "mydata" will be sent if you click the button in the final result. You can check the blue button to see some added element options.
If you omit this data-touchdesigner, the generated id from the xd component will be sent.

When you're done selecting and adding meta data to your elements, go to **Plugins - Web Export - Export artboard**. The `index.html` you'll find in this repo is an example export.

In your exported `index.html` add the following line just before the `</body>`:

```
<script src="touchdesigner.js"></script>
```

Open `webserver.toe` and press button1. You'll see the text in text1 change.