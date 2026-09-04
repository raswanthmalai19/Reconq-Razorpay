import { useState, useRef, useEffect } from 'react';
import { X, Send, RefreshCw, Bot, User, MessageSquare } from 'lucide-react';
import { sendCopilotMessage } from '../api/client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const SUGGESTIONS = [
  "What's my overall match rate?",
  "Show me unresolved transactions",
  "How much revenue leakage was detected?",
  "Analyze my fee patterns",
  "Show human review items above ₹50,000",
  "What's confirmed by the bank?",
];

const WELCOME = `Hello. I'm ReconQ Copilot, powered by Gemini (with Groq fallback).

Ask me anything about your reconciliation data — I query your actual results, not guesses.`;

function MsgBubble({ role, text }) {
  const isUser = role === 'user';
  return (
    <div className="rq-fade-in" style={{ display: 'flex', gap: 9, alignItems: 'flex-start', flexDirection: isUser ? 'row-reverse' : 'row' }}>
      <div style={{
        width: 26, height: 26, borderRadius: 6, flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: isUser ? 'var(--accent-blue)' : '#f4f4f5',
        border: isUser ? 'none' : '1px solid var(--border)',
      }}>
        {isUser
          ? <User size={12} color="#fff" />
          : <Bot size={12} color="var(--text-secondary)" />
        }
      </div>
      <div style={{
        maxWidth: '86%',
        padding: '9px 13px',
        borderRadius: 10,
        background: isUser ? 'var(--accent-blue)' : '#ffffff',
        border: isUser ? 'none' : '1px solid var(--border)',
        color: isUser ? '#fff' : 'var(--text-primary)',
        fontSize: 13,
        lineHeight: 1.6,
        boxShadow: 'var(--shadow-sm)',
      }}>
        {isUser
          ? <span>{text}</span>
          : <div className="copilot-markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown></div>
        }
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
    if (!msg.trim() || loading) return;
    setMessages(prev => [...prev, { role: 'user', text: msg.trim() }]);
    setInput('');
    setLoading(true);
    setShowSuggestions(false);
    try {
      const res = await sendCopilotMessage(msg, runId || 'default');
      setMessages(prev => [...prev, { role: 'assistant', text: res.reply }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', text: `Error: ${err.message}. Is the backend running?` }]);
    } finally {
      setLoading(false);
    }
  };

  const reset = async () => {
    setMessages([{ role: 'assistant', text: WELCOME }]);
    setShowSuggestions(true);
    try {
      const axios = (await import('axios')).default;
      await axios.post(`/api/copilot/reset/${runId || 'default'}`);
    } catch { /* silent */ }
  };

  return (
    <div className="rq-copilot" style={{
      width: 380, height: '100vh', flexShrink: 0,
      borderLeft: '1px solid var(--border)',
      background: 'var(--bg-subtle)',
      display: 'flex', flexDirection: 'column',
      boxShadow: 'var(--shadow-lg)',
    }}>
      {/* Header */}
      <div style={{
        padding: '13px 16px',
        borderBottom: '1px solid var(--border)',
        background: '#fff',
        display: 'flex', alignItems: 'center', gap: 9,
      }}>
        <div style={{ width: 28, height: 28, borderRadius: 7, background: 'var(--accent-blue-light)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <MessageSquare size={14} color="var(--accent-blue)" />
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>Copilot</div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
            {runId ? `Run ${runId.slice(0,8)}` : 'No run'} · Gemini + Groq fallback
          </div>
        </div>
        <button onClick={reset} title="Reset conversation" className="rq-btn" style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4, borderRadius: 5 }}>
          <RefreshCw size={13} />
        </button>
        <button onClick={onClose} className="rq-btn" style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4, borderRadius: 5 }}>
          <X size={15} />
        </button>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 12px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {messages.map((m, i) => <MsgBubble key={i} role={m.role} text={m.text} />)}

        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 26, height: 26, borderRadius: 6, background: '#f4f4f5', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Bot size={12} color="var(--text-secondary)" />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '8px 12px', background: '#fff', border: '1px solid var(--border)', borderRadius: 10, boxShadow: 'var(--shadow-sm)' }}>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Querying data</span>
              {[0,1,2].map(i => (
                <div key={i} style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--accent-blue)', opacity: 0.7, animation: 'bounce 0.5s infinite alternate', animationDelay: `${i * 0.15}s` }} />
              ))}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Suggestion chips */}
      {showSuggestions && (
        <div style={{ padding: '0 12px 10px', display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4, paddingLeft: 2 }}>Suggested questions</div>
          {SUGGESTIONS.map((s, i) => (
            <button key={i} onClick={() => send(s)} className="rq-chip" style={{
              textAlign: 'left', fontSize: 12, padding: '6px 10px', borderRadius: 7,
              background: '#fff', color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
              cursor: 'pointer',
            }}>
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={{ padding: '10px 12px', borderTop: '1px solid var(--border)', background: '#fff', display: 'flex', gap: 8, alignItems: 'flex-end' }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input); } }}
          placeholder="Ask about your data..."
          rows={1}
          style={{
            flex: 1, padding: '8px 11px', borderRadius: 8,
            background: 'var(--bg-subtle)', border: '1px solid var(--border)',
            color: 'var(--text-primary)', fontSize: 13, resize: 'none',
            maxHeight: 100, outline: 'none', lineHeight: 1.5, fontFamily: 'inherit',
          }}
        />
        <button
          onClick={() => send(input)}
          disabled={!input.trim() || loading}
          className="rq-btn"
          style={{
            width: 34, height: 34, borderRadius: 8,
            border: 'none',
            background: input.trim() && !loading ? 'var(--accent-blue)' : '#f4f4f5',
            color: input.trim() && !loading ? '#fff' : 'var(--text-muted)',
            cursor: input.trim() && !loading ? 'pointer' : 'not-allowed',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
