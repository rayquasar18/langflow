/**
 * API client for Langflow flow execution.
 * Uses native fetch -- zero external dependencies.
 */

export async function runFlow(
  hostUrl: string,
  flowId: string,
  apiKey: string,
  message: string,
): Promise<string> {
  let response: Response;

  try {
    response = await fetch(
      `${hostUrl}/api/v1/run/${flowId}?stream=false`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": apiKey,
        },
        body: JSON.stringify({
          input_value: message,
          output_type: "chat",
          input_type: "chat",
        }),
      },
    );
  } catch {
    throw new Error("Failed to send. Try again.");
  }

  if (!response.ok) {
    throw new Error("Failed to send. Try again.");
  }

  let data: unknown;
  try {
    data = JSON.parse(await response.text());
  } catch {
    throw new Error("Failed to send. Try again.");
  }

  // Primary path: response.outputs[0].outputs[0].results.message.text
  try {
    const d = data as Record<string, unknown>;
    const outputs = d.outputs as Array<Record<string, unknown>>;
    const innerOutputs = outputs[0].outputs as Array<Record<string, unknown>>;
    const results = innerOutputs[0].results as Record<string, unknown>;
    const msg = results.message as Record<string, unknown>;
    if (typeof msg.text === "string") {
      return msg.text;
    }
  } catch {
    // Fall through to fallback
  }

  // Fallback: response.outputs[0].outputs[0].messages[0].message
  try {
    const d = data as Record<string, unknown>;
    const outputs = d.outputs as Array<Record<string, unknown>>;
    const innerOutputs = outputs[0].outputs as Array<Record<string, unknown>>;
    const messages = innerOutputs[0].messages as Array<Record<string, unknown>>;
    if (typeof messages[0].message === "string") {
      return messages[0].message;
    }
  } catch {
    // Fall through to error
  }

  throw new Error("Failed to send. Try again.");
}
