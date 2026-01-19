document.getElementById("rehydrate").addEventListener("click", () => {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".SHARD";

  input.onchange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const shard = JSON.parse(event.target.result);
      const messages = shard.messages || [];

      const preview = `
CONTINUITY MEMORY CARD LOADED
User: ${shard.user_id}
Platform: ${shard.platform}
Timestamp: ${shard.timestamp}
Messages:\n${messages.map(m => `• ${m.role}: ${m.content}`).join("\n")}
      `;

      chrome.tabs.query({active: true, currentWindow: true}, tabs => {
        chrome.scripting.executeScript({
          target: {tabId: tabs[0].id},
          func: (preview) => {
            const box = document.querySelector("textarea");
            if (box) box.value = preview;
          },
          args: [preview]
        });
      });
    };

    reader.readAsText(file);
  };

  input.click();
});
