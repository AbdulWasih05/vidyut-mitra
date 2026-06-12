"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  MoreVertical,
  Paperclip,
  Search,
  Send,
  UserCircle,
  Phone,
  Video,
  Smile,
  Mic,
  Loader2,
  FileImage,
  Image as ImageIcon
} from "lucide-react";

type Message = {
  id: string;
  type: "text" | "audio" | "image" | "file";
  body?: string;
  url?: string;
  sender: "user" | "bot";
  time: string;
};

export default function ChatFallbackPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "msg-0",
      type: "text",
      body: "Welcome to VidyutMitra! Say 'Hi' to begin.",
      sender: "bot",
      time: "",
    }
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [mounted, setMounted] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMounted(true);
    setMessages(prev => [{
      ...prev[0],
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }]);
  }, []);

  // Scroll to bottom on new message
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSend = async () => {
    if (!inputValue.trim() && !selectedFile) return;

    const newMsgId = Date.now().toString();
    const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Optimistic UI for user message
    const formData = new FormData();
    formData.append("from", "web-user");
    
    const userMessages: Message[] = [];
    if (inputValue.trim()) {
      formData.append("body", inputValue);
      userMessages.push({
        id: `u-${newMsgId}-text`,
        type: "text",
        body: inputValue,
        sender: "user",
        time: currentTime,
      });
    }

    if (selectedFile) {
      formData.append("image", selectedFile);
      userMessages.push({
        id: `u-${newMsgId}-img`,
        type: "image",
        url: URL.createObjectURL(selectedFile),
        sender: "user",
        time: currentTime,
      });
    }

    setMessages((prev) => [...prev, ...userMessages]);
    setInputValue("");
    setSelectedFile(null);
    setIsLoading(true);

    try {
      const res = await fetch("http://localhost:5001/api/web-chat", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Server error");
      const data = await res.json();
      
      const botMessages: Message[] = data.responses.map((r: any, idx: number) => ({
        id: `b-${newMsgId}-${idx}`,
        type: r.type,
        body: r.body,
        url: r.url,
        sender: "bot",
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }));

      setMessages((prev) => [...prev, ...botMessages]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${newMsgId}`,
          type: "text",
          body: "Sorry, I couldn't reach the server right now.",
          sender: "bot",
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleSend();
    }
  };

  return (
    <div className="flex h-screen w-full bg-[#f0f2f5] overflow-hidden font-sans">
      {/* Left Sidebar */}
      <div className="w-[30%] min-w-[300px] border-r border-[#d1d7db] bg-white flex flex-col z-10 transition-transform md:translate-x-0 hidden md:flex">
        {/* Header */}
        <div className="h-[60px] bg-[#f0f2f5] flex items-center justify-between px-4">
          <UserCircle size={40} className="text-gray-500" />
          <div className="flex gap-4 text-[#54656f]">
            <Search size={20} className="cursor-pointer" />
            <MoreVertical size={20} className="cursor-pointer" />
          </div>
        </div>

        {/* Search */}
        <div className="p-2 bg-white">
          <div className="bg-[#f0f2f5] flex items-center rounded-lg px-3 py-1.5 object-cover">
            <Search size={18} className="text-[#54656f] mr-3" />
            <input
              type="text"
              placeholder="Search or start new chat"
              className="bg-transparent outline-none flex-1 text-sm text-[#3b4a54] placeholder-[#8696a0]"
            />
          </div>
        </div>

        {/* Chat List */}
        <div className="flex-1 overflow-y-auto bg-white">
          <div className="flex items-center px-3 py-3 hover:bg-[#f5f6f6] cursor-pointer transition-colors bg-[#f0f2f5]">
            <div className="w-12 h-12 bg-[#128c7e] rounded-full flex items-center justify-center text-white shrink-0 shadow-sm mr-3">
              <span className="font-semibold text-lg">VM</span>
            </div>
            <div className="flex-1 min-w-0 border-b border-[#f2f2f2] pb-3 -mb-3">
              <div className="flex justify-between items-center mb-0.5">
                <span className="font-normal text-[17px] text-[#111b21] truncate">VidyutMitra Bot</span>
                <span className="text-xs text-[#667781]">{messages[messages.length - 1]?.time || ""}</span>
              </div>
              <div className="text-sm text-[#667781] truncate">
                {messages[messages.length - 1]?.type === 'image' ? '📸 Photo' : messages[messages.length - 1]?.body || 'Start chatting'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col h-full bg-[#efeae2] relative w-full">
        {/* Header pattern overlay */}
        <div className="absolute inset-0 z-0 opacity-[0.06] pointer-events-none" style={{ backgroundImage: 'url("https://web.whatsapp.com/img/bg-chat-tile-dark_a4be512e7195b6b733d9110b408f075d.png")', backgroundSize: '400px' }} />

        {/* Header */}
        <div className="h-[60px] bg-[#f0f2f5] flex items-center justify-between px-4 z-10 sticky top-0 shadow-sm border-l border-[#d1d7db]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#128c7e] rounded-full flex items-center justify-center text-white shadow-sm shrink-0">
              <span className="font-semibold">VM</span>
            </div>
            <div>
              <h2 className="font-normal text-[16px] text-[#111b21]">VidyutMitra Bot</h2>
              <p className="text-xs text-[#667781]">online</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-[#54656f]">
             <Video size={20} className="cursor-pointer" />
             <Phone size={20} className="cursor-pointer" />
            <Search size={20} className="cursor-pointer" />
            <MoreVertical size={20} className="cursor-pointer lg:!ml-2" />
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-[5%] lg:px-[10%] py-4 z-10 flex flex-col" ref={scrollRef}>
           <div className="bg-[#ffeecd] px-3 py-1.5 rounded-lg text-xs text-[#54656f] text-center w-fit mx-auto shadow-sm mb-4">
              Messages to this chat and calls are strictly internal for the hackathon demo.
           </div>
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex mb-2 ${
                msg.sender === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[75%] min-w-[80px] rounded-lg px-3 pt-2 pb-6 shadow-sm relative text-[14px] ${
                  msg.sender === "user" ? "bg-[#d9fdd3] text-[#111b21]" : "bg-white text-[#111b21]"
                }`}
                style={{
                  borderTopRightRadius: msg.sender === 'user' ? '0' : '8px',
                  borderTopLeftRadius: msg.sender === 'bot' ? '0' : '8px'
                }}
              >
                {msg.type === "text" && (
                  <span className="whitespace-pre-wrap leading-relaxed">{msg.body}</span>
                )}
                {msg.type === "image" && msg.url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={msg.url} alt="Uploaded attachment" className="rounded-md max-w-full h-auto mt-1 max-h-[300px] object-contain" />
                )}
                {msg.type === "audio" && msg.url && (
                    <div className="mt-1 flex items-center min-w-[200px]">
                      <audio controls className="w-full h-[40px] appearance-none" src={msg.url} />
                    </div>
                )}
                <span className="absolute bottom-1 right-2 text-[10px] text-[#667781] select-none text-right">
                  {msg.time}
                </span>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex mb-2 justify-start">
              <div className="max-w-[65%] rounded-lg px-3 py-3 shadow-sm bg-white text-[#111b21] flex items-center gap-2" style={{ borderTopLeftRadius: '0' }}>
               <Loader2 size={16} className="animate-spin text-[#8696a0]" />
               <em className="text-sm text-[#8696a0]">Typing...</em>
              </div>
            </div>
          )}
        </div>

        {/* File Preview */}
        {selectedFile && (
           <div className="h-[60px] bg-[#f0f2f5] border-t border-[#d1d7db] px-4 flex items-center z-10 shadow-inner">
             <div className="bg-white px-3 py-1.5 rounded-lg text-sm border border-[#e9edef] flex items-center gap-2 relative">
               <span className="w-6 h-6 rounded bg-emerald-100 flex items-center justify-center text-emerald-600"><ImageIcon size={14}/></span>
               <span className="truncate max-w-[150px]">{selectedFile.name}</span>
               <button onClick={() => setSelectedFile(null)} className="ml-2 text-rose-500 font-bold hover:text-rose-700">×</button>
             </div>
           </div>
        )}

        {/* Input Area */}
        <div className="bg-[#f0f2f5] px-4 py-3 pb-6 sm:pb-3 flex items-center gap-3 z-10">
          <Smile size={26} className="text-[#54656f] cursor-pointer shrink-0" />
          <button 
             onClick={() => fileInputRef.current?.click()}
             className="shrink-0 p-2 hover:bg-[#d1d7db] rounded-full transition-colors relative"
             title="Attach Photo"
          >
            <Paperclip size={24} className="text-[#54656f] cursor-pointer" />
            <input 
              type="file" 
              ref={fileInputRef} 
              className="hidden" 
              accept="image/*"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setSelectedFile(e.target.files[0]);
                  // Reset input value to allow selecting same file again
                  e.target.value = '';
                }
              }} 
            />
          </button>
          
          <div className="flex-1 bg-white rounded-lg flex items-center px-3 py-2 border border-[#fff]">
            <input
              type="text"
              placeholder="Type a message"
              className="w-full bg-transparent outline-none text-[#111b21] text-[15px]"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
            />
          </div>
          
          <button 
             onClick={handleSend}
             disabled={isLoading || (!inputValue.trim() && !selectedFile)}
             className={`shrink-0 p-2 rounded-full transition-colors flex items-center justify-center ${
               (inputValue.trim() || selectedFile) && !isLoading ? "text-[#54656f] hover:bg-[#d1d7db]" : "text-[#8696a0]"
             }`}
          >
            { (inputValue.trim() || selectedFile) && !isLoading ? <Send size={24} /> : <Mic size={24} /> }
          </button>
        </div>
      </div>
    </div>
  );
}
