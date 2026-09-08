import { createStore } from "/js/AlpineStore.js";

export const store = createStore("file_browser_s3", {
  async open() {
    try {
      const { store: files } = await import("/components/modals/file-browser/file-browser-store.js");
      if (typeof files.loadConnections !== "function") throw new Error("Update Agent Zero to a version with the File Browser connection provider interface.");
      await files.openSettings("s3");
    } catch (error) {
      globalThis.toastFrontendError?.(error.message, "File Browser S3 access");
    }
  },
});
