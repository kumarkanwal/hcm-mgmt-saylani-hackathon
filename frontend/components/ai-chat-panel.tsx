"use client";

import { useMutation } from "@tanstack/react-query";
import { Bot, Send, Sparkles, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";
import type { Role } from "@/lib/types";

type Message = { role: "user" | "assistant"; content: string; aiGenerated?: boolean };
type ChatResponse = { answer: string; tools_used: string[]; ai_generated: true };

const suggestions: Record<Role, string[]> = {
  admin: ["What is our current headcount?", "Summarize this month's payroll", "Show recent employee activity"],
  hr: ["Who is on leave today?", "Who came late most this month?", "Show upcoming holidays"],
  employee: ["How many sick leaves do I have left?", "What time am I considered late?", "Show my latest payslip"],
};

export function AiChatPanel({ open, onOpenChange, role }: { open: boolean; onOpenChange: (open: boolean) => void; role: Role }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const chat = useMutation({ mutationFn: (message: string) => api.post<ChatResponse>("/ai/chat", { message, history: messages.slice(-8).map((item) => ({ role: item.role, content: item.content })) }), onSuccess: (response) => setMessages((current) => [...current, { role: "assistant", content: response.answer, aiGenerated: response.ai_generated }]), onError: (error: ApiError) => setMessages((current) => [...current, { role: "assistant", content: error.status === 429 ? "The assistant request limit has been reached. Please try again later." : error.message }]) });
  const send = (text: string) => { if (!text.trim() || chat.isPending) return; setMessages((current) => [...current, { role: "user", content: text.trim() }]); setInput(""); chat.mutate(text.trim()); };
  if (!open) return null;
  return <><button className="fixed inset-0 z-40 bg-slate-900/20" onClick={() => onOpenChange(false)} aria-label="Close assistant" /><aside className="fixed inset-y-0 right-0 z-50 flex w-full flex-col border-l border-line bg-white shadow-2xl sm:w-[420px]"><header className="flex items-center justify-between border-b border-line p-5"><div><h2 className="text-xl font-bold">Assistant</h2><p className="text-sm text-muted">Ask questions about your HR data.</p></div><Button variant="ghost" size="icon" onClick={() => onOpenChange(false)}><X className="size-5" /></Button></header><div className="flex-1 overflow-y-auto p-5 scrollbar-thin"><div className="flex flex-wrap gap-2">{suggestions[role].map((item) => <button key={item} className="rounded-md border border-line bg-slate-50 px-3 py-2 text-left text-xs text-slate-600 hover:border-primary" onClick={() => send(item)}>{item}</button>)}</div>{!messages.length && <div className="flex min-h-80 flex-col items-center justify-center text-center"><span className="flex size-14 items-center justify-center rounded-full bg-teal-50 text-primary"><Bot className="size-7" /></span><h3 className="mt-4 font-semibold">How can I help?</h3><p className="mt-1 max-w-xs text-sm text-muted">Ask a suggested question or type your own message below.</p></div>}<div className="mt-6 space-y-4">{messages.map((message, index) => <div key={index} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}><div className={`max-w-[88%] rounded-xl px-4 py-3 text-sm leading-6 ${message.role === "user" ? "bg-teal-50 text-slate-800" : "bg-slate-50 text-slate-700"}`}>{message.role === "assistant" && <Bot className="mb-2 size-5 text-primary" />}<p className="whitespace-pre-wrap">{message.content}</p>{message.aiGenerated && <span className="mt-3 inline-flex items-center gap-1 rounded-full bg-slate-200 px-2 py-1 text-[10px] text-slate-600"><Sparkles className="size-3" />AI-generated</span>}</div></div>)}{chat.isPending && <div className="w-40 rounded-xl bg-slate-50 p-4"><div className="flex gap-1"><i className="size-2 animate-bounce rounded-full bg-slate-400" /><i className="size-2 animate-bounce rounded-full bg-slate-400 [animation-delay:120ms]" /><i className="size-2 animate-bounce rounded-full bg-slate-400 [animation-delay:240ms]" /></div></div>}</div></div><footer className="border-t border-line p-4"><div className="relative"><Input value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") send(input); }} placeholder="Ask a question..." className="pr-12" /><Button size="icon" className="absolute right-1 top-1 size-9" onClick={() => send(input)} disabled={!input.trim() || chat.isPending}><Send className="size-4" /></Button></div></footer></aside></>;
}
