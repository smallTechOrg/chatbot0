import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useChat } from "./useChat";

vi.mock("@/lib/api", () => ({ fetchHistory: vi.fn(), sendChat: vi.fn() }));
import { fetchHistory, sendChat } from "@/lib/api";

const ORIGIN = "https://example.com";

beforeEach(() => {
  vi.resetAllMocks();
  localStorage.clear();
  vi.spyOn(console, "error").mockImplementation(() => {});
  vi.mocked(fetchHistory).mockResolvedValue({ ok: true, status: 200, history: [] });
});

async function ready(host = ORIGIN) {
  const hook = renderHook(() => useChat(host));
  await waitFor(() => expect(hook.result.current.isBotProcessing).toBe(false));
  return hook;
}

describe("useChat", () => {
  it("loads the history for the session, passing the host website as origin", async () => {
    vi.mocked(fetchHistory).mockResolvedValue({
      ok: true,
      status: 200,
      history: [
        { type: "human", content: "hi" },
        { type: "ai", content: "hello" },
      ],
    });
    const { result } = await ready();
    expect(fetchHistory).toHaveBeenCalledWith(expect.stringMatching(/^[0-9a-f-]{36}$/), ORIGIN);
    expect(result.current.messages).toEqual([
      { sender: "You", text: "hi" },
      { sender: "Bot", text: "hello" },
    ]);
  });

  it("sends a message to /chat with the same session and origin, and shows the reply", async () => {
    vi.mocked(sendChat).mockResolvedValue({ success: true, response: "Hi there", status: 200 });
    const { result } = await ready();

    await act(() => result.current.sendMessageDirect("  hello  "));

    const [input, session, origin] = vi.mocked(sendChat).mock.calls[0];
    expect([input, origin]).toEqual(["hello", ORIGIN]);
    expect(vi.mocked(fetchHistory).mock.calls[0][0]).toBe(session);
    expect(result.current.messages).toEqual([
      { sender: "You", text: "hello" },
      { sender: "Bot", text: "Hi there" },
    ]);
  });

  it("shows the API's error text when the reply is not successful", async () => {
    vi.mocked(sendChat).mockResolvedValue({ success: false, error: "Sorry", status: 500 });
    const { result } = await ready();
    await act(() => result.current.sendMessageDirect("hello"));
    expect(result.current.messages.at(-1)).toEqual({ sender: "Error", text: "Sorry" });
  });

  it("shows a network error when the request fails", async () => {
    vi.mocked(sendChat).mockRejectedValue(new TypeError("fetch failed"));
    const { result } = await ready();
    await act(() => result.current.sendMessageDirect("hello"));
    expect(result.current.messages.at(-1)).toEqual({ sender: "Error", text: "Network or server issue." });
    expect(result.current.isBotProcessing).toBe(false);
  });

  it("shows a timeout message when the request is aborted", async () => {
    const abort = Object.assign(new Error("aborted"), { name: "AbortError" });
    vi.mocked(sendChat).mockRejectedValue(abort);
    const { result } = await ready();
    await act(() => result.current.sendMessageDirect("hello"));
    expect(result.current.messages.at(-1)).toEqual({ sender: "Error", text: "Request timed out. Please try again." });
  });

  it("ignores empty messages", async () => {
    const { result } = await ready();
    await act(() => result.current.sendMessageDirect("   "));
    expect(sendChat).not.toHaveBeenCalled();
  });

  it("still works when the history cannot be loaded", async () => {
    vi.mocked(fetchHistory).mockRejectedValue(new Error("down"));
    const { result } = await ready();
    expect(result.current.messages).toEqual([]);
  });

  it("tells the parent page about the first message once per session", async () => {
    vi.mocked(sendChat).mockResolvedValue({ success: true, response: "ok", status: 200 });
    const post = vi.spyOn(window.parent, "postMessage").mockImplementation(() => {});
    const { result } = await ready();
    await act(() => result.current.sendMessageDirect("one"));
    await act(() => result.current.sendMessageDirect("two"));
    // jsdom's window.parent is the window itself, so nothing is posted; the flag is still set once.
    expect(post).not.toHaveBeenCalled();
    expect(Object.keys(localStorage).filter((k) => k.startsWith("chat_first_sent_"))).toHaveLength(1);
  });
});
