import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";

type Step = "idle" | "validating" | "retrieving" | "generating" | "complete" | "error";

interface SpecResult {
  requirements: string;
  design: string;
  tasks: string;
}

type SpecField = keyof SpecResult;

const EMPTY_SPECS: SpecResult = { requirements: "", design: "", tasks: "" };

const STEPS = [
  { id: "retrieving", label: "Retrieving architecture knowledge" },
  { id: "validating", label: "Validating agent idea" },
  { id: "generating", label: "Generating spec files" },
  { id: "complete", label: "Specs ready" },
];

function getStepStatus(stepId: string, currentStep: Step) {
  const order = ["retrieving", "validating", "generating", "complete"];
  const currentIndex = order.indexOf(currentStep);
  const stepIndex = order.indexOf(stepId);

  if (currentStep === "error") {
    if (stepIndex <= currentIndex) return "error";
    return "pending";
  }
  if (stepIndex < currentIndex) return "completed";
  if (stepIndex === currentIndex) return "active";
  return "pending";
}

function StepIcon({ status }: { status: string }) {
  if (status === "completed") return <span>&#10003;</span>;
  if (status === "active") return <span>&#9679;</span>;
  if (status === "error") return <span>&#10007;</span>;
  return <span>&#9675;</span>;
}

export default function App() {
  const [query, setQuery] = useState("");
  const [step, setStep] = useState<Step>("idle");
  const [specs, setSpecs] = useState<SpecResult | null>(null);
  const [activeTab, setActiveTab] = useState<SpecField>("requirements");
  const [error, setError] = useState<string | null>(null);
  const [streamingSpecs, setStreamingSpecs] = useState<SpecResult>({ ...EMPTY_SPECS });
  const [streamingField, setStreamingField] = useState<SpecField | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [thinking, setThinking] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [thinkingCollapsed, setThinkingCollapsed] = useState(false);

  const userSelectedTabRef = useRef(false);
  const thinkingEndRef = useRef<HTMLDivElement>(null);

  // RAF-based rendering: accumulate in refs, flush to state at 60fps
  const specsBufferRef = useRef<SpecResult>({ ...EMPTY_SPECS });
  const thinkingBufferRef = useRef("");
  const latestFieldRef = useRef<SpecField | null>(null);
  const rafIdRef = useRef(0);
  const specsDirtyRef = useRef(false);
  const thinkingDirtyRef = useRef(false);

  const flushToState = useCallback(() => {
    rafIdRef.current = 0;
    if (specsDirtyRef.current) {
      specsDirtyRef.current = false;
      setStreamingSpecs({ ...specsBufferRef.current });
      setStreamingField(latestFieldRef.current);
      if (latestFieldRef.current && !userSelectedTabRef.current) {
        setActiveTab(latestFieldRef.current);
      }
    }
    if (thinkingDirtyRef.current) {
      thinkingDirtyRef.current = false;
      setThinking(thinkingBufferRef.current);
    }
  }, []);

  function scheduleFlush() {
    if (!rafIdRef.current) {
      rafIdRef.current = requestAnimationFrame(flushToState);
    }
  }

  useEffect(() => {
    if (isThinking && thinkingEndRef.current) {
      thinkingEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [thinking, isThinking]);

  // Cleanup RAF on unmount
  useEffect(() => {
    return () => {
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
    };
  }, []);

  const charCount = query.length;
  const charClass = charCount > 800 ? "error" : charCount > 700 ? "warning" : "";

  function handleStreamEvent(event: { type: string; step?: string; field?: string; content?: string; message?: string }) {
    switch (event.type) {
      case "progress":
        if (event.step) {
          setStep(event.step as Step);
        }
        break;
      case "thinking":
        setIsThinking(true);
        thinkingBufferRef.current += event.content ?? "";
        thinkingDirtyRef.current = true;
        scheduleFlush();
        break;
      case "delta": {
        // First delta means thinking is done, spec writing started
        setIsThinking(false);
        setThinkingCollapsed(true);
        const field = event.field as SpecField;
        const content = event.content ?? "";
        latestFieldRef.current = field;
        specsBufferRef.current = {
          ...specsBufferRef.current,
          [field]: specsBufferRef.current[field] + content,
        };
        specsDirtyRef.current = true;
        scheduleFlush();
        break;
      }
      case "done":
        // Final flush — ensure all buffered content is rendered
        if (rafIdRef.current) {
          cancelAnimationFrame(rafIdRef.current);
          rafIdRef.current = 0;
        }
        setStreamingSpecs({ ...specsBufferRef.current });
        setSpecs({ ...specsBufferRef.current });
        setThinking(thinkingBufferRef.current);
        setStep("complete");
        setIsStreaming(false);
        setIsThinking(false);
        setStreamingField(null);
        break;
      case "error":
        if (rafIdRef.current) {
          cancelAnimationFrame(rafIdRef.current);
          rafIdRef.current = 0;
        }
        setStep("error");
        setError(event.message ?? "An unknown error occurred.");
        setIsStreaming(false);
        setIsThinking(false);
        setStreamingField(null);
        break;
    }
  }

  async function handleSubmit() {
    if (!query.trim() || query.length < 10 || query.length > 800) return;

    setError(null);
    setSpecs(null);
    setStreamingSpecs({ ...EMPTY_SPECS });
    setStreamingField(null);
    setThinking("");
    setIsThinking(false);
    setThinkingCollapsed(false);
    setStep("retrieving");
    setIsStreaming(true);
    userSelectedTabRef.current = false;
    setActiveTab("requirements");

    // Reset buffers
    specsBufferRef.current = { ...EMPTY_SPECS };
    thinkingBufferRef.current = "";
    latestFieldRef.current = null;
    specsDirtyRef.current = false;
    thinkingDirtyRef.current = false;

    try {
      const response = await fetch("http://localhost:8000/generate-stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });

      if (!response.ok || !response.body) {
        setStep("error");
        setError("Failed to connect to the server. Make sure the backend is running on localhost:8000.");
        setIsStreaming(false);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data: ")) continue;
          const jsonStr = trimmed.slice(6);
          try {
            const event = JSON.parse(jsonStr);
            handleStreamEvent(event);
          } catch {
            // Skip malformed JSON lines
          }
        }
      }

      // Process any remaining data in buffer
      if (buffer.trim().startsWith("data: ")) {
        try {
          const event = JSON.parse(buffer.trim().slice(6));
          handleStreamEvent(event);
        } catch {
          // Skip malformed
        }
      }
    } catch {
      setStep("error");
      setError("Failed to connect to the server. Make sure the backend is running on localhost:8000.");
      setIsStreaming(false);
    }
  }

  function handleTabChange(tab: SpecField) {
    setActiveTab(tab);
    if (isStreaming) {
      userSelectedTabRef.current = true;
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && e.metaKey) {
      handleSubmit();
    }
  }

  const isLoading = ["validating", "retrieving", "generating"].includes(step);
  const showOutput = isStreaming || (specs && step === "complete");

  const displayText = step === "complete" && specs
    ? specs[activeTab]
    : streamingSpecs[activeTab];

  const showCursor = isStreaming && streamingField === activeTab;

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="app-logo">A</div>
        <div className="app-header-text">
          <h1>Agent Architect</h1>
          <p>AI-powered spec generator for agent projects</p>
        </div>
      </header>

      <main className="main-content">
        {step === "idle" && !specs && (
          <div className="hero-section">
            <h2>Design Your AI Agent</h2>
            <p>
              Describe your agent idea and get production-ready spec files —
              requirements, design, and implementation tasks — compatible with
              Kiro IDE and Claude Code.
            </p>
          </div>
        )}

        <div className="input-card">
          <label className="input-label">Describe your agent idea</label>
          <textarea
            className="input-textarea"
            placeholder="e.g. I want to build an AI agent that reviews pull requests, checks for bugs, and suggests improvements..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <div className="input-footer">
            <span className={`char-count ${charClass}`}>
              {charCount}/800 characters
              {charCount > 0 && charCount < 10 && " (minimum 10)"}
            </span>
            <button
              className="submit-btn"
              onClick={handleSubmit}
              disabled={isLoading || charCount < 10 || charCount > 800}
            >
              {isLoading ? "Processing..." : <>Generate Specs &#8594;</>}
            </button>
          </div>
        </div>

        {error && (
          <div className="error-card">
            <span className="error-icon">&#9888;</span>
            <span className="error-text">{error}</span>
          </div>
        )}

        {isLoading && (
          <div className="progress-container">
            <div className="progress-title">Processing Pipeline</div>
            <div className="progress-steps">
              {STEPS.map((s) => {
                const status = getStepStatus(s.id, step);
                return (
                  <div key={s.id} className={`progress-step ${status}`}>
                    <div className={`step-icon ${status}`}>
                      <StepIcon status={status} />
                    </div>
                    <span className={`step-text ${status}`}>{s.label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {thinking && (
          <div className={`thinking-container ${thinkingCollapsed ? "collapsed" : ""}`}>
            <button
              className="thinking-header"
              onClick={() => setThinkingCollapsed((c) => !c)}
            >
              <span className="thinking-label">
                {isThinking && <span className="thinking-indicator" />}
                {isThinking ? "Thinking..." : "Thought process"}
              </span>
              <span className="thinking-toggle">
                {thinkingCollapsed ? "\u25B6" : "\u25BC"}
              </span>
            </button>
            {!thinkingCollapsed && (
              <div className="thinking-body">
                <div className="thinking-text">{thinking}</div>
                <div ref={thinkingEndRef} />
              </div>
            )}
          </div>
        )}

        {showOutput && (
          <div className="spec-output">
            <div className="tab-bar">
              {(["requirements", "design", "tasks"] as SpecField[]).map((tab) => {
                const isActive = activeTab === tab;
                const isTabStreaming = isStreaming && streamingField === tab;
                const labels: Record<SpecField, { icon: string; label: string }> = {
                  requirements: { icon: "\u{1F4CB}", label: "Requirements" },
                  design: { icon: "\u{1F6E0}", label: "Design" },
                  tasks: { icon: "\u2611", label: "Tasks" },
                };
                return (
                  <button
                    key={tab}
                    className={`tab-btn ${isActive ? "active" : ""} ${isTabStreaming ? "streaming" : ""}`}
                    onClick={() => handleTabChange(tab)}
                  >
                    <span className="tab-icon">{labels[tab].icon}</span>
                    {labels[tab].label}
                    {isTabStreaming && <span className="streaming-dot" />}
                  </button>
                );
              })}
            </div>
            <div className="spec-content">
              <div className={showCursor ? "streaming-cursor" : ""}>
                <ReactMarkdown>{displayText}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
