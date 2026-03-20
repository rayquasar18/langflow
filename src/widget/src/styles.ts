export const WIDGET_STYLES = `
  :host {
    all: initial;
    font-family: system-ui, -apple-system, sans-serif;
  }

  *,
  *::before,
  *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  .toggle-btn {
    position: fixed;
    bottom: 24px;
    right: 24px;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: #000000;
    border: none;
    cursor: pointer;
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.16);
    transition: transform 0.2s;
  }

  .toggle-btn:hover {
    transform: scale(1.05);
  }

  .toggle-btn:focus-visible {
    outline: 2px solid #2563eb;
    outline-offset: 2px;
  }

  .toggle-btn svg {
    width: 24px;
    height: 24px;
    fill: #ffffff;
  }

  .chat-window {
    position: fixed;
    bottom: 96px;
    right: 24px;
    width: 380px;
    height: 520px;
    background: #ffffff;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
    display: flex;
    flex-direction: column;
    z-index: 9998;
    overflow: hidden;
  }

  .chat-header {
    height: 48px;
    background: #f4f4f5;
    border-radius: 12px 12px 0 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    flex-shrink: 0;
  }

  .chat-header-title {
    font-size: 14px;
    font-weight: 600;
    line-height: 1.5;
    color: #18181b;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .close-btn {
    width: 28px;
    height: 28px;
    border-radius: 6px;
    border: none;
    background: transparent;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #71717a;
  }

  .close-btn:hover {
    background: #e4e4e7;
  }

  .close-btn:focus-visible {
    outline: 2px solid #2563eb;
    outline-offset: 2px;
  }

  .close-btn svg {
    width: 16px;
    height: 16px;
  }

  .message-list {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .message {
    max-width: 80%;
    padding: 8px 12px;
    font-size: 14px;
    line-height: 1.5;
    font-family: system-ui, -apple-system, sans-serif;
    word-wrap: break-word;
    overflow-wrap: break-word;
  }

  .message-user {
    align-self: flex-end;
    background: #000000;
    color: #ffffff;
    border-radius: 12px 12px 0 12px;
  }

  .message-bot {
    align-self: flex-start;
    background: #f4f4f5;
    color: #18181b;
    border-radius: 12px 12px 12px 0;
  }

  .input-area {
    display: flex;
    border-top: 1px solid #e4e4e7;
    padding: 8px;
    gap: 8px;
    flex-shrink: 0;
  }

  .chat-input {
    flex: 1;
    border: 1px solid #e4e4e7;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
    font-family: system-ui, -apple-system, sans-serif;
    outline: none;
    background: #ffffff;
    color: #18181b;
  }

  .chat-input:focus {
    border-color: #a1a1aa;
  }

  .send-btn {
    width: 36px;
    height: 36px;
    background: #000000;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .send-btn:hover {
    background: #27272a;
  }

  .send-btn:focus-visible {
    outline: 2px solid #2563eb;
    outline-offset: 2px;
  }

  .send-btn:disabled {
    background: #a1a1aa;
    cursor: not-allowed;
  }

  .send-btn svg {
    width: 16px;
    height: 16px;
    fill: #ffffff;
  }

  .typing-indicator {
    align-self: flex-start;
    background: #f4f4f5;
    border-radius: 12px 12px 12px 0;
    padding: 8px 16px;
    display: flex;
    gap: 4px;
    align-items: center;
  }

  .typing-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #71717a;
    animation: bounce 1.4s infinite ease-in-out;
  }

  .typing-dot:nth-child(1) {
    animation-delay: 0s;
  }

  .typing-dot:nth-child(2) {
    animation-delay: 0.2s;
  }

  .typing-dot:nth-child(3) {
    animation-delay: 0.4s;
  }

  @keyframes bounce {
    0%, 80%, 100% {
      transform: translateY(0);
    }
    40% {
      transform: translateY(-6px);
    }
  }

  .error-text {
    color: #ef4444;
    font-size: 13px;
    padding: 4px 8px;
    font-family: system-ui, -apple-system, sans-serif;
  }

  .hidden {
    display: none !important;
  }

  @media (max-width: 479px) {
    .chat-window {
      width: 100vw;
      height: 100vh;
      bottom: 0;
      right: 0;
      border-radius: 0;
    }

    .chat-header {
      border-radius: 0;
    }

    .toggle-btn.window-open {
      display: none;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .typing-dot {
      animation: none;
      opacity: 0.5;
    }

    .typing-dot:nth-child(2) {
      opacity: 0.7;
    }

    .typing-dot:nth-child(3) {
      opacity: 0.9;
    }

    .toggle-btn {
      transition: none;
    }
  }
`;
