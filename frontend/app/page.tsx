'use client'

import type React from "react"
import { useState, useEffect } from "react"
import { v4 } from "uuid"

import { ChatInput, MessageList, Message } from "@/components/chat"
import SettingsMenu from "@/components/SettingsMenu"
import { Sidebar } from "@/components/Sidebar"
import LoginForm from "@/components/LoginForm"
import { ContextWindow } from "@/components/ContextWindow"

type ChatSession = {
  id: string
  name: string
  history: Message[]
}

export default function Chat() {
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [useWebSearch, setUseWebSearch] = useState(false)
  const [chats, setChats] = useState<ChatSession[]>([])
  const [activeChatId, setActiveChatId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [useDoubleRetrievers, setUseDoubleRetrievers] = useState(true)
  const [token, setToken] = useState<string | null>(null)
  const [username, setUsername] = useState<string | null>(null)
  const [showLoginForm, setShowLoginForm] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamController, setStreamController] = useState<AbortController | null>(null);
  const [contextData, setContextData] = useState<any>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  // Add state for controlling context window
  const [contextIsOpen, setContextIsOpen] = useState(false);

  useEffect(() => {
    const storedToken = localStorage.getItem("access_token")
    const storedUsername = localStorage.getItem("username")   
    if (storedToken) setToken(storedToken)
    if (storedUsername) setUsername(storedUsername)
  }, [])

  useEffect(() => {
    if (token) {
      console.log(token)
      fetch(`http://${process.env.NEXT_PUBLIC_HOST_IP}:8000/chats`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      .then(res => {
        if (res.status === 401) {
          localStorage.removeItem("access_token")
          localStorage.removeItem("username")
          setToken(null)
          setUsername(null)
          throw new Error("Unauthorized")
        }
        return res.json()
      })
      .then(data => {
        const loadedChats = data.map((chat: any) => ({
          id: chat._id,
          name: chat.history?.[0]?.content?.slice(0, 30) || "New Chat",
          history: chat.history,
        }))
        setChats(loadedChats)
        if (loadedChats.length > 0) {
          setActiveChatId(loadedChats[0].id)
        }
      })
      .catch(err => {
        console.error("Failed to load chats", err)
      })
    }
  }, [token])

  const activeChat = chats.find((c) => c.id === activeChatId)
  const history = activeChat?.history ?? []
  const currentChatIsEmpty = history.length === 0

  function generateChatTitle(message: string): string {
    const stopwords = new Set(["the", "a", "an", "of", "to", "is", "and", "in", "on", "with", "that", "for", "as"]);
    const words = message.trim().split(/\s+/).filter(word => !stopwords.has(word.toLowerCase()));
    const firstFew = words.slice(0, 6).join(" ");
    const title = firstFew[0] + firstFew.slice(1);
    return `${title}`;
  }

  const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  if (!input.trim()) return;
  const userMessage: Message = { role: "user", content: input };

  setChats((prevChats) =>
    prevChats.map((chat) =>
      chat.id === activeChatId
        ? { ...chat, history: [...chat.history, userMessage] }
        : chat
    )
  );

  setInput("");
  setIsLoading(true);
  setIsStreaming(true);

  const controller = new AbortController();
  setStreamController(controller);

    try {
      const response = await fetch(`http://${process.env.NEXT_PUBLIC_HOST_IP}:8000/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}`},
        body: JSON.stringify({ 
          query: userMessage.content, 
          history: history, 
          use_web_search: useWebSearch,
          use_double_retrievers: useDoubleRetrievers, 
          chat_id: activeChatId
        }),
        signal: controller.signal,
      })
      if (!response.ok || !response.body) throw new Error("Failed to get response")

      let assistantMessage = ""
      setChats((prevChats) =>
        prevChats.map((chat) =>
          chat.id === activeChatId
            ? {
                ...chat,
                history: [...chat.history, { role: "assistant", content: "" }],
              }
            : chat
        )
      )

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        let chunk = decoder.decode(value)
        if (chunk.includes("[CONTEXT START]")) {
          const start = chunk.indexOf("[CONTEXT START]");
          const end = chunk.indexOf("[CONTEXT END]");
          const jsonStr = chunk.substring(start + 15, end);
          console.log("EXTRACTED JSON STRING:", jsonStr);
          try {
            const parsed = JSON.parse(jsonStr);
            console.log("PARSED CONTEXT DATA:", parsed);
            setContextData(parsed);
          } catch (err) {
            console.warn("Failed to parse context data:", err);
          }
          chunk = chunk.replace(/\[CONTEXT START\][\s\S]*?\[CONTEXT END\]/, "");
        }
        assistantMessage += chunk
        setChats((prevChats) =>
          prevChats.map((chat) =>
            chat.id === activeChatId
              ? {
                  ...chat,
                  history: chat.history.map((msg, idx) =>
                    idx === chat.history.length - 1 && msg.role === "assistant"
                      ? { ...msg, content: assistantMessage }
                      : msg
                  ),
                }
              : chat
          )
        )
      }
    } catch (err: any) {
      if (err.name === "AbortError") {
        setChats((prevChats) =>
          prevChats.map((chat) =>
            chat.id === activeChatId
              ? {
                  ...chat,
                  history: chat.history.map((msg, idx) =>
                    idx === chat.history.length - 1 && msg.role === "assistant"
                      ? { ...msg, content: "[Stopped]" }
                      : msg
                  ),
                }
              : chat
          )
        )
      } else {
        setChats((prevChats) =>
          prevChats.map((chat) =>
            chat.id === activeChatId
              ? {
                  ...chat,
                  history: [
                    ...chat.history,
                    { role: "assistant", content: "Sorry, there was an error processing your request." },
                  ],
                }
              : chat
          )
        )
      }
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
      setStreamController(null);
    }
  }
  
  const isEmpty = history.length === 0
  
  useEffect(() => {
    if (chats.length === 0 && !activeChatId) {
      const newChatId = v4();
      const defaultChat: ChatSession = {
        id: newChatId,
        name: "New Chat",
        history: [],
      };
      setChats([defaultChat]);
      setActiveChatId(newChatId);
    }
  }, [activeChatId, chats.length]);

  useEffect(() => {
    if (history.length ===  1 && activeChatId) {
      const newTitle = generateChatTitle(history[0].content)
      setChats((prevChats) =>
        prevChats.map((chat) =>
          chat.id === activeChatId ? { ...chat, name: newTitle } : chat
        )
      )
    }
  }, [history, activeChatId])

  function handleSignIn() {
    setShowLoginForm(true);
  }
  function handleSignOut() {
    setToken(null);
    setUsername(null);
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
  }

  return showLoginForm
  ? <LoginForm
      onLogin={(tok, user) => {
        setToken(tok);
        setUsername(user);
        setShowLoginForm(false);
      }}
      onGuest={() => setShowLoginForm(false)}
    />
  : (
    <div className="bg-neutral-200 dark:bg-neutral-800 font-sans h-screen overflow-hidden flex">
      <SettingsMenu        
        useDoubleRetrievers={useDoubleRetrievers}
        setUseDoubleRetrievers={setUseDoubleRetrievers}
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />

      <Sidebar
        chats={chats}
        sidebarOpen={sidebarOpen}
        activeChatId={activeChatId}
        setActiveChatId={setActiveChatId}
        setChats={setChats}
        setSidebarOpen={setSidebarOpen}
        currentChatIsEmpty={currentChatIsEmpty}
        username={username}
        onSignIn={handleSignIn}
        onSignOut={handleSignOut}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      <div 
        className="flex-1 flex flex-col items-center p-4 relative bg-white dark:bg-neutral-900 rounded-lg m-2" 
        style={{ marginRight: '25vw', marginLeft: "4vw"}}
      >
        <div className={`w-full max-w-4xl flex flex-col items-center h-full ${isEmpty ? "justify-center" : ""}`}>
          {isEmpty && (
            <div className="text-center">
              <p className="font-medium text-neutral-700 dark:text-neutral-300 text-responsive-3xl">
                What can I help you find today?
              </p>
            </div>
          )}
          
          <MessageList messages={history} isLoading={isLoading} />
          
          <ChatInput
            input={input}
            setInput={setInput}
            isLoading={isLoading}
            useWebSearch={useWebSearch}
            setUseWebSearch={setUseWebSearch}
            onSubmit={handleSubmit}
            isStreaming={isStreaming}
            onStop={() => {
              if (streamController) {
                streamController.abort();
              }
            }}
          />
        </div>

        {isEmpty && (
          <p className="absolute bottom-3 left-1/2 -translate-x-1/2 text-center text-neutral-500 dark:text-neutral-400 max-w-xl mx-auto text-responsive-xs">
            <strong className="text-neutral-700 dark:text-neutral-300">Disclaimer:</strong> This system uses AI-generated content. The information provided may be incomplete, outdated, or incorrect.{" "}
            <strong className="text-neutral-700 dark:text-neutral-300">
              Do not rely on this tool as a sole source for decision-making. Always verify with official documentation and authoritative sources.
            </strong>
          </p>
        )}
      </div>

      <ContextWindow 
        contextChunks={contextData} 
        isOpen={contextIsOpen}
        setIsOpen={setContextIsOpen}
        chatId={activeChatId}
        token={token}
      />
    </div>
  )
}