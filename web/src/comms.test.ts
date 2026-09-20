import { describe, expect, it } from "vitest";
import { modeFromSnapshot, type ChannelStatus } from "./comms";

describe("communication mode honesty", () => {
  it("is online only when internet is available", () => {
    const channels: ChannelStatus[] = [
      { id: "internet", available: true, reason: "ok" },
      { id: "local_network", available: false, reason: "no" },
    ];
    expect(modeFromSnapshot(channels)).toBe("ONLINE");
  });

  it("does not claim online when only local hub exists", () => {
    const channels: ChannelStatus[] = [
      { id: "internet", available: false, reason: "down" },
      { id: "local_network", available: true, reason: "hub" },
    ];
    expect(modeFromSnapshot(channels)).toBe("LOCAL_EMERGENCY_NETWORK");
  });
});
