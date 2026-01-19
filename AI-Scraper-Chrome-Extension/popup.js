document.getElementById("save").addEventListener("click", () => {
  chrome.tabs.query({active: true, currentWindow: true}, tabs => {
    chrome.tabs.sendMessage(tabs[0].id, { action: "save" }, () => {
      alert("Memory saved locally");
    });
  });
});

document.getElementById("clear").addEventListener("click", () => {
  chrome.storage.local.clear(() => alert("Memory cleared"));
});
