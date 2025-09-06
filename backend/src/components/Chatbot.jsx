import React, { useState, useEffect, useRef } from "react";
import "../Chatbot.css"; // Import the CSS file

export default function Chatbot() {
  const API_URL = "http://localhost:8000";
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetch(`${API_URL}/`)
      .then((res) => {
        if (res.ok) setConnected(true);
        else setConnected(false);
      })
      .catch(() => setConnected(false));
  }, []);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { type: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input;
    setInput("");
    setIsTyping(true);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: currentInput }),
      });

      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        {
          type: "assistant",
          content: data.answer,
          docs: Array.isArray(data.retrieved_docs) ? data.retrieved_docs : [],
        },
      ]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { type: "error", content: "Error contacting server." },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">
        <h2 className="chatbot-title">Quest Parker - Professional Profile Chatbot</h2>
        <div className={`connection-status ${connected ? 'status-connected' : 'status-disconnected'}`}>
          <span>{connected ? "🟢" : "🔴"}</span>
          <span>{connected ? "Connected" : "Disconnected"}</span>
        </div>
      </div>
      
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-messages">
            <h3>👋 Welcome!</h3>
            <p>Ask me anything about Quest Parker's professional background, skills, or experience.</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`message message-${msg.type}`}>
              <div className="message-label">
                {msg.type === "user" ? "You" : msg.type === "assistant" ? "Quest Bot" : "Error"}
              </div>
              <div className="message-content">
                {msg.content}
              </div>
              {Array.isArray(msg.docs) && msg.docs.length > 0 && (
                <div className="message-sources">
                  <strong>Sources:</strong> {msg.docs.map((d) => d.title).join(", ")}
                </div>
              )}
            </div>
          ))
        )}
        
        {isTyping && (
          <div className="message message-assistant">
            <div className="message-label">Quest Bot</div>
            <div className="typing-indicator">
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      <div className="input-container">
        <input
          className="message-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about Quest's experience, skills, projects..."
          disabled={isTyping}
        />
        <button 
          className="send-button" 
          onClick={sendMessage}
          disabled={isTyping || !input.trim()}
        >
          {isTyping ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}