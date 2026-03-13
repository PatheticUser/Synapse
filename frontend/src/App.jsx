import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, Sparkles, Cpu, Trash2, User, Bot, Search } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_BASE_URL = 'http://localhost:8000';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(`session_${Math.random().toString(36).substr(2, 9)}`);
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const query = input;
    const userMessage = { role: 'user', content: query };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/research`, {
        query: query,
        session_id: sessionId
      });

      const agentMessage = { role: 'agent', content: response.data.answer };
      setMessages(prev => [...prev, agentMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, { role: 'agent', content: '### Connection Error\n\nI encountered an error connecting to the Synapse AI engine. Please ensure the backend server is running.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearHistory = async () => {
    try {
      await axios.delete(`${API_BASE_URL}/history/${sessionId}`);
      setMessages([]);
    } catch (error) {
      console.error('Error clearing history:', error);
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <div className="header-brand">
          <div className="brand-icon">
            <Sparkles size={20} />
          </div>
          <h1>Synapse AI</h1>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={clearHistory} className="icon-btn" title="Clear Chat">
            <Trash2 size={18} />
          </button>
        </div>
      </header>

      <main className="chat-window">
        {messages.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="empty-state"
          >
            <h2>How can I assist your research?</h2>
            <p>Synapse AI is ready to search the web, analyze academic papers, and synthesize complex information for you.</p>
          </motion.div>
        )}

        <AnimatePresence>
          {messages.map((msg, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="message-container"
            >
              <div className={`message ${msg.role}`}>
                <div className="message-label">
                  {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
                  {msg.role === 'user' ? 'You' : 'Synapse AI'}
                </div>
                <div className="message-body">
                  {msg.role === 'user' ? (
                    <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                  ) : (
                    <div className="markdown-content">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="message-container"
          >
            <div className="message agent">
              <div className="message-label">
                <Bot size={14} />
                Synapse AI
              </div>
              <div className="loading-indicator">
                <div className="loading-dot"></div>
                <div className="loading-dot"></div>
                <div className="loading-dot"></div>
              </div>
            </div>
          </motion.div>
        )}

        <div ref={chatEndRef} />
      </main>

      <div className="input-area-container">
        <div className="input-wrapper">
          <textarea
            ref={inputRef}
            rows="1"
            placeholder='Ask anything...'
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="send-btn"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;

