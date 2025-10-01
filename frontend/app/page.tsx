'use client'

import type React from "react"
import { useState, useEffect } from "react"
import { v4 } from "uuid"

import { ChatInput, MessageList, Message } from "@/components/chat"
import SettingsMenu from "@/components/SettingsMenu"
import { Sidebar } from "@/components/Sidebar"
import LoginForm from "@/components/LoginForm"
import { ContextWindow } from "@/components/ContextWindow"

const WELCOME_MESSAGES = [
  "What can I help you find today?",
  "What are we working on today?",
  "Hi, let's get started.",
  "How can I assist you today?",
  "Ready when you are!",
  "What's on your mind?",
  "Let's explore together.",
] as const;

function getRandomGreeting(): string {
  const randomIndex = Math.floor(Math.random() * WELCOME_MESSAGES.length);
  return WELCOME_MESSAGES[randomIndex];
}

type ChatSession = {
  id: string
  name: string
  history: Message[]
}

export default function Chat() {

  // Chat states
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [chats, setChats] = useState<ChatSession[]>([])
  const [activeChatId, setActiveChatId] = useState<string | null>(null)
  const [randomGreeting, setRandomGreeting] = useState<string | null>(null)

  // Configuration states
  const [useWebSearch, setUseWebSearch] = useState(false)

  // Authentication state
  const [token, setToken] = useState<string | null>(null)
  const [username, setUsername] = useState<string | null>(null)
  const [showLoginForm, setShowLoginForm] = useState(false);

  // Streaming state
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamController, setStreamController] = useState<AbortController | null>(null);

  // Settings menu state
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [theme, setTheme] = useState<"light" | "dark">("light");

  // Context window state
  const [contextData, setContextData] = useState<any>(null);
  const [contextIsOpen, setContextIsOpen] = useState(false);

  // Editing state
  const [editingMessageIndex, setEditingMessageIndex] = useState<number | null>(null)
  const [editingContent, setEditingContent] = useState("")

  // Chat loading state
  const [loadingChats, setLoadingChats] = useState<Set<string>>(new Set())

  useEffect(() => {
    // Initialize theme
    const storedTheme = (localStorage.getItem("theme") as "light" | "dark") || null
    const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
    const initialTheme = storedTheme ?? (prefersDark ? "dark" : "light")
    setTheme(initialTheme)

    const storedToken = localStorage.getItem("access_token")
    const storedUsername = localStorage.getItem("username")
    
    if (storedToken && storedUsername) {
      // Validate token by trying to fetch chats
      fetch(`http://${process.env.NEXT_PUBLIC_HOST_IP}:${process.env.NEXT_PUBLIC_BACKEND_PORT}/chats`, {
        headers: { Authorization: `Bearer ${storedToken}` },
      })
      .then(res => {
        if (res.status === 401) {
          // Token is invalid, clear storage and show login
          localStorage.removeItem("access_token")
          localStorage.removeItem("username")
          localStorage.removeItem("password")
          setToken(null)
          setUsername(null)
          setShowLoginForm(true)
          throw new Error("Unauthorized")
        }
        return res.json()
      })
      .then(data => {
        // Token is valid, set user data and load chats
        setToken(storedToken)
        setUsername(storedUsername)
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
        console.error("Failed to validate token or load chats", err)
      })
    } else {
      setShowLoginForm(true)
    }
  }, [])

  useEffect(() => {
    localStorage.setItem("theme", theme)
  }, [theme])


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

  const handleSubmit = async (e: React.FormEvent, messageContent?: string, fromIndex?: number) => {
    e.preventDefault();
    
    const messageToSend = messageContent || input.trim();
    if (!messageToSend) return;

    let currentActiveChatId = activeChatId;
    if (!currentActiveChatId) {
      // Create a new chat immediately if none exists
      const newChatId = v4();
      const newRandomGreeting = getRandomGreeting();
      const newChat: ChatSession = {
        id: newChatId,
        name: "New Chat",
        history: [],
      };
      setChats(prevChats => [...prevChats, newChat]);
      setActiveChatId(newChatId);
      currentActiveChatId = newChatId;
      setRandomGreeting(newRandomGreeting);
    }

    let editedHistory: Message[];
    let userMessage: Message;

    if (fromIndex !== undefined) {
      editedHistory = history.slice(0, fromIndex);
      userMessage = { role: "user", content: messageToSend };
    } else {
      // Normal new message
      editedHistory = history;
      userMessage = { role: "user", content: messageToSend };
    }

    setChats((prevChats) =>
      prevChats.map((chat) =>
        chat.id === currentActiveChatId
          ? { ...chat, history: [...editedHistory, userMessage] }
          : chat
      )
    );

    setInput("");
    setEditingMessageIndex(null);
    setEditingContent("");
    setIsLoading(true);
    setIsStreaming(true);
    setLoadingChats(prev => new Set(prev).add(activeChatId!))

    const controller = new AbortController();
    setStreamController(controller);

    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      };
  
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
  
      const response = await fetch(`http://${process.env.NEXT_PUBLIC_HOST_IP}:${process.env.NEXT_PUBLIC_BACKEND_PORT}/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify({ 
          query: userMessage.content, 
          history: editedHistory, 
          use_web_search: useWebSearch,
          chat_id: currentActiveChatId
        }),
        signal: controller.signal,
      })
      if (response.status === 401) {
        // Token expired during request
        localStorage.removeItem("access_token")
        localStorage.removeItem("username")
        localStorage.removeItem("password")
        setToken(null)
        setUsername(null)
        setShowLoginForm(true)
        throw new Error("Unauthorized")
      }

      if (!response.ok || !response.body) throw new Error("Failed to get response")

      let assistantMessage = ""
      setChats((prevChats) =>
        prevChats.map((chat) =>
          chat.id === currentActiveChatId
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
          try {
            const parsed = JSON.parse(jsonStr);
            setContextData(parsed);
          } catch (err) {
            console.warn("Failed to parse context data:", err);
          }
          chunk = chunk.replace(/\[CONTEXT START\][\s\S]*?\[CONTEXT END\]/, "");
        }
        assistantMessage += chunk
        setChats((prevChats) =>
          prevChats.map((chat) =>
            chat.id === currentActiveChatId
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
            chat.id === currentActiveChatId
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
            chat.id === currentActiveChatId
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
      setLoadingChats(prev => {
        const newSet = new Set(prev)
        newSet.delete(currentActiveChatId!)
        return newSet
      })
    }
  }

  const handleEditMessage = (index: number, content: string) => {
    setEditingMessageIndex(index);
    setEditingContent(content);
  }

  const handleSaveEdit = (e: React.FormEvent) => {
    if (editingMessageIndex === null || !editingContent.trim()) return;
    handleSubmit(e, editingContent, editingMessageIndex);
  }

  const handleCancelEdit = () => {
    setEditingMessageIndex(null);
    setEditingContent("");
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
      setRandomGreeting(getRandomGreeting());

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
    setChats([]);
    setActiveChatId(null);
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("password");
  }

   function handleLogin(tok: string, user: string) {
    setToken(tok);
    setUsername(user);
    localStorage.setItem("access_token", tok);
    localStorage.setItem("username", user);
    setShowLoginForm(false);
    
    fetch(`http://${process.env.NEXT_PUBLIC_HOST_IP}:${process.env.NEXT_PUBLIC_BACKEND_PORT}/chats`, {
      headers: { Authorization: `Bearer ${tok}` },
    })
    .then(res => res.json())
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
      console.error("Failed to load chats after login", err)
    })
  }

  function handleGuest() {
    setShowLoginForm(false);
    setToken(null);
    setUsername(null);
    setChats([]);
    setActiveChatId(null);
    localStorage.removeItem("access_token");
    localStorage.removeItem("username");
    localStorage.removeItem("password")
  }

  useEffect(() => {
    // Clear context data when switching chats
    setContextData(null)
    setContextIsOpen(false)
  }, [activeChatId])

  return showLoginForm
  ? <LoginForm
      onLogin={handleLogin}
      onGuest={handleGuest}
    />
  : (
    <html className={theme === "dark" ? "dark" : ""}>
      <div className="bg-neutral-200 dark:bg-neutral-800 font-sans h-screen overflow-hidden flex">
        <SettingsMenu
          open={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          theme={theme}
          setTheme={setTheme}
        />

        <Sidebar
          chats={chats}
          activeChatId={activeChatId}
          setActiveChatId={setActiveChatId}
          setChats={setChats}
          currentChatIsEmpty={currentChatIsEmpty}
          username={username}
          onSignIn={handleSignIn}
          onSignOut={handleSignOut}
          onOpenSettings={() => setSettingsOpen(true)}
          loadingChats={loadingChats}
          setLoadingChats={setLoadingChats}
          streamController={streamController}
        />

        <div 
          className="flex-1 flex flex-col items-center p-4 relative bg-white dark:bg-neutral-900 rounded-lg m-2" 
          style={{ marginRight: '25vw', marginLeft: "3vw"}}
        >
          <div className={`w-full max-w-4xl flex flex-col items-center h-full ${isEmpty ? "justify-center" : ""}`}>
            {isEmpty && (
              <div className="text-center">
                <p className="font-medium text-neutral-700 dark:text-neutral-300 text-responsive-5xl">
                  {randomGreeting}
                </p>
              </div>
            )}
            
            <MessageList 
              messages={history} 
              isLoading={loadingChats.has(activeChatId!)}
              editingMessageIndex={editingMessageIndex}
              editingContent={editingContent}
              setEditingContent={setEditingContent}
              onEditMessage={handleEditMessage}
              onSaveEdit={handleSaveEdit}
              onCancelEdit={handleCancelEdit}
              isStreaming={isStreaming}
            />

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
            <p className="absolute bottom-3 left-1/2 -translate-x-1/2 text-center text-neutral-500 dark:text-neutral-400 max-w-xl mx-auto text-responsive-sm">
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
    </html>

  )
}