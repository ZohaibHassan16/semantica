import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export interface HybridSemanticSearchResult {
  id: string;
  label: string;
  type: string;
  score?: number;
}

interface HybridSemanticSearchProps {
  onSelectNode: (nodeId: string) => void;
  disabled?: boolean;
}

interface SearchApiResponse {
  results?: Array<
    | HybridSemanticSearchResult
    | {
        node?: {
          id?: string;
          type?: string;
          content?: string;
        };
        score?: number;
      }
  >;
}

const SEARCH_DEBOUNCE_MS = 300;
const MAX_RESULTS = 10;

function normalizeResults(payload: SearchApiResponse): HybridSemanticSearchResult[] {
  const rawResults = payload.results ?? [];

  return rawResults
    .map((item): HybridSemanticSearchResult | null => {
      if (!item || typeof item !== "object") return null;

      if ("id" in item && typeof item.id === "string") {
        return {
          id: item.id,
          label: typeof item.label === "string" && item.label.trim() ? item.label : item.id,
          type: typeof item.type === "string" && item.type.trim() ? item.type : "entity",
          score: typeof item.score === "number" ? item.score : undefined,
        };
      }

      const node = "node" in item ? item.node : undefined;
      if (!node || typeof node.id !== "string") return null;

      return {
        id: node.id,
        label: typeof node.content === "string" && node.content.trim() ? node.content : node.id,
        type: typeof node.type === "string" && node.type.trim() ? node.type : "entity",
        score: typeof item.score === "number" ? item.score : undefined,
      };
    })
    .filter((result): result is HybridSemanticSearchResult => result !== null)
    .slice(0, MAX_RESULTS);
}

export function HybridSemanticSearch({ onSelectNode, disabled = false }: HybridSemanticSearchProps) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [results, setResults] = useState<HybridSemanticSearchResult[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorText, setErrorText] = useState<string | null>(null);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [hoverIndex, setHoverIndex] = useState(-1);
  const [isFocused, setIsFocused] = useState(false);

  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const requestIdRef = useRef(0);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedQuery(query.trim());
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      window.clearTimeout(timer);
    };
  }, [query]);

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (!wrapperRef.current) return;
      if (wrapperRef.current.contains(event.target as Node)) return;
      setIsOpen(false);
      setActiveIndex(-1);
    };

    window.addEventListener("mousedown", handleOutsideClick);
    return () => {
      window.removeEventListener("mousedown", handleOutsideClick);
    };
  }, []);

  useEffect(() => {
    if (!debouncedQuery || disabled) {
      setResults([]);
      setErrorText(null);
      setIsLoading(false);
      setActiveIndex(-1);
      return;
    }

    const controller = new AbortController();
    const currentRequestId = ++requestIdRef.current;

    const run = async () => {
      setIsLoading(true);
      setErrorText(null);
      setIsOpen(true);

      try {
        const url = new URL("/api/graph/search", window.location.origin);
        url.searchParams.set("q", debouncedQuery);

        const response = await fetch(url.toString(), {
          method: "GET",
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Search failed with status ${response.status}`);
        }

        const payload = (await response.json()) as SearchApiResponse;
        if (currentRequestId !== requestIdRef.current) return;

        const normalized = normalizeResults(payload);
        setResults(normalized);
        setActiveIndex(normalized.length > 0 ? 0 : -1);
      } catch (error) {
        if (controller.signal.aborted) return;
        if (currentRequestId !== requestIdRef.current) return;

        const message = error instanceof Error ? error.message : "Search request failed";
        setErrorText(message);
        setResults([]);
        setActiveIndex(-1);
      } finally {
        if (currentRequestId === requestIdRef.current) {
          setIsLoading(false);
        }
      }
    };

    void run();

    return () => {
      controller.abort();
    };
  }, [debouncedQuery, disabled]);

  const hasEmptyState = useMemo(() => {
    return !isLoading && !errorText && debouncedQuery.length > 0 && results.length === 0;
  }, [isLoading, errorText, debouncedQuery, results.length]);

  const selectResult = useCallback(
    (result: HybridSemanticSearchResult) => {
      onSelectNode(result.id);
      setQuery(result.label);
      setIsOpen(false);
      setActiveIndex(-1);
      setHoverIndex(-1);
    },
    [onSelectNode]
  );

  const handleKeyDown: React.KeyboardEventHandler<HTMLInputElement> = useCallback((event) => {
    if (!isOpen || results.length === 0) {
      if (event.key === "Enter" && debouncedQuery.length > 0) {
        event.preventDefault();
      }
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((prev) => (prev + 1) % results.length);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((prev) => (prev <= 0 ? results.length - 1 : prev - 1));
      return;
    }

    if (event.key === "Enter") {
      event.preventDefault();
      const item = results[activeIndex];
      if (item) {
        selectResult(item);
      }
      return;
    }

    if (event.key === "Escape") {
      setIsOpen(false);
      setActiveIndex(-1);
    }
  }, [results, activeIndex, debouncedQuery]);

  return (
    <div
      ref={wrapperRef}
      style={{
        position: "relative",
        width: 360,
        maxWidth: "45vw",
        borderRadius: 12,
        border: "1px solid rgba(255,255,255,0.1)",
        background: "linear-gradient(160deg, rgba(14,19,28,0.72), rgba(14,19,28,0.56))",
        boxShadow: "0 14px 30px rgba(0,0,0,0.28)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        padding: 8,
      }}
    >
      <input
        type="text"
        value={query}
        disabled={disabled}
        onChange={(event) => {
          setQuery(event.target.value);
          setIsOpen(true);
        }}
        onFocus={() => setIsOpen(true)}
        onFocusCapture={() => setIsFocused(true)}
        onBlurCapture={() => setIsFocused(false)}
        onKeyDown={handleKeyDown}
        placeholder="Hybrid search nodes..."
        aria-label="Hybrid semantic search"
        style={{
          width: "100%",
          height: 38,
          borderRadius: 10,
          border: isFocused ? "1px solid rgba(103,163,255,0.46)" : "1px solid rgba(255,255,255,0.1)",
          background: "linear-gradient(135deg, rgba(13,17,23,0.8), rgba(22,27,34,0.65))",
          color: "#e6edf3",
          padding: "0 12px",
          outline: "none",
          boxShadow: isFocused
            ? "0 0 0 2px rgba(88,166,255,0.18), inset 0 0 0 1px rgba(255,255,255,0.03)"
            : "inset 0 0 0 1px rgba(255,255,255,0.03)",
          fontSize: 12,
          letterSpacing: 0.2,
          transition: "border-color 180ms ease, box-shadow 180ms ease, background 180ms ease",
        }}
      />

      <div
        style={{
          position: "absolute",
          top: 48,
          left: 0,
          right: 0,
          zIndex: 40,
          maxHeight: isOpen ? 320 : 0,
          overflowY: "auto",
          opacity: isOpen ? 1 : 0,
          transition: "opacity 160ms ease, max-height 180ms ease",
          pointerEvents: isOpen ? "auto" : "none",
          borderRadius: 10,
          border: "1px solid rgba(255,255,255,0.1)",
          background: "linear-gradient(160deg, rgba(13,17,23,0.94), rgba(20,27,39,0.9))",
          boxShadow: "0 16px 34px rgba(0,0,0,0.4)",
          backdropFilter: "blur(14px)",
          WebkitBackdropFilter: "blur(14px)",
        }}
      >
        {isLoading && <div style={itemBaseStyle}>Searching...</div>}

        {errorText && !isLoading && (
          <div style={{ ...itemBaseStyle, color: "#ff7b72" }}>{errorText}</div>
        )}

        {hasEmptyState && <div style={itemBaseStyle}>No matches found.</div>}

        {!isLoading &&
          !errorText &&
          results.map((result, index) => {
            const isActive = index === activeIndex || index === hoverIndex;
            return (
              <button
                key={result.id}
                type="button"
                onMouseDown={(event) => event.preventDefault()}
                onMouseEnter={() => setHoverIndex(index)}
                onMouseLeave={() => setHoverIndex(-1)}
                onClick={() => selectResult(result)}
                style={{
                  ...itemBaseStyle,
                  textAlign: "left",
                  width: "100%",
                  background: isActive ? "rgba(88,166,255,0.14)" : "transparent",
                  border: "none",
                  cursor: "pointer",
                  transition: "background 160ms ease, transform 160ms ease",
                  transform: isActive ? "translateX(2px)" : "translateX(0)",
                }}
              >
                <div style={{ color: "#ffffff", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
                  {result.label}
                </div>
                <div style={{ color: "#8b949e", fontSize: 12, display: "flex", gap: 8 }}>
                  <span>{result.type}</span>
                  {typeof result.score === "number" && (
                    <span style={{ color: "#58a6ff" }}>score {result.score.toFixed(3)}</span>
                  )}
                </div>
              </button>
            );
          })}
      </div>
    </div>
  );
}

const itemBaseStyle: React.CSSProperties = {
  padding: "11px 12px",
  borderBottom: "1px solid rgba(255,255,255,0.07)",
  color: "#e6edf3",
  fontSize: 12,
};
