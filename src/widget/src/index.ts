import { QuasarChat } from "./chat-widget";

if (!customElements.get("quasar-chat")) {
  customElements.define("quasar-chat", QuasarChat);
}
