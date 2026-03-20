import { WIDGET_STYLES } from "./styles";
import { runFlow } from "./api";

const CHAT_ICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z"/></svg>`;

const CLOSE_ICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;

const SEND_ICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>`;

export class QuasarChat extends HTMLElement {
  private shadow: ShadowRoot;
  private flowId = "";
  private apiKey = "";
  private hostUrl = "";
  private flowName = "Chat";
  private isOpen = false;
  private isSending = false;

  constructor() {
    super();
    this.shadow = this.attachShadow({ mode: "open" });
  }

  connectedCallback(): void {
    this.flowId = this.getAttribute("data-flow-id") || "";
    this.apiKey = this.getAttribute("data-api-key") || "";
    this.hostUrl =
      this.getAttribute("data-host-url") || window.location.origin;
    this.flowName = this.getAttribute("data-flow-name") || "Chat";
    this.render();
    this.wireEvents();
  }

  private render(): void {
    this.shadow.innerHTML = `
      <style>${WIDGET_STYLES}</style>

      <button class="toggle-btn" aria-label="Open chat">
        ${CHAT_ICON_SVG}
      </button>

      <div class="chat-window hidden">
        <div class="chat-header">
          <span class="chat-header-title">${this.escapeHtml(this.flowName)}</span>
          <button class="close-btn" aria-label="Close chat">
            ${CLOSE_ICON_SVG}
          </button>
        </div>
        <div class="message-list" role="log" aria-live="polite"></div>
        <div class="input-area">
          <input
            class="chat-input"
            type="text"
            placeholder="Type a message..."
            aria-label="Chat message input"
          />
          <button class="send-btn" aria-label="Send message">
            ${SEND_ICON_SVG}
          </button>
        </div>
      </div>
    `;
  }

  private wireEvents(): void {
    const toggleBtn = this.shadow.querySelector(
      ".toggle-btn",
    ) as HTMLButtonElement;
    const closeBtn = this.shadow.querySelector(
      ".close-btn",
    ) as HTMLButtonElement;
    const sendBtn = this.shadow.querySelector(
      ".send-btn",
    ) as HTMLButtonElement;
    const input = this.shadow.querySelector(
      ".chat-input",
    ) as HTMLInputElement;
    const chatWindow = this.shadow.querySelector(
      ".chat-window",
    ) as HTMLDivElement;

    toggleBtn.addEventListener("click", () => {
      this.isOpen = !this.isOpen;
      chatWindow.classList.toggle("hidden", !this.isOpen);
      toggleBtn.classList.toggle("window-open", this.isOpen);
      toggleBtn.setAttribute(
        "aria-label",
        this.isOpen ? "Close chat" : "Open chat",
      );
      if (this.isOpen) {
        input.focus();
      }
    });

    closeBtn.addEventListener("click", () => {
      this.isOpen = false;
      chatWindow.classList.add("hidden");
      toggleBtn.classList.remove("window-open");
      toggleBtn.setAttribute("aria-label", "Open chat");
      toggleBtn.focus();
    });

    sendBtn.addEventListener("click", () => {
      this.handleSend();
    });

    input.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.handleSend();
      }
    });

    this.shadow.addEventListener("keydown", (e: Event) => {
      if ((e as KeyboardEvent).key === "Escape" && this.isOpen) {
        this.isOpen = false;
        chatWindow.classList.add("hidden");
        toggleBtn.classList.remove("window-open");
        toggleBtn.setAttribute("aria-label", "Open chat");
        toggleBtn.focus();
      }
    });
  }

  private async handleSend(): Promise<void> {
    const input = this.shadow.querySelector(
      ".chat-input",
    ) as HTMLInputElement;
    const text = input.value.trim();
    if (!text || this.isSending) return;

    input.value = "";
    this.addMessage(text, "user");
    this.showTypingIndicator();
    this.isSending = true;

    // Disable send button while sending
    const sendBtn = this.shadow.querySelector(
      ".send-btn",
    ) as HTMLButtonElement;
    sendBtn.disabled = true;

    try {
      const reply = await runFlow(
        this.hostUrl,
        this.flowId,
        this.apiKey,
        text,
      );
      this.hideTypingIndicator();
      this.addMessage(reply, "bot");
    } catch (err) {
      this.hideTypingIndicator();
      this.showError(
        err instanceof Error ? err.message : "Failed to send. Try again.",
      );
    } finally {
      this.isSending = false;
      sendBtn.disabled = false;
    }
  }

  private addMessage(text: string, sender: "user" | "bot"): void {
    const messageList = this.shadow.querySelector(
      ".message-list",
    ) as HTMLDivElement;
    const div = document.createElement("div");
    div.className = `message message-${sender}`;
    div.textContent = text;
    messageList.appendChild(div);
    messageList.scrollTop = messageList.scrollHeight;
  }

  private showTypingIndicator(): void {
    const messageList = this.shadow.querySelector(
      ".message-list",
    ) as HTMLDivElement;
    const indicator = document.createElement("div");
    indicator.className = "typing-indicator";
    indicator.innerHTML = `
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    `;
    messageList.appendChild(indicator);
    messageList.scrollTop = messageList.scrollHeight;
  }

  private hideTypingIndicator(): void {
    const indicator = this.shadow.querySelector(".typing-indicator");
    if (indicator) {
      indicator.remove();
    }
  }

  private showError(message: string): void {
    const inputArea = this.shadow.querySelector(
      ".input-area",
    ) as HTMLDivElement;

    // Remove any existing error
    const existing = this.shadow.querySelector(".error-text");
    if (existing) existing.remove();

    const errorDiv = document.createElement("div");
    errorDiv.className = "error-text";
    errorDiv.textContent = message;
    inputArea.insertAdjacentElement("afterend", errorDiv);

    setTimeout(() => {
      errorDiv.remove();
    }, 5000);
  }

  private escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}
