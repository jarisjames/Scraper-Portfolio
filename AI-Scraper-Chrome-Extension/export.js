document.getElementById("export").addEventListener("click", () => {
  chrome.storage.local.get("memorySession", result => {
    chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
      const tabId = tabs[0].id;

      chrome.scripting.executeScript({
        target: { tabId },
        func: () => {
          // Example: Try to extract user name from LLM UI
          let userName =
            document.querySelector(".username, .user-profile, .account-name")?.innerText?.trim() ||
            "anonymous";
          return userName;
        }
      }).then(injection => {
        const user_id = injection[0].result;
        const tabUrl = new URL(tabs[0].url);
        const platformName = tabUrl.hostname;

        const card = {
          shard_version: "1.0",
          user_id,
          platform: platformName,
          timestamp: new Date().toISOString(),
          messages: result.memorySession || []
        };

        const blob = new Blob([JSON.stringify(card, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `MemoryCard_${Date.now()}.SHARD`;
        a.click();
        URL.revokeObjectURL(url);
      });
    });
  });
});
