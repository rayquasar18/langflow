import getWidgetCode from "../get-widget-code";

// Mock the customGetHostProtocol
jest.mock("@/customization/utils/custom-get-host-protocol", () => ({
  customGetHostProtocol: () => ({
    protocol: "https:",
    host: "localhost:3000",
  }),
}));

describe("getWidgetCode", () => {
  const baseOptions = {
    flowId: "test-flow-123",
    flowName: "Test Flow",
    isAuth: false,
    webhookAuthEnable: false,
  };

  describe("Basic widget code generation", () => {
    it("should generate widget code with API key when isAuth is false", () => {
      const code = getWidgetCode(baseOptions);

      // Check for self-hosted script tag (no CDN)
      expect(code).toContain("<script");
      expect(code).toContain('src="https://localhost:3000/widget.js"');
      expect(code).toContain("</script>");
      expect(code).not.toContain("cdn.jsdelivr");

      // Check for quasar-chat component
      expect(code).toContain("<quasar-chat");
      expect(code).toContain('data-flow-name="Test Flow"');
      expect(code).toContain('data-flow-id="test-flow-123"');
      expect(code).toContain('data-host-url="https://localhost:3000"');

      // Should include data-api-key placeholder when isAuth is false
      expect(code).toContain('data-api-key="..."');

      // Check closing tag
      expect(code).toContain("</quasar-chat>");
    });

    it("should generate widget code without API key when isAuth is true", () => {
      const code = getWidgetCode({
        ...baseOptions,
        isAuth: true,
      });

      // Check for script tag
      expect(code).toContain("<script");
      expect(code).toContain("/widget.js");

      // Check for quasar-chat component
      expect(code).toContain("<quasar-chat");
      expect(code).toContain('data-flow-name="Test Flow"');
      expect(code).toContain('data-flow-id="test-flow-123"');
      expect(code).toContain('data-host-url="https://localhost:3000"');

      // Should NOT include data-api-key when isAuth is true
      expect(code).not.toContain("data-api-key");

      // Check closing tag
      expect(code).toContain("</quasar-chat>");
    });
  });

  describe("Flow ID handling", () => {
    it("should correctly embed flowId in the widget", () => {
      const code = getWidgetCode({
        ...baseOptions,
        flowId: "custom-flow-456",
      });

      expect(code).toContain('data-flow-id="custom-flow-456"');
    });

    it("should handle empty flowId", () => {
      const code = getWidgetCode({
        ...baseOptions,
        flowId: "",
      });

      expect(code).toContain('data-flow-id=""');
    });

    it("should handle flowId with special characters", () => {
      const code = getWidgetCode({
        ...baseOptions,
        flowId: "flow-with-dashes_and_underscores",
      });

      expect(code).toContain('data-flow-id="flow-with-dashes_and_underscores"');
    });

    it("should handle flowId with UUID format", () => {
      const uuid = "550e8400-e29b-41d4-a716-446655440000";
      const code = getWidgetCode({
        ...baseOptions,
        flowId: uuid,
      });

      expect(code).toContain(`data-flow-id="${uuid}"`);
    });
  });

  describe("Flow name handling", () => {
    it("should correctly embed flowName as data-flow-name", () => {
      const code = getWidgetCode({
        ...baseOptions,
        flowName: "Custom Chat Widget",
      });

      expect(code).toContain('data-flow-name="Custom Chat Widget"');
    });

    it("should omit data-flow-name when flowName is empty", () => {
      const code = getWidgetCode({
        ...baseOptions,
        flowName: "",
      });

      expect(code).not.toContain("data-flow-name");
    });

    it("should handle flowName with special characters", () => {
      const code = getWidgetCode({
        ...baseOptions,
        flowName: "Chat Widget: v1.0 (beta)",
      });

      expect(code).toContain('data-flow-name="Chat Widget: v1.0 (beta)"');
    });

    it("should handle flowName with unicode characters", () => {
      const code = getWidgetCode({
        ...baseOptions,
        flowName: "Chat Widget",
      });

      expect(code).toContain('data-flow-name="Chat Widget"');
    });
  });

  describe("Host URL handling", () => {
    it("should construct data-host-url from protocol and host", () => {
      const code = getWidgetCode(baseOptions);

      expect(code).toContain('data-host-url="https://localhost:3000"');
    });

    it("should use same host for script src and data-host-url", () => {
      const code = getWidgetCode(baseOptions);

      expect(code).toContain('src="https://localhost:3000/widget.js"');
      expect(code).toContain('data-host-url="https://localhost:3000"');
    });
  });

  describe("Authentication handling", () => {
    it("should include data-api-key attribute when isAuth is false", () => {
      const code = getWidgetCode({
        ...baseOptions,
        isAuth: false,
      });

      expect(code).toContain('data-api-key="..."');
    });

    it("should not include data-api-key attribute when isAuth is true", () => {
      const code = getWidgetCode({
        ...baseOptions,
        isAuth: true,
      });

      expect(code).not.toContain("data-api-key");
    });

    it("should handle isAuth being undefined (defaults to falsy)", () => {
      const code = getWidgetCode({
        flowId: "test-flow",
        flowName: "Test",
        isAuth: undefined,
        webhookAuthEnable: false,
      });

      // When isAuth is undefined/falsy, data-api-key should be included
      expect(code).toContain('data-api-key="..."');
    });
  });

  describe("Code structure", () => {
    it("should have proper HTML structure with script and quasar-chat tags", () => {
      const code = getWidgetCode(baseOptions);

      // Check for opening and closing script tags
      const scriptTagCount = (code.match(/<script/g) || []).length;
      const scriptCloseTagCount = (code.match(/<\/script>/g) || []).length;
      expect(scriptTagCount).toBe(1);
      expect(scriptCloseTagCount).toBe(1);

      // Check for opening and closing quasar-chat tags
      expect(code).toContain("<quasar-chat");
      expect(code).toContain("</quasar-chat>");
    });

    it("should have all required attributes in quasar-chat component", () => {
      const code = getWidgetCode(baseOptions);

      expect(code).toMatch(/data-flow-id="[^"]*"/);
      expect(code).toMatch(/data-host-url="[^"]*"/);
    });

    it("should use self-hosted widget.js (no CDN reference)", () => {
      const code = getWidgetCode(baseOptions);

      expect(code).toContain("/widget.js");
      expect(code).not.toContain("cdn.jsdelivr");
      expect(code).not.toContain("langflow-embedded-chat");
    });
  });

  describe("Edge cases", () => {
    it("should handle all parameters being empty strings", () => {
      const code = getWidgetCode({
        flowId: "",
        flowName: "",
        isAuth: false,
        webhookAuthEnable: false,
      });

      expect(code).toContain("<script");
      expect(code).toContain("<quasar-chat");
      expect(code).toContain('data-flow-id=""');
    });

    it("should handle minimum required parameters", () => {
      const code = getWidgetCode({
        flowId: "test",
        flowName: "Test",
        isAuth: false,
        webhookAuthEnable: false,
      });

      expect(code).toContain("<script");
      expect(code).toContain("<quasar-chat");
      expect(code).toContain("</quasar-chat>");
    });

    it("should produce consistent output for same inputs", () => {
      const code1 = getWidgetCode(baseOptions);
      const code2 = getWidgetCode(baseOptions);

      expect(code1).toBe(code2);
    });

    it("should handle flowId with slashes", () => {
      const code = getWidgetCode({
        ...baseOptions,
        flowId: "folder/subfolder/flow",
      });

      expect(code).toContain('data-flow-id="folder/subfolder/flow"');
    });
  });

  describe("Output format", () => {
    it("should return a string", () => {
      const code = getWidgetCode(baseOptions);

      expect(typeof code).toBe("string");
    });

    it("should start with script tag", () => {
      const code = getWidgetCode(baseOptions);

      expect(code.trimStart()).toMatch(/^<script/);
    });

    it("should be copyable HTML code", () => {
      const code = getWidgetCode(baseOptions);

      // Should be valid HTML-like syntax
      expect(code).toContain("<");
      expect(code).toContain(">");
      expect(code).not.toContain("undefined");
      expect(code).not.toContain("null");
    });
  });

  describe("Integration scenarios", () => {
    it("should work with typical production settings", () => {
      const code = getWidgetCode({
        flowId: "prod-flow-123",
        flowName: "Production Chat Bot",
        isAuth: true,
        webhookAuthEnable: false,
        copy: false,
      });

      expect(code).toContain('data-flow-id="prod-flow-123"');
      expect(code).toContain('data-flow-name="Production Chat Bot"');
      expect(code).not.toContain("data-api-key");
    });

    it("should work with typical development settings", () => {
      const code = getWidgetCode({
        flowId: "dev-flow-456",
        flowName: "Dev Chat Bot",
        isAuth: false,
        webhookAuthEnable: false,
        copy: true,
      });

      expect(code).toContain('data-flow-id="dev-flow-456"');
      expect(code).toContain('data-flow-name="Dev Chat Bot"');
      expect(code).toContain('data-api-key="..."');
    });

    it("should work when embedded in HTML documentation", () => {
      const code = getWidgetCode(baseOptions);

      // Should be valid HTML that can be embedded
      expect(code).not.toContain("{{");
      expect(code).not.toContain("}}");
      expect(code).not.toContain("${");
    });
  });
});
