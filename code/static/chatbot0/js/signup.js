/* chatbot0 sign-up (templates/chatbot0/signup.html). Ported from zer0-frontend-web signUpPage.tsx:
   same fields, same validation, same three API calls in the same order and with the same payloads,
   then the embed script with a copy button.

   The API is this same Flask service. Paths are root-absolute ("/domains/", not "domains/"): on the
   Cloud Run URL the page is at /chatbot0/signup and the API at the root; on chatbot0.smalltech.in the
   page is at /signup and register_host_routing lets every non-page path and every non-GET request through
   to the API. Either way "/domains/" is the API. */
(function () {
  "use strict";

  var API_URL = "";
  // The widget is still hosted on zer0.smalltech.in; keep this exactly as signUpPage.tsx builds it.
  var WIDGET_ORIGIN = "https://zer0.smalltech.in";

  function track(name, params) {
    if (window.stTrack) window.stTrack(name, params || {});
  }

  function $(id) { return document.getElementById(id); }

  function init() {
    var form = $("signup-form");
    if (!form) return;

    var nameEl = $("su-name");
    var websiteEl = $("su-website");
    var emailEl = $("su-email");
    var phoneEl = $("su-phone");
    var promptEl = $("su-prompt");
    var pickerEl = $("su-colour-picker");
    var colourEl = $("su-colour");
    var submitEl = $("signup-submit");
    var errorEl = $("signup-error");
    var formStep = $("signup-form-step");
    var doneStep = $("signup-done-step");
    var embedEl = $("signup-embed");
    var copyEl = $("signup-copy");
    var methodButtons = form.querySelectorAll("[data-contact-method]");
    var swatches = form.querySelectorAll("[data-colour]");
    var previews = document.querySelectorAll("[data-colour-preview]");

    var contactMethod = "email";
    var colour = colourEl.value;
    var isSubmitting = false;
    var embedScript = "";
    var formStartTracked = false;
    var SUBMIT_LABEL = submitEl.textContent;

    function isFormValid() {
      return nameEl.value.trim() !== "" &&
        websiteEl.value.trim() !== "" &&
        (contactMethod === "email" ? emailEl.value.trim() !== "" : phoneEl.value.trim() !== "");
    }

    function refreshSubmit() {
      submitEl.disabled = !isFormValid() || isSubmitting;
    }

    function setContactMethod(method) {
      contactMethod = method;
      var email = method === "email";
      // Only the active field is shown, required and validated, as in the original (one input rendered at a time).
      emailEl.hidden = !email; emailEl.disabled = !email; emailEl.required = email;
      phoneEl.hidden = email; phoneEl.disabled = email; phoneEl.required = !email;
      for (var i = 0; i < methodButtons.length; i++) {
        var b = methodButtons[i];
        b.setAttribute("aria-pressed", String(b.getAttribute("data-contact-method") === method));
      }
      refreshSubmit();
    }

    function setColour(value, from) {
      colour = value;
      if (from !== "text") colourEl.value = value;
      if (from !== "picker" && /^#[0-9A-Fa-f]{6}$/.test(value)) pickerEl.value = value.toLowerCase();
      for (var i = 0; i < previews.length; i++) previews[i].style.background = value;
      for (var j = 0; j < swatches.length; j++) {
        swatches[j].setAttribute("aria-pressed", String(swatches[j].getAttribute("data-colour") === value));
      }
    }

    function showError(message) {
      errorEl.textContent = message || "";
      errorEl.hidden = !message;
    }

    function jsonPost(path, method, body) {
      return fetch(API_URL + path, {
        method: method,
        headers: { accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
    }

    async function handleSubmit(e) {
      e.preventDefault();
      if (!isFormValid() || isSubmitting) return;
      isSubmitting = true;
      submitEl.textContent = "Setting up your agent…";
      refreshSubmit();
      showError(null);

      var name = nameEl.value.trim();
      var website = websiteEl.value.trim();
      var customPrompt = promptEl.value.trim();

      try {
        // 1. Register the domain, with who is signing up
        var domainBody = { website_url: website, contact_name: name };
        if (contactMethod === "email") domainBody.email = emailEl.value.trim();
        else domainBody.mobile = phoneEl.value.trim();
        var domainRes = await jsonPost("/domains/", "POST", domainBody);
        if (domainRes.status === 409) {
          throw new Error("This website is already signed up. Write to us at contact@smalltech.in and we'll help.");
        }
        if (domainRes.status === 422) {
          throw new Error("Please check your website address, email or phone number.");
        }
        if (!domainRes.ok) throw new Error("Failed to register domain. Please try again.");
        var domainData = await domainRes.json();

        // 2. Save custom prompt (company description)
        if (customPrompt) {
          var promptRes = await jsonPost("/prompt", "POST", {
            domain: domainData.key,
            agent_type: "sales",
            type: "company",
            text: customPrompt
          });
          if (!promptRes.ok) console.warn("Prompt save failed, continuing...");
        }

        // 3. Build the embed script tag
        embedScript = "<script\n  src=\"" + WIDGET_ORIGIN + "/embed.js\"\n  data-chat-url=\"" + WIDGET_ORIGIN +
          "/embed\"\n  data-colour=\"" + colour + "\"\n  data-tagline=\"Chat with us\"\n  defer\n></" + "script>";
        embedEl.textContent = embedScript;
        track("sign_up", { method: "chatbot0" });
        formStep.hidden = true;
        doneStep.hidden = false;
        window.scrollTo(0, 0);
        var title = $("signup-done-title");
        if (title) title.focus();
      } catch (err) {
        showError(err instanceof Error ? err.message : "Something went wrong.");
        track("signup_error", { method: "chatbot0" });
      } finally {
        isSubmitting = false;
        submitEl.textContent = SUBMIT_LABEL;
        refreshSubmit();
      }
    }

    function copied() {
      copyEl.textContent = "Copied!";
      track("embed_code_copy", { method: "chatbot0" });
      setTimeout(function () { copyEl.textContent = "Copy"; }, 2500);
    }

    // Older browsers and non-HTTPS pages have no navigator.clipboard: select the code and copy it instead.
    function copyBySelection() {
      var range = document.createRange();
      range.selectNodeContents(embedEl);
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      if (ok) { sel.removeAllRanges(); copied(); }
    }

    function copyToClipboard() {
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(embedScript).then(copied, copyBySelection);
      } else {
        copyBySelection();
      }
    }

    // Wire up
    form.addEventListener("submit", handleSubmit);
    form.addEventListener("input", refreshSubmit);
    nameEl.addEventListener("focus", function () {
      if (formStartTracked) return;
      formStartTracked = true;
      track("signup_form_start", { method: "chatbot0" });
    });
    for (var i = 0; i < methodButtons.length; i++) {
      methodButtons[i].addEventListener("click", function () {
        setContactMethod(this.getAttribute("data-contact-method"));
      });
    }
    for (var j = 0; j < swatches.length; j++) {
      swatches[j].style.background = swatches[j].getAttribute("data-colour");
      swatches[j].addEventListener("click", function () { setColour(this.getAttribute("data-colour")); });
    }
    pickerEl.addEventListener("input", function () { setColour(pickerEl.value, "picker"); });
    colourEl.addEventListener("input", function () { setColour(colourEl.value, "text"); });
    copyEl.addEventListener("click", copyToClipboard);
    $("signup-restart").addEventListener("click", function () {
      doneStep.hidden = true;
      formStep.hidden = false;
      embedScript = "";
      embedEl.textContent = "";
      window.scrollTo(0, 0);
    });

    setContactMethod("email");
    setColour(colour);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
