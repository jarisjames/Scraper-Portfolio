function openDB() {
  return indexedDB.open("HandoffVault", 1);
}

function storeMemory(memory) {
  const dbReq = openDB();
  dbReq.onupgradeneeded = e => {
    let db = e.target.result;
    db.createObjectStore("sessions", { keyPath: "timestamp" });
  };

  dbReq.onsuccess = e => {
    let db = e.target.result;
    let tx = db.transaction("sessions", "readwrite");
    let store = tx.objectStore("sessions");
    store.put(memory);
  };
}
