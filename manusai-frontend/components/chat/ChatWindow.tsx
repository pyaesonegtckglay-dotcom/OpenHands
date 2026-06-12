"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send,
  Zap,
  Bot,
  User,
  StopCircle,
  ArrowDown,
  Copy,
  Check,
  Terminal,
} from "lucide-react";
import { useChatStore } from "@/store/chatStore";
import { Message } from "@/types";
import { streamChat } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const oneDarkStyle = require("react-syntax-highlighter/dist/cjs/styles/prism/one-dark") as Record<string, React.CSSProperties>;
import type { Components } from "react-markdown";

// ─── Typing cursor ─────────────────────────────────────────────────────────────
function Cursor() {
  return (
    <span className="inline-block w-0.5 h-[1em] bg-blue-400 animate-pulse ml-0.5 rounded-sm align-text-bottom" />
  );
}

// ─── Copy button for code blocks ───────────────────────────────────────────────
function CopyButton({ code }: { code: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1 px-2 py-1 text-[10px] text-gray-400 hover:text-white bg-gray-700/50 hover:bg-gray-600/60 rounded transition-all"
      title="Copy code"
    >
      {copied ? (
        <>
          <Check className="w-3 h-3 text-green-400" />
          <span className="text-green-400">Copied!</span>
        </>
      ) : (
        <>
          <Copy className="w-3 h-3" />
          <span>Copy</span>
        </>
      )}
    </button>
  );
}

// ─── Markdown components with syntax highlighting ──────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function buildMarkdownComponents(_isStreaming: boolean): Components {
  return {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    code({ node: _node, className, children }) {
      const match = /language-(\w+)/.exec(className || "");
      const language = match ? match[1] : "";
      const codeString = String(children).replace(/\n$/, "");
      const isBlock = !!match || codeString.includes("\n");

      if (isBlock) {
        return (
          <div className="relative group my-3 rounded-xl overflow-hidden border border-[#2d3038] bg-[#0d0f13]">
            {/* Code header */}
            <div className="flex items-center justify-between px-4 py-2 bg-[#1a1d24] border-b border-[#2d3038]">
              <div className="flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5 text-gray-500" />
                <span className="text-[11px] text-gray-400 font-mono">
                  {language || "code"}
                </span>
              </div>
              <CopyButton code={codeString} />
            </div>

            {/* Syntax highlighted content */}
            <SyntaxHighlighter
              style={oneDarkStyle}
              language={language || "text"}
              PreTag="div"
              showLineNumbers={codeString.split("\n").length > 4}
              wrapLines
              customStyle={{
                margin: 0,
                padding: "1rem",
                background: "transparent",
                fontSize: "0.8rem",
                lineHeight: "1.6",
              }}
              lineNumberStyle={{
                color: "#4b5563",
                fontSize: "0.7rem",
                minWidth: "2rem",
              }}
            >
              {codeString}
            </SyntaxHighlighter>
          </div>
        );
      }

      // Inline code
      return (
        <code
          className="px-1.5 py-0.5 bg-[#1a1d24] text-blue-300 rounded font-mono text-[0.8em] border border-[#2d3038]"
        >
          {children}
        </code>
      );
    },

    // Styled paragraph
    p({ children }) {
      return <p className="my-1.5 leading-relaxed">{children}</p>;
    },

    // Styled headings
    h1({ children }) {
      return (
        <h1 className="text-xl font-bold text-white mt-4 mb-2 pb-1 border-b border-[#2d3038]">
          {children}
        </h1>
      );
    },
    h2({ children }) {
      return (
        <h2 className="text-lg font-bold text-white mt-3 mb-1.5">{children}</h2>
      );
    },
    h3({ children }) {
      return (
        <h3 className="text-base font-semibold text-gray-100 mt-2.5 mb-1">
          {children}
        </h3>
      );
    },

    // Styled lists
    ul({ children }) {
      return (
        <ul className="my-2 ml-4 space-y-1 list-disc list-outside text-gray-200">
          {children}
        </ul>
      );
    },
    ol({ children }) {
      return (
        <ol className="my-2 ml-4 space-y-1 list-decimal list-outside text-gray-200">
          {children}
        </ol>
      );
    },
    li({ children }) {
      return <li className="pl-1">{children}</li>;
    },

    // Styled blockquote
    blockquote({ children }) {
      return (
        <blockquote className="my-2 pl-4 border-l-2 border-blue-500/60 text-gray-400 italic">
          {children}
        </blockquote>
      );
    },

    // Styled table
    table({ children }) {
      return (
        <div className="my-3 overflow-x-auto rounded-lg border border-[#2d3038]">
          <table className="w-full text-sm">{children}</table>
        </div>
      );
    },
    thead({ children }) {
      return <thead className="bg-[#1a1d24]">{children}</thead>;
    },
    th({ children }) {
      return (
        <th className="px-4 py-2 text-left text-gray-300 font-semibold border-b border-[#2d3038]">
          {children}
        </th>
      );
    },
    td({ children }) {
      return (
        <td className="px-4 py-2 text-gray-300 border-b border-[#1e2128]">
          {children}
        </td>
      );
    },

    // Styled horizontal rule
    hr() {
      return <hr className="my-4 border-[#2d3038]" />;
    },

    // Styled links
    a({ href, children }) {
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-400 hover:text-blue-300 underline underline-offset-2 transition-colors"
        >
          {children}
        </a>
      );
    },

    // Strong / em
    strong({ children }) {
      return <strong className="font-semibold text-white">{children}</strong>;
    },
    em({ children }) {
      return <em className="text-gray-300 italic">{children}</em>;
    },
  };
}

// ─── Message bubble ────────────────────────────────────────────────────────────
interface MessageBubbleProps {
  msg: Message;
  isStreaming?: boolean;
}

function MessageBubble({ msg, isStreaming }: MessageBubbleProps) {
  const isUser = msg.role === "user";
  const components = buildMarkdownComponents(!!isStreaming);

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""} group`}>
      {/* Avatar */}
      <div className="flex-shrink-0 mt-0.5">
        <div
          className={`w-7 h-7 rounded-full flex items-center justify-center shadow-sm ${
            isUser
              ? "bg-blue-600"
              : "bg-gradient-to-br from-violet-600 to-blue-600"
          }`}
        >
          {isUser ? (
            <User className="w-3.5 h-3.5 text-white" />
          ) : (
            <Bot className="w-3.5 h-3.5 text-white" />
          )}
        </div>
      </div>

      {/* Content */}
      <div
        className={`flex flex-col gap-1 max-w-[85%] sm:max-w-[78%] ${
          isUser ? "items-end" : "items-start"
        }`}
      >
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-blue-600 text-white rounded-tr-sm"
              : "bg-[#1a1d24] text-gray-200 rounded-tl-sm border border-[#252830]"
          }`}
        >
          {isUser ? (
            <span className="whitespace-pre-wrap break-words">{msg.content}</span>
          ) : (
            <div className="min-w-0">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={components}
              >
                {msg.content || ""}
              </ReactMarkdown>
              {isStreaming && msg.content && <Cursor />}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Thinking indicator ────────────────────────────────────────────────────────
function ThinkingIndicator() {
  return (
    <div className="flex gap-3">
      <div className="flex-shrink-0 mt-0.5">
        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-violet-600 to-blue-600 flex items-center justify-center">
          <Bot className="w-3.5 h-3.5 text-white" />
        </div>
      </div>
      <div className="bg-[#1a1d24] border border-[#252830] rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-1.5">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="w-1.5 h-1.5 bg-blue-500/60 rounded-full animate-bounce"
            style={{ animationDelay: `${i * 0.18}s` }}
          />
        ))}
        <span className="text-gray-500 text-xs ml-1">ManusAI is thinking…</span>
      </div>
    </div>
  );
}

// ─── Welcome screen ────────────────────────────────────────────────────────────
function WelcomeScreen({ onSuggestion }: { onSuggestion: (s: string) => void }) {
  const suggestions = [
    { label: "Hello! What can you do?", category: "Chat" },
    { label: "What is Python?", category: "Question" },
    { label: "Write a quicksort in Python", category: "Code" },
    { label: "Build a portfolio website", category: "Project" },
    { label: "Create a SaaS business plan", category: "Project" },
    { label: "Analyze market trends for AI", category: "Analysis" },
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-4 py-8">
      <div className="w-16 h-16 bg-gradient-to-br from-blue-500/20 to-violet-600/20 rounded-2xl flex items-center justify-center mb-5 border border-[#252830]">
        <Zap className="w-8 h-8 text-blue-400" />
      </div>
      <h2 className="text-white font-bold text-2xl mb-2 tracking-tight">
        ManusAI
      </h2>
      <p className="text-gray-400 text-sm max-w-md leading-relaxed mb-1">
        Your AI assistant for research, planning, coding, and analysis.
      </p>
      <p className="text-gray-600 text-xs max-w-sm mb-8">
        Powered by Gemini · GitHub Models · SambaNova
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
        {suggestions.map((s) => (
          <button
            key={s.label}
            onClick={() => onSuggestion(s.label)}
            className="flex items-start gap-3 px-4 py-3 bg-[#1a1d24] hover:bg-[#1e2128] text-left rounded-xl border border-[#252830] hover:border-[#3a3d48] transition-all group"
          >
            <div className="flex-1 min-w-0">
              <p className="text-gray-300 text-xs font-medium group-hover:text-white transition-colors line-clamp-2">
                {s.label}
              </p>
              <p className="text-gray-600 text-[10px] mt-0.5">{s.category}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

// ─── Stop Generation Button ────────────────────────────────────────────────────
function StopButton({ onStop }: { onStop: () => void }) {
  return (
    <button
      onClick={onStop}
      className="flex items-center gap-2 mx-auto px-4 py-2 bg-[#1a1d24] border border-red-600/40 hover:bg-red-900/20 hover:border-red-500/60 text-red-400 hover:text-red-300 rounded-xl text-xs font-medium transition-all group"
      title="Stop generation"
    >
      <StopCircle className="w-3.5 h-3.5 group-hover:animate-pulse" />
      Stop generating
    </button>
  );
}

// ─── Main ChatWindow ───────────────────────────────────────────────────────────
export default function ChatWindow() {
  const { messages, isSending, currentConversationId, error } = useChatStore();

  const [input, setInput] = useState("");
  const [streamingContent, setStreamingContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);
  const messagesRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const streamBufferRef = useRef<string>("");
  const userScrolledRef = useRef(false);

  // Smart auto-scroll — only scroll if user hasn't scrolled up
  const scrollToBottomSmooth = useCallback(() => {
    if (!userScrolledRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, []);

  useEffect(() => {
    scrollToBottomSmooth();
  }, [messages, scrollToBottomSmooth]);

  // Scroll during streaming (throttled via rAF)
  useEffect(() => {
    if (isStreaming && streamingContent) {
      scrollToBottomSmooth();
    }
  }, [streamingContent, isStreaming, scrollToBottomSmooth]);

  const handleScroll = () => {
    if (!messagesRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = messagesRef.current;
    const distFromBottom = scrollHeight - scrollTop - clientHeight;
    setShowScrollBtn(distFromBottom > 200);
    userScrolledRef.current = distFromBottom > 100;
  };

  const scrollToBottom = () => {
    userScrolledRef.current = false;
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSend = async (overrideContent?: string) => {
    const content = (overrideContent || input).trim();
    if (!content || isSending || isStreaming) return;

    setInput("");
    setStreamError(null);
    setStreamingContent("");
    userScrolledRef.current = false;

    const ac = new AbortController();
    abortControllerRef.current = ac;
    setIsStreaming(true);
    streamBufferRef.current = "";

    // Optimistic user message
    const tempUserMsg: Message = {
      id: `temp_${Date.now()}`,
      conversation_id: currentConversationId || "",
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };
    useChatStore.setState((s) => ({ messages: [...s.messages, tempUserMsg] }));

    try {
      await streamChat(
        content,
        currentConversationId,
        (token: string) => {
          streamBufferRef.current += token;
          setStreamingContent(streamBufferRef.current);
        },
        (convId: string, msgId: string) => {
          const assistantMsg: Message = {
            id: msgId || `asst_${Date.now()}`,
            conversation_id: convId || currentConversationId || "",
            role: "assistant",
            content: streamBufferRef.current,
            created_at: new Date().toISOString(),
          };
          useChatStore.setState((s) => {
            const filtered = s.messages.filter((m) => m.id !== tempUserMsg.id);
            const realUserMsg: Message = {
              ...tempUserMsg,
              id: `user_${Date.now()}`,
              conversation_id: convId || currentConversationId || "",
            };
            return {
              messages: [...filtered, realUserMsg, assistantMsg],
              currentConversationId: convId || s.currentConversationId,
            };
          });
          setStreamingContent("");
          setIsStreaming(false);
          abortControllerRef.current = null;
          streamBufferRef.current = "";
          useChatStore.getState().loadConversations();
        },
        (err: string) => {
          setStreamError(err);
          setIsStreaming(false);
          setStreamingContent("");
          streamBufferRef.current = "";
        },
        ac.signal,
      );
    } catch (e: unknown) {
      const err = e as { name?: string };
      if (err?.name !== "AbortError") {
        setStreamError("Connection error. Please try again.");
      }
      setIsStreaming(false);
      setStreamingContent("");
      streamBufferRef.current = "";
    }

    inputRef.current?.focus();
  };

  const handleStop = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setIsStreaming(false);

    // Persist the partial response as a stopped message
    if (streamBufferRef.current.trim()) {
      const partialContent = streamBufferRef.current;
      const assistantMsg: Message = {
        id: `asst_stopped_${Date.now()}`,
        conversation_id: currentConversationId || "",
        role: "assistant",
        content: partialContent,
        created_at: new Date().toISOString(),
      };
      useChatStore.setState((s) => ({
        messages: [...s.messages, assistantMsg],
      }));
    }
    setStreamingContent("");
    streamBufferRef.current = "";
  }, [currentConversationId]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isEmpty = messages.length === 0 && !isStreaming;

  return (
    <div className="flex flex-col h-full bg-[#0d0f13]">
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-4 sm:px-6 py-3 border-b border-[#1e2128] flex-shrink-0 bg-[#111318]">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 bg-gradient-to-br from-blue-500/20 to-violet-600/20 rounded-lg flex items-center justify-center border border-[#252830]">
            <Zap className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <div>
            <h1 className="text-white font-semibold text-sm leading-none">
              {currentConversationId ? "Conversation" : "New Chat"}
            </h1>
            <p className="text-gray-600 text-[10px] mt-0.5">
              ManusAI · Cognitive AI
            </p>
          </div>
        </div>

        {/* Live streaming badge */}
        {isStreaming && (
          <div className="flex items-center gap-1.5 text-xs text-blue-400">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
            </span>
            <span>Generating…</span>
          </div>
        )}
      </div>

      {/* ── Messages ── */}
      <div
        ref={messagesRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto relative scroll-smooth"
      >
        {isEmpty ? (
          <WelcomeScreen onSuggestion={(s) => handleSend(s)} />
        ) : (
          <div className="px-4 sm:px-6 py-6 space-y-5 max-w-4xl mx-auto w-full">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}

            {/* Live streaming message */}
            {isStreaming && streamingContent && (
              <MessageBubble
                msg={{
                  id: "streaming",
                  conversation_id: currentConversationId || "",
                  role: "assistant",
                  content: streamingContent,
                  created_at: new Date().toISOString(),
                }}
                isStreaming
              />
            )}

            {/* Thinking dots (before first token arrives) */}
            {isStreaming && !streamingContent && <ThinkingIndicator />}

            {/* Stop button below streaming content */}
            {isStreaming && (
              <div className="pt-1">
                <StopButton onStop={handleStop} />
              </div>
            )}

            {/* Error message */}
            {(error || streamError) && (
              <div className="bg-red-900/20 border border-red-700/40 rounded-xl px-4 py-3 text-red-300 text-sm flex items-center gap-2">
                <span className="text-red-400 text-base">⚠</span>
                {error || streamError}
              </div>
            )}

            <div ref={bottomRef} />
          </div>
        )}

        {/* Scroll to bottom FAB */}
        {showScrollBtn && !isEmpty && (
          <button
            onClick={scrollToBottom}
            className="absolute bottom-4 right-4 w-8 h-8 bg-[#1a1d24] border border-[#252830] hover:bg-[#252830] rounded-full flex items-center justify-center text-gray-400 hover:text-white transition-all shadow-lg"
          >
            <ArrowDown className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* ── Input area ── */}
      <div className="flex-shrink-0 px-4 sm:px-6 py-4 border-t border-[#1e2128] bg-[#111318]">
        <div className="max-w-4xl mx-auto">
          <div
            className={`flex gap-2 items-end bg-[#1a1d24] border rounded-2xl px-3 py-2 transition-colors ${
              isStreaming
                ? "border-blue-600/30"
                : "border-[#252830] focus-within:border-blue-600/50"
            }`}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                isStreaming
                  ? "ManusAI is responding…"
                  : "Ask ManusAI anything…"
              }
              rows={1}
              disabled={isStreaming}
              className="flex-1 bg-transparent text-white text-sm resize-none focus:outline-none placeholder-gray-600 disabled:opacity-40 py-1.5 max-h-40 overflow-y-auto"
              style={{ minHeight: "24px" }}
              onInput={(e) => {
                const el = e.target as HTMLTextAreaElement;
                el.style.height = "auto";
                el.style.height = Math.min(el.scrollHeight, 160) + "px";
              }}
            />

            {isStreaming ? (
              <button
                onClick={handleStop}
                className="w-8 h-8 bg-red-600/20 hover:bg-red-600/40 text-red-400 rounded-xl flex items-center justify-center flex-shrink-0 transition-colors border border-red-600/30"
                title="Stop generating"
              >
                <StopCircle className="w-4 h-4" />
              </button>
            ) : (
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || isSending}
                className="w-8 h-8 bg-blue-600 hover:bg-blue-700 disabled:opacity-30 disabled:cursor-not-allowed text-white rounded-xl flex items-center justify-center flex-shrink-0 transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <p className="text-[10px] text-gray-700 text-center mt-2">
            Enter to send · Shift+Enter for new line · Gemini → GitHub Models →
            SambaNova
          </p>
        </div>
      </div>
    </div>
  );
}
