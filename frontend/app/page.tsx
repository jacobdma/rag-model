'use client'

import type React from "react"
import { useState, useEffect } from "react"
import { v4 } from "uuid"

import { ChatInput, MessageList, Message } from "@/components/chat"
import SettingsMenu from "@/components/SettingsMenu"
import { Sidebar } from "@/components/Sidebar"
import LoginForm from "@/components/LoginForm"

type ChatSession = {
  id: string
  name: string
  history: Message[]
}

export default function Chat() {
  // All hooks at the top!
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [useWebSearch, setUseWebSearch] = useState(false)
  const [chats, setChats] = useState<ChatSession[]>([])
  const [activeChatId, setActiveChatId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [useDoubleRetrievers, setUseDoubleRetrievers] = useState(true)
  const [token, setToken] = useState<string | null>(null)
  const [username, setUsername] = useState<string | null>(null)

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

  // If no token, show login form
  const showLogin = !token;

  const activeChat = chats.find((c) => c.id === activeChatId)
  const history = activeChat?.history ?? []
  const currentChatIsEmpty = history.length === 0

  function generateChatTitle(message: string): string {
    const stopwords = new Set(["the", "a", "an", "of", "to", "is", "and", "in", "on", "with", "that", "for", "as"]);
    const words = message.trim().split(/\s+/).filter(word => !stopwords.has(word.toLowerCase()));
    const firstFew = words.slice(0, 6).join(" ");
    const title = firstFew[0].toUpperCase() + firstFew.slice(1);

    const lower = message.trim().toLowerCase();
    if (["how", "what", "why", "when", "where", "who"].some(q => lower.startsWith(q))) {
        return `Question: ${title}`;
    } else if (lower.startsWith("generate") || lower.startsWith("create")) {
        return `Request: ${title}`;
    } else {
        return `Topic: ${title}`;
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return
    const userMessage: Message = { role: "user", content: input }

  setChats((prevChats) =>
    prevChats.map((chat) =>
      chat.id === activeChatId
        ? {
            ...chat,
            history: [...chat.history, { role: "user", content: input }],
          }
        : chat
    )
  )

  setInput("")
  setIsLoading(true)


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
    })
    if (!response.ok || !response.body) throw new Error("Failed to get response")

    let assistantMessage = ""
    // Add an empty assistant message first
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
      const chunk = decoder.decode(value)
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
  } catch (err) {
    console.error("Error:", err)
    setChats((prevChats) =>
      prevChats.map((chat) =>
        chat.id === activeChatId
          ? {
              ...chat,
              history: [...chat.history, { role: "assistant", content: "Sorry, there was an error processing your request." }],
            }
          : chat
        )
      )
    } finally {
      setIsLoading(false)
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

  return showLogin
  ? <LoginForm onLogin={(tok, user) => {
      setToken(tok)
      setUsername(user)
      localStorage.setItem("access_token", tok)
      localStorage.setItem("username", user)
    }} />
  : (
    <div className="bg-white dark:bg-neutral-900 font-sans h-screen overflow-hidden">
      <div className="absolute top-4 left-4 z-50 bg-white dark:bg-neutral-800 px-3 py-1 rounded-full text-sm shadow text-neutral-800 dark:text-neutral-200">
        {username ? `Signed in as ${username}` : "Not signed in"}
      </div>
      <SettingsMenu
        useDoubleRetrievers={useDoubleRetrievers}
        setUseDoubleRetrievers={setUseDoubleRetrievers}
      />

      <div className="flex h-screen">
        <Sidebar
          chats={chats}
          sidebarOpen={sidebarOpen}
          activeChatId={activeChatId}
          setActiveChatId={setActiveChatId}
          setChats={setChats}
          setSidebarOpen={setSidebarOpen}
          currentChatIsEmpty={currentChatIsEmpty}
        />
        <div className={`w-full p-4 h-screen flex flex-col items-center ${isEmpty ? "justify-center" : ""}`}>
            {isEmpty && (
              <div className="text-center ">
                <p className="font-medium text-neutral-700 dark:text-neutral-300 text-3xl">
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
            />
        </div>
        {isEmpty && (
          <p className="absolute bottom-3 left-1/2 -translate-x-1/2 text-center text-neutral-500 dark:text-neutral-400 max-w-xl mx-auto mt-4 text-xs">
            <strong className="text-neutral-700 dark:text-neutral-300">Disclaimer:</strong> This system uses AI-generated content. The information provided may be incomplete, outdated, or incorrect.{" "}
            <strong className="text-neutral-700 dark:text-neutral-300">
              Do not rely on this tool as a sole source for decision-making. Always verify with official documentation and authoritative sources.
            </strong>
          </p>
        )}
      </div>
    </div>
  )
}
