import { useMemo, useState } from "react";

interface ExtractedEntity {
  id: string;
  label: string;
  type: string;
}

interface ExtractedRelation {
  id: string;
  source: string;
  target: string;
  predicate: string;
}

interface MockExtractionResult {
  entities: ExtractedEntity[];
  relationships: ExtractedRelation[];
}

const DEFAULT_SAMPLE =
  "OpenAI and Anthropic collaborated with Microsoft on responsible AI governance in Washington.";

function tokenizeEntities(input: string): ExtractedEntity[] {
  const matches = input.match(/\b[A-Z][a-zA-Z0-9_-]{2,}\b/g) ?? [];
  const seen = new Set<string>();

  const entities: ExtractedEntity[] = [];
  for (const token of matches) {
    const key = token.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);

    entities.push({
      id: `ent-${entities.length + 1}`,
      label: token,
      type: token.endsWith("AI") ? "Concept" : "Entity",
    });

    if (entities.length >= 12) break;
  }

  return entities;
}

function buildRelations(entities: ExtractedEntity[]): ExtractedRelation[] {
  const relations: ExtractedRelation[] = [];

  for (let i = 0; i < entities.length - 1; i++) {
    relations.push({
      id: `rel-${i + 1}`,
      source: entities[i].id,
      target: entities[i + 1].id,
      predicate: i % 2 === 0 ? "associated_with" : "influences",
    });

    if (relations.length >= 10) break;
  }

  return relations;
}

function mockExtract(text: string): MockExtractionResult {
  const entities = tokenizeEntities(text);
  const relationships = buildRelations(entities);
  return { entities, relationships };
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function highlightEntities(text: string, entities: ExtractedEntity[]): string {
  const safeText = escapeHtml(text);
  if (!text.trim() || entities.length === 0) return safeText;

  const pattern = entities.map((entity) => escapeRegExp(entity.label)).join("|");
  if (!pattern) return safeText;

  const regex = new RegExp(`\\b(${pattern})\\b`, "g");
  return safeText.replace(regex, "<mark>$1</mark>");
}

export function EnrichmentPanel() {
  const [inputText, setInputText] = useState(DEFAULT_SAMPLE);
  const [result, setResult] = useState<MockExtractionResult | null>(null);
  const [hasExtracted, setHasExtracted] = useState(false);
  const [isTextareaFocused, setTextareaFocused] = useState(false);
  const [isExtractHovered, setExtractHovered] = useState(false);

  const entityIdToLabel = useMemo(() => {
    if (!result?.entities) return new Map<string, string>();
    return new Map(result.entities.map((entity) => [entity.id, entity.label]));
  }, [result?.entities]);

  const highlightedPreview = useMemo(() => {
    if (!result) return inputText;
    return highlightEntities(inputText, result.entities);
  }, [inputText, result]);

  const handleExtract = () => {
    const trimmed = inputText.trim();
    if (!trimmed) {
      setResult({ entities: [], relationships: [] });
      setHasExtracted(true);
      return;
    }

    const extraction = mockExtract(trimmed);
    setResult(extraction);
    setHasExtracted(true);
  };

  const entityCount = result?.entities.length ?? 0;
  const relationCount = result?.relationships.length ?? 0;

  return (
    <section
      style={{
        padding: "14px 16px",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        background: "linear-gradient(165deg, rgba(13,17,23,0.44), rgba(13,17,23,0.24))",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
      }}
    >
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 10 }}>
        <h3 style={{ margin: 0, fontSize: 13, color: "#9fc7ff", fontWeight: 700, letterSpacing: 0.45 }}>
          Enrichment Panel
        </h3>
        <span style={{ color: "#9aa5b1", fontSize: 11, letterSpacing: 0.2 }}>Mock mode</span>
      </header>

      <p style={{ margin: "0 0 10px 0", color: "#8b949e", fontSize: 12, lineHeight: 1.5 }}>
        Prepare text for NLP entity and relation extraction. API integration can be plugged into
        the same action later.
      </p>

      <textarea
        value={inputText}
        onChange={(event) => setInputText(event.target.value)}
        onFocus={() => setTextareaFocused(true)}
        onBlur={() => setTextareaFocused(false)}
        placeholder="Paste narrative text for extraction..."
        style={{
          width: "100%",
          minHeight: 110,
          resize: "vertical",
          borderRadius: 12,
          border: isTextareaFocused ? "1px solid rgba(116,176,255,0.44)" : "1px solid rgba(255,255,255,0.1)",
          background: "linear-gradient(145deg, rgba(13,17,23,0.7), rgba(16,20,28,0.52))",
          color: "#e6edf3",
          padding: "11px 12px",
          fontSize: 12,
          lineHeight: 1.45,
          outline: "none",
          boxSizing: "border-box",
          boxShadow: isTextareaFocused
            ? "0 0 0 2px rgba(88,166,255,0.16), inset 0 1px 0 rgba(255,255,255,0.04)"
            : "inset 0 1px 0 rgba(255,255,255,0.04)",
          transition: "border-color 170ms ease, box-shadow 170ms ease",
        }}
      />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 10 }}>
        <button
          type="button"
          onClick={handleExtract}
          onMouseEnter={() => setExtractHovered(true)}
          onMouseLeave={() => setExtractHovered(false)}
          style={{
            border: "1px solid rgba(116,176,255,0.46)",
            background: isExtractHovered
              ? "linear-gradient(135deg, rgba(62,132,235,0.34), rgba(32,86,162,0.24))"
              : "linear-gradient(135deg, rgba(62,132,235,0.26), rgba(32,86,162,0.18))",
            color: "#b9d8ff",
            borderRadius: 10,
            padding: "8px 14px",
            fontSize: 12,
            fontWeight: 600,
            cursor: "pointer",
            letterSpacing: 0.2,
            transition: "background 160ms ease, transform 160ms ease",
            transform: isExtractHovered ? "translateY(-1px)" : "translateY(0)",
          }}
        >
          Extract
        </button>

        <div style={{ display: "flex", gap: 10, fontSize: 11 }}>
          <span style={statStyle}>Entities: {entityCount}</span>
          <span style={statStyle}>Relations: {relationCount}</span>
        </div>
      </div>

      <div style={cardStyle}>
        <div style={cardHeaderStyle}>Entity Highlights</div>
        <div
          style={{ color: "#c9d1d9", fontSize: 12, lineHeight: 1.5 }}
          dangerouslySetInnerHTML={{ __html: highlightedPreview || "<em>No text</em>" }}
        />
      </div>

      <div style={cardStyle}>
        <div style={cardHeaderStyle}>Entities</div>
        {!hasExtracted ? (
          <div style={placeholderStyle}>Run extraction to preview entities.</div>
        ) : entityCount === 0 ? (
          <div style={placeholderStyle}>No entities detected.</div>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {result?.entities.map((entity) => (
              <span
                key={entity.id}
                style={{
                  borderRadius: 999,
                  border: "1px solid rgba(88,166,255,0.3)",
                  background: "rgba(88,166,255,0.12)",
                  color: "#58a6ff",
                  fontSize: 11,
                  fontWeight: 600,
                  padding: "3px 8px",
                }}
              >
                {entity.label} <span style={{ color: "#8b949e" }}>({entity.type})</span>
              </span>
            ))}
          </div>
        )}
      </div>

      <div style={cardStyle}>
        <div style={cardHeaderStyle}>Relationships</div>
        {!hasExtracted ? (
          <div style={placeholderStyle}>Run extraction to preview relationships.</div>
        ) : relationCount === 0 ? (
          <div style={placeholderStyle}>No relationships detected.</div>
        ) : (
          <ul style={{ margin: 0, paddingLeft: 18, color: "#e6edf3", fontSize: 12, display: "grid", gap: 6 }}>
            {result?.relationships.map((rel) => {
              const source = entityIdToLabel.get(rel.source) ?? rel.source;
              const target = entityIdToLabel.get(rel.target) ?? rel.target;

              return (
                <li key={rel.id}>
                  <span style={{ color: "#58a6ff", fontWeight: 600 }}>{source}</span>
                  <span style={{ color: "#8b949e" }}> → {rel.predicate} → </span>
                  <span style={{ color: "#3fb950", fontWeight: 600 }}>{target}</span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}

const statStyle: React.CSSProperties = {
  color: "#9aa5b1",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 999,
  background: "rgba(255,255,255,0.04)",
  padding: "2px 8px",
};

const cardStyle: React.CSSProperties = {
  marginTop: 10,
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 12,
  padding: 10,
  background: "linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))",
  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.05)",
  backdropFilter: "blur(10px)",
  WebkitBackdropFilter: "blur(10px)",
};

const cardHeaderStyle: React.CSSProperties = {
  color: "#9fc7ff",
  fontSize: 11,
  fontWeight: 700,
  marginBottom: 8,
  letterSpacing: 0.35,
};

const placeholderStyle: React.CSSProperties = {
  color: "#8b949e",
  fontSize: 12,
};
