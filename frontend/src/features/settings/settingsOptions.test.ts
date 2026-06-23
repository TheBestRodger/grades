import { describe, expect, it } from "vitest";

import { defaultProvider, modeOptions, providerOptions } from "./settingsOptions";

describe("settingsOptions", () => {
  it("contains supported AI modes", () => {
    expect(modeOptions.map((option) => option.value)).toEqual(["default", "off", "local", "token"]);
  });

  it("returns first provider for selected mode", () => {
    expect(defaultProvider("default")).toBe("off");
    expect(defaultProvider("off")).toBe("off");
    expect(defaultProvider("local")).toBe("ollama");
    expect(defaultProvider("token")).toBe("openai_compatible");
  });

  it("keeps provider lists scoped by mode", () => {
    expect(providerOptions.local.map((option) => option.value)).toEqual(["ollama", "lm_studio"]);
    expect(providerOptions.token).toHaveLength(1);
  });
});
