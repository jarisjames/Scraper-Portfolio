// content.js
console.log("[handoff] content.js loaded");

const selectorMap = {
  "chatgpt.com":       ".bg-token-message-surface .whitespace-pre-wrap",
  "claude.ai":             ".chat-message",
  // Copilot bubbles
  "copilot.microsoft.com": "div[id*='-content-']"
};

// selector for your own (user) messages in Copilot
const userSelector = "div.font-ligatures-none.self-end";

function getScrollContainer(sel) {
  const sample = document.querySelector(sel);
  if (!sample) return null;
  let el = sample.parentElement;
  while (el && el !== document.body) {
    const style = getComputedStyle(el);
    if ((style.overflowY === "auto" || style.overflowY === "scroll")
        && el.scrollHeight > el.clientHeight) {
      return el;
    }
    el = el.parentElement;
  }
  return null;
}

// scroll up, grab both user & cop messages, batch by batch, until nothing new
async function loadAllAndExtract(isCop, copSel, userSel) {
  const container = getScrollContainer(copSel) || window;
  const seen = new Set();
  const batches = [];

  while (true) {
    // scroll to top
    if (container === window) window.scrollTo(0, 0);
    else container.scrollTop = 0;
    container.dispatchEvent(new Event("scroll", { bubbles: true }));
    await new Promise(r => setTimeout(r, 500));

    const nodes = Array.from(
      document.querySelectorAll(`${copSel}, ${userSel}`)
    );
    console.log(`[handoff] total nodes found: ${nodes.length}`);

    const batch = [];
    nodes.forEach(node => {
      let role, text = "";

      if (isCop && node.matches(copSel)) {
        role = "copilot";
        node.querySelectorAll("span.font-ligatures-none").forEach(s => {
          const t = s.innerText.trim();
          if (t && !t.includes("[object Object]")) text += t + " ";
        });
        text = text.trim();
      }
      else if (isCop && node.matches(userSel)) {
        role = "user";
        text = node.innerText.trim();
      }
      else if (!isCop) {
        // fallback for non-Copilot sites
        role = "ai";
        text = node.innerText.trim();
      } else {
        return; // neither user nor cop match
      }

      if (text) {
        const key = `${role}:${text}`;
        if (!seen.has(key)) {
          seen.add(key);
          batch.push({ role, text });
        }
      }
    });

    console.log(`[handoff] new batch size: ${batch.length}`);
    if (!batch.length) break;
    batches.push(batch);
  }

  // restore scroll to bottom
  if (container === window) window.scrollTo(0, document.body.scrollHeight);
  else container.scrollTop = container.scrollHeight;

  // flatten batches in reverse so oldest-first
  const memory = [];
  let id = 0;
  for (let i = batches.length - 1; i >= 0; i--) {
    for (const msg of batches[i]) {
      memory.push({
        id: id++,
        role: msg.role,
        content: msg.text
      });
    }
  }
  return memory;
}

async function extractSession() {
  const host    = window.location.hostname;
  const isCop   = host.includes("copilot.microsoft.com");
  const copSel  = selectorMap[host] || ".message";

  console.log(`[handoff] extractSession host=${host} selector="${copSel}"`);
  let memory = [];

  if (isCop) {
    console.log("[handoff] loading & extracting ALL chats (user + copilot)...");
    memory = await loadAllAndExtract(isCop, copSel, userSelector);

  } else if (host.includes("claude.ai")) {
    // ——— Claude: interleave user & AI in DOM order ———
    const claudeNodes = document.querySelectorAll(
      "p.whitespace-pre-wrap.break-words, p.whitespace-normal.break-words"
    );
    claudeNodes.forEach((node, i) => {
      const role = node.classList.contains("whitespace-pre-wrap")
        ? "user"
        : "ai";
      const text = node.innerText.trim();
      if (text) memory.push({ id: i, role, content: text });
    });

  } else if (host.includes("chatgpt.com")) {
    // ——— ChatGPT: interleave user & AI in DOM order ———
    const userSelChat = selectorMap["chatgpt.com"];
    const aiSelChat   = "div.markdown.prose p";

    const chatNodes = document.querySelectorAll(
      `${userSelChat}, ${aiSelChat}`
    );
    chatNodes.forEach((node, i) => {
      const role = node.matches(userSelChat) ? "user" : "ai";
      const text = node.innerText.trim();
      if (text) memory.push({ id: i, role, content: text });
    });

  } else {
    // non‑Copilot, non‑Claude, non‑ChatGPT fallback
    document.querySelectorAll(copSel).forEach((node, i) => {
      const txt = node.innerText.trim();
      if (txt) memory.push({ id: i, role: "ai", content: txt });
    });
  }

  console.log(`[handoff] scraped total: ${memory.length} msgs`);
  chrome.storage.local.set({ memorySession: memory });
  showDebugOverlay(memory);
}

function showDebugOverlay(memory) {
  const existing = document.getElementById("handoff-debug-overlay");
  if (existing) existing.remove();

  const o = document.createElement("div");
  o.id = "handoff-debug-overlay";
  Object.assign(o.style, {
    position:   "fixed", bottom: "16px", right: "16px",
    background: "#111",   color: "#fff",
    padding:    "12px",   borderRadius: "8px",
    fontFamily: "monospace", fontSize: "12px",
    whiteSpace: "pre-wrap",  maxWidth: "300px",
    boxShadow:  "0 4px 12px rgba(0,0,0,0.3)", zIndex: 9999
  });

  const title = `🧠 ${memory.length} msgs`;
  const preview = memory.slice(0, 3)
    .map(m => `• ${m.role}: ${m.content.slice(0, 50)}…`)
    .join("\n") || "No messages found.";

  o.textContent = `${title}\n\n${preview}`;

  const x = document.createElement("div");
  x.textContent = "✖";
  Object.assign(x.style, {
    position: "absolute", top: "4px", right: "6px",
    cursor:   "pointer",  color: "#bbb", fontSize: "14px"
  });
  x.onclick = () => o.remove();
  o.appendChild(x);

  document.body.appendChild(o);
}

chrome.runtime.onMessage.addListener((req, sender, sendResponse) => {
  if (req.action === "save") {
    extractSession().then(() => sendResponse({ status: "done" }));
    return true;
  }
});
