import { useState, useRef, useEffect } from 'react';
import { X, Send, Sparkles, RotateCcw, Bot, User, Database } from 'lucide-react';
import { sendCopilotMessage } from '../api/client';
import ReactMarkdown from 'react-markdown';

const WELCOME = `**Welcome to ReconQ Copilot** — your AI finance analyst.

I can query your actual reconciliation data using Gemini function-calling. Try asking:`;

const SUGGESTIONS = [
  { label: '📊 Match rate summary', text: "What's my overall match rate and how many transactions were auto-cleared?" },
  { label: '🔍 Unresolved items', text: 'Show me all unresolved transactions with their amounts' },
  { label: '💰 Fee analysis', text: 'Analyze my fee patterns — are there any overcharges?' },
  { label: '⚠️ Leakage report', text: 'How much revenue leakage was detected and what types?' },
  { label: '🏦 Bank reconciliation', text: 'How many settlements were confirmed by the bank vs. still in transit?' },
  { label: '📋 High-value review', text: 'Show me human-review items above ₹1 lakh' },
];

/* ── Markdown-rendered message bubble ─────────────────────────────── */
function MsgBubble({ role, text }) {
  const isUser = role === 'user';
  return (
    <div style={{
      display: 'flex', gap: 10, alignItems: 'flex-start',
      flexDirection: isUser ? 'row-reverse' : 'row',
    }}>
      <div style={{
        width: 28, height: 28, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        background: isUser ? 'var(--accent-blue)' : 'rgba(139,92,246,0.2)',
      }}>
        {isUser ? <User size={14} color="#fff" /> : <Bot size={14} color="#8b5cf6" />}
      </div>
      <div style={{
        maxWidth: '85%', padding: '10px 14px', borderRadius: 12,
        background: isUser ? 'var(--accent-blue)' : 'var(--bg-card)',
        border: isUser ? 'none' : '1px solid var(--border)',
        color: isUser ? '#fff' : 'var(--text-primary)',
        fontSize: 13, lineHeight: 1.65,
      }}>
        {isUser ? (
          <span>{text}</span>
        ) : (
          <div className="copilot-markdown">
            <ReactMarkdown>{text}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Copilot({ runId, onClose }) {
  const [messages, setMessages] = useState([{ role: 'assistant', text: WELCOME }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const send = async (msg) => {
    if (!msg.trim()) return;
    const userMsg = { role: 'user', text: msg.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);
    setShowSuggestions(false);
    try {
      const res = await sendCopilotMessage(msg, runId || 'default');
      setMessages(prev => [...prev, { role: 'assistant', text: res.reply }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', text: `**Error:** ${err.message}. Is the backend running?` }]);
    } finally {
      setLoading(false);
    }
  };

  const reset = async () => {
    setMessages([{ role: 'assistant', text: WELCOME }]);
    setShowSuggestions(true);
    // Actually reset the backend chat session
    try {
      const axios = (await import('axios')).default;
      await axios.post(`/api/copilot/reset/${runId || 'default'}`);
    } catch { /* silent — reset is best-effort */ }
  };

  return (
    <div style={{
      width: 400, height: '100vh', flexShrink: 0,
      borderLeft: '1px solid var(--border)',
      background: 'var(--bg-secondary)',
      display: 'flex', flexDirection: 'column',
    }}>
      {/* ── Header ────────────────────────────────────────────────── */}
      <div style={{
        padding: '14px 18px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: 10,
          background: 'rgba(139,92,246,0.2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Sparkles size={16} color="#8b5cf6" />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>ReconQ Copilot</div>
          <div style={{ fontSize: 10, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 4 }}>
            <Database size={9} />
            {runId ? `Run: ${runId.slice(0, 8)}…` : 'No active run'} · Gemini function-calling
          </div>
        </div>
        <button onClick={reset} title="Reset chat" style={{
          background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: 'var(--text-secondary)',
        }}>
          <RotateCcw size={15} />
        </button>
        <button onClick={onClose} style={{
          background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: 'var(--text-secondary)',
        }}>
          <X size={16} />
        </button>
      </div>

      {/* ── Messages ──────────────────────────────────────────────── */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '16px 14px',
        display: 'flex', flexDirection: 'column', gap: 14,
      }}>
        {messages.map((m, i) => <MsgBubble key={i} role={m.role} text={m.text} />)}

        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px' }}>
            <div style={{
              width: 28, height: 28, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: 'rgba(139,92,246,0.2)',
            }}>
              <Bot size={14} color="#8b5cf6" />
            </div>
            <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Querying your data</span>
              {[0, 1, 2].map(i => (
                <div key={i} style={{
                  width: 5, height: 5, borderRadius: '50%', background: '#8b5cf6',
                  animation: 'bounce 0.6s infinite alternate',
                  animationDelay: `${i * 0.15}s`,
                }} />
              ))}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Suggestion chips ──────────────────────────────────────── */}
      {showSuggestions && (
        <div style={{
          padding: '0 14px 10px', display: 'flex', flexWrap: 'wrap', gap: 6,
        }}>
          {SUGGESTIONS.map((s, i) => (
            <button
              key={i}
              onClick={() => send(s.text)}
              style={{
                fontSize: 11, padding: '5px 10px', borderRadius: 8,
                background: 'rgba(139,92,246,0.08)', color: '#8b5cf6',
                border: '1px solid rgba(139,92,246,0.2)',
                cursor: 'pointer', fontWeight: 500, whiteSpace: 'nowrap',
                transition: 'all .15s',
              }}
              onMouseEnter={e => e.target.style.background = 'rgba(139,92,246,0.18)'}
              onMouseLeave={e => e.target.style.background = 'rgba(139,92,246,0.08)'}
            >
              {s.label}
            </button>
          ))}
        </div>
      )}

      {/* ── Input bar ─────────────────────────────────────────────── */}
      <div style={{
        padding: '10px 14px', borderTop: '1px solid var(--border)',
        display: 'flex', gap: 8, alignItems: 'flex-end',
      }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input); }
          }}
          placeholder="Ask about your reconciliation data…"
          rows={1}
          style={{
            flex: 1, padding: '9px 12px', borderRadius: 10,
            background: 'var(--bg-card)', border: '1px solid var(--border)',
            color: 'var(--text-primary)', fontSize: 13, resize: 'none',
            maxHeight: 100, outline: 'none', lineHeight: 1.5,
          }}
        />
        <button
          onClick={() => send(input)}
          disabled={!input.trim() || loading}
          style={{
            width: 36, height: 36, borderRadius: 10, border: 'none',
            background: input.trim() && !loading ? 'var(--accent-blue)' : 'var(--bg-card)',
            color: input.trim() && !loading ? '#fff' : 'var(--text-secondary)',
            cursor: input.trim() && !loading ? 'pointer' : 'not-allowed',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all .15s',
          }}
        >
          <Send size={15} />
        </button>
      </div>
    </div>
  );
}
