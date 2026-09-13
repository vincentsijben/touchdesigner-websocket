(() => {
  const BUTTON_RELEASE_DELAY_MS = 120;
  const buttonReleaseTimers = new WeakMap();

  function parseMessage(raw) {
    const text = String(raw || "").trim();
    if (!text) {
      return null;
    }

    const parts = text.split(":", 3);
    if (parts.length !== 3) {
      return null;
    }

    return {
      type: parts[0].trim().toLowerCase(),
      name: parts[1].trim(),
      value: parts[2].trim(),
    };
  }

  function isTruthy(value) {
    return String(value).trim().toLowerCase() === "1" ||
      String(value).trim().toLowerCase() === "true" ||
      String(value).trim().toLowerCase() === "on" ||
      String(value).trim().toLowerCase() === "yes";
  }

  function setValueLabel(controlId, value) {
    const label = document.querySelector('[data-value-for="' + controlId + '"]');
    if (label) {
      label.textContent = String(value);
    }
  }

  function toHexChannel(normalizedChannel) {
    const clamped = Math.min(Math.max(normalizedChannel, 0), 1);
    const intValue = Math.round(clamped * 255);
    return intValue.toString(16).padStart(2, "0");
  }

  function formatDisplayFloat(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return String(value);
    }
    return numeric.toFixed(4).replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1");
  }

  function normalizeNumericText(value) {
    const text = String(value || "").trim();
    if (text.includes(",") && !text.includes(".")) {
      return text.replace(",", ".");
    }
    return text;
  }

  function parseColorChannels(value) {
    const pieces = String(value)
      .split(",")
      .map((part) => parseFloat(part.trim()))
      .filter((part) => Number.isFinite(part));

    if (pieces.length < 3) {
      return null;
    }

    let channels = pieces.slice(0, 4);
    if (channels.length === 3) {
      channels.push(1);
    }

    // Normalize each channel independently so mixed formats are handled safely:
    // - TD messages are usually 0..1 floats
    // - Some senders may still send 0..255 values
    channels = channels.map((channel) => {
      const normalized = channel > 1 ? (channel / 255) : channel;
      return Math.min(Math.max(normalized, 0), 1);
    });

    return {
      r: channels[0],
      g: channels[1],
      b: channels[2],
      a: channels[3],
    };
  }

  function normalizeChannelValue(value) {
    const numeric = parseFloat(normalizeNumericText(value));
    if (!Number.isFinite(numeric)) {
      return null;
    }
    const normalized = numeric > 1 ? (numeric / 255) : numeric;
    return Math.min(Math.max(normalized, 0), 1);
  }

  function readColorInputChannels(colorInput) {
    const hex = String(colorInput.value || "#000000").replace("#", "");
    if (hex.length !== 6) {
      return { r: 0, g: 0, b: 0 };
    }
    const r = parseInt(hex.slice(0, 2), 16) / 255;
    const g = parseInt(hex.slice(2, 4), 16) / 255;
    const b = parseInt(hex.slice(4, 6), 16) / 255;
    return { r, g, b };
  }

  function applyColorChannelSlider(name, value) {
    const lname = String(name || "").toLowerCase();
    const channelValue = normalizeChannelValue(value);
    if (channelValue == null) {
      return false;
    }

    let channel = null;
    if (/(^|.*)(colorr|backgroundr|backgroundcolor1|color1)$/.test(lname)) {
      channel = "r";
    } else if (/(^|.*)(colorg|backgroundg|backgroundcolor2|color2)$/.test(lname)) {
      channel = "g";
    } else if (/(^|.*)(colorb|backgroundb|backgroundcolor3|color3)$/.test(lname)) {
      channel = "b";
    } else if (/(^|.*)(colora|coloralpha|backgrounda|backgroundalpha|backgroundcolor4|color4)$/.test(lname)) {
      channel = "a";
    }

    if (!channel) {
      return false;
    }

    const colorInput = document.getElementById("primaryColor");
    if (!colorInput) {
      return false;
    }

    const channels = readColorInputChannels(colorInput);
    channels[channel] = channelValue;

    if (channel !== "a") {
      const hex = "#" + toHexChannel(channels.r) + toHexChannel(channels.g) + toHexChannel(channels.b);
      colorInput.value = hex;
      setValueLabel("primaryColor", formatDisplayFloat(channels.r) + "," + formatDisplayFloat(channels.g) + "," + formatDisplayFloat(channels.b));
    }

    const alphaSlider = document.getElementById("backgroundAlpha");
    if (alphaSlider) {
      const alphaValue = channel === "a" ? channelValue : parseFloat(alphaSlider.value || "1");
      alphaSlider.value = Number.isFinite(alphaValue) ? alphaValue : 1;
      setValueLabel("backgroundAlpha", formatDisplayFloat(Number.isFinite(alphaValue) ? alphaValue : 1));
    }

    return true;
  }

  function findAllByDataName(baseSelector, name) {
    const requested = String(name || "").toLowerCase();
    return Array.from(document.querySelectorAll(baseSelector)).filter((element) => {
      return String(element.dataset.name || "").toLowerCase() === requested;
    });
  }

  function findOneByDataName(baseSelector, name) {
    const matches = findAllByDataName(baseSelector, name);
    return matches.length ? matches[0] : null;
  }

  function applySlider(name, value) {
    if (applyColorChannelSlider(name, value)) {
      return;
    }

    const elements = findAllByDataName('input[type="range"][data-name], input[type="number"][data-name]', name);
    if (!elements.length) {
      return;
    }

    const normalizedValue = normalizeNumericText(value);

    elements.forEach((element) => {
      element.value = normalizedValue;
      setValueLabel(element.id, formatDisplayFloat(normalizedValue));
    });
  }

  function applyToggle(name, value) {
    const checkbox = findOneByDataName('input[type="checkbox"][data-name]', name);
    if (!checkbox) {
      return;
    }

    checkbox.checked = isTruthy(value);
  }

  function applyButton(name, value) {
    const button = findOneByDataName('.td-button[data-name]', name);
    if (!button) {
      return;
    }

    const pressed = isTruthy(value);
    const existingTimer = buttonReleaseTimers.get(button);
    if (existingTimer) {
      clearTimeout(existingTimer);
      buttonReleaseTimers.delete(button);
    }

    if (pressed) {
      button.classList.add("is-pressed");
      button.setAttribute("aria-pressed", "true");
      return;
    }

    const timerId = setTimeout(() => {
      button.classList.remove("is-pressed");
      button.setAttribute("aria-pressed", "false");
      buttonReleaseTimers.delete(button);
    }, BUTTON_RELEASE_DELAY_MS);

    buttonReleaseTimers.set(button, timerId);
  }

  function applyText(name, value) {
    const radios = findAllByDataName('input[type="radio"][data-name]', name);
    if (radios.length) {
      radios.forEach((radio) => {
        radio.checked = radio.value === value;
      });
      return;
    }

    const select = findOneByDataName('select[data-name]', name);
    if (select) {
      select.value = value;
      return;
    }

    const textInput = findOneByDataName('input[type="text"][data-name]', name);
    if (textInput) {
      textInput.value = value;
      return;
    }

    const textArea = findOneByDataName('textarea[data-name]', name);
    if (textArea) {
      textArea.value = value;
    }
  }

  function applyBackgroundColor(value) {
    const colorInput = document.getElementById("primaryColor");
    if (!colorInput) {
      return;
    }

    const channels = parseColorChannels(value);
    if (!channels) {
      return;
    }

    const hex = "#" + toHexChannel(channels.r) + toHexChannel(channels.g) + toHexChannel(channels.b);
    colorInput.value = hex;

    const alphaSlider = document.getElementById("backgroundAlpha");
    if (alphaSlider) {
      alphaSlider.value = channels.a;
      setValueLabel("backgroundAlpha", formatDisplayFloat(channels.a));
    }

    setValueLabel("primaryColor", formatDisplayFloat(channels.r) + "," + formatDisplayFloat(channels.g) + "," + formatDisplayFloat(channels.b));
  }

  function applyColor(name, value) {
    const lname = String(name || "").toLowerCase();
    if (lname === "background" || lname === "color") {
      applyBackgroundColor(value);
    }
  }

  function applyIncomingMessage(rawMessage, logger) {
    const parsed = parseMessage(rawMessage);
    if (!parsed) {
      return;
    }

    if (parsed.type === "slider") {
      applySlider(parsed.name, parsed.value);
    } else if (parsed.type === "toggle") {
      applyToggle(parsed.name, parsed.value);
    } else if (parsed.type === "button") {
      applyButton(parsed.name, parsed.value);
    } else if (parsed.type === "color") {
      applyColor(parsed.name, parsed.value);
    } else if (parsed.type === "text") {
      applyText(parsed.name, parsed.value);
    }

    if (typeof logger === "function") {
      logger("applied <- " + rawMessage);
    }
  }

  window.tdReceive = {
    applyIncomingMessage,
  };
})();
