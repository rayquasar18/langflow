import { customGetHostProtocol } from "@/customization/utils/custom-get-host-protocol";
import type { GetCodeType } from "@/types/tweaks";

/**
 * Function to get the widget code for the API
 * @param {string} flow - The current flow.
 * @returns {string} - The widget code
 */
export default function getWidgetCode({
  flowId,
  flowName,
  isAuth,
}: GetCodeType): string {
  const { protocol, host } = customGetHostProtocol();
  const hostUrl = `${protocol}//${host}`;

  const source = `<script src="${hostUrl}/widget.js"></script>`;

  return `${source}
<quasar-chat
  data-flow-id="${flowId}"
  data-host-url="${hostUrl}"${
    !isAuth ? `\n  data-api-key="..."` : ""
  }${flowName ? `\n  data-flow-name="${flowName}"` : ""}>
</quasar-chat>`;
}
