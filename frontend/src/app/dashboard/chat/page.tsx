"use client";

import { useState, FormEvent, useRef, useEffect } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

const SYSTEM_MESSAGE: Message = {
  role: "assistant",
  content:
    "Bonjour. Je suis le Head Coach Resilio+. Le mode chat interactif sera disponible dans la prochaine version. " +
    "En attendant, utilisez les pages Plan et Calendrier pour générer vos séances hebdomadaires.",
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([SYSTEM_MESSAGE]);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = { role: "user", content: input.trim() };
    const botReply: Message = {
      role: "assistant",
      content:
        "Le mode chat sera disponible dans la prochaine version. Consultez la page Calendrier pour votre plan de la semaine.",
    };
    setMessages((prev) => [...prev, userMessage, botReply]);
    setInput("");
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <h2 className="text-xl font-semibold text-slate-100 mb-4">Chat — Head Coach</h2>

      <div className="flex-1 overflow-y-auto space-y-3 mb-4 pr-1">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[75%] rounded-lg px-4 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-violet-700 text-white"
                  : "bg-slate-800 text-slate-200 border border-slate-700"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Écrivez votre message..."
          className="flex-1 px-3 py-2 text-sm rounded bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-violet-500"
        />
        <button
          type="submit"
          className="px-4 py-2 text-sm rounded bg-violet-600 hover:bg-violet-500 text-white transition-colors"
        >
          Envoyer
        </button>
      </form>
    </div>
  );
}
