'use client'

import type React from "react"
import { useState, useEffect, use } from "react"
import { uuid } from "uuidv4"

import { ChatInput, MessageList, Message } from "@/components/chat"
import SettingsMenu from "@/components/SettingsMenu"
import { Sidebar } from "@/components/Sidebar"

type ChatSession = {
  id: string
  name: string
  messages: Message[]
}

export default function Chat() {
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [useWebSearch, setUseWebSearch] = useState(false)
  const [chats, setChats] = useState<ChatSession[]>([])
  const [activeChatId, setActiveChatId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [useDoubleRetrievers, setUseDoubleRetrievers] = useState(true);

  const activeChat = chats.find((c) => c.id === activeChatId)
  const messages = activeChat?.messages ?? []
  const currentChatIsEmpty = messages.length === 0

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
            messages: [...chat.messages, { role: "user", content: input }],
          }
        : chat
    )
  )

  setInput("")
  setIsLoading(true)


  try {
    const response = await fetch(`http://${process.env.HOST_IP}:8000/stream-query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        query: userMessage.content, 
        history: messages, 
        use_web_search: useWebSearch,
        use_double_retrievers: useDoubleRetrievers, 
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
              messages: [...chat.messages, { role: "assistant", content: "" }],
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
                messages: chat.messages.map((msg, idx) =>
                  idx === chat.messages.length - 1 && msg.role === "assistant"
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
              messages: [...chat.messages, { role: "assistant", content: "Sorry, there was an error processing your request." }],
            }
          : chat
        )
      )
    } finally {
      setIsLoading(false)
    }
  }
  const isEmpty = messages.length === 0
  useEffect(() => {
    if (chats.length === 0) {
      const defaultChat: ChatSession = {
        id: uuid(),
        name: "New Chat",
        messages: [],
      }
      setChats([defaultChat])
      setActiveChatId(defaultChat.id)
    }
  }, [chats])

  useEffect(() => {
    if (messages.length ===  1 && activeChatId) {
      const newTitle = generateChatTitle(messages[0].content)
      setChats((prevChats) =>
      prevChats.map((chat) =>
        chat.id === activeChatId ? { ...chat, name: newTitle } : chat
      )
    )
  }
}, [messages, activeChatId])

  return (
    <div className="bg-white dark:bg-neutral-900 font-sans h-screen overflow-hidden">
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

            <MessageList messages={messages} isLoading={isLoading} />
            <ChatInput
              input={input}
              setInput={setInput}
              isLoading={isLoading}
              useWebSearch={useWebSearch}
              setUseWebSearch={setUseWebSearch}
              onSubmit={handleSubmit}
            />
        </div>
      </div>
    </div>
  )
}
