'use client'

import type React from "react"
import { useRef, useEffect } from "react"
import { Search, ArrowUp, Square } from "lucide-react"

export interface Message {
  role: "user" | "assistant"
  content: string
}

export function MessageList({ messages, isLoading }: { messages: Message[]; isLoading: boolean }) {
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  return (
    <div className={`flex-col overflow-y-auto mb-4 w-full max-w-xl mx-auto ${messages.length === 0 ? "" : "flex-1"}`}>
      {messages.map((message, index) => (
        <div key={index} className={`mb-4 ${message.role === "user" ? "text-right" : "text-left"}`}>
          <div className={`inline-block px-4 py-2 text-responsive-sm rounded-3xl break-words whitespace-pre-wrap text-left${
            message.role === "user" 
            ? `
              bg-neutral-100                  
              dark:bg-neutral-800
              text-neutral-700 
              dark:text-neutral-300
              font-medium
              max-w-[80%]
              `
            : `
              text-neutral-700
              dark:text-neutral-300
              font-medium
              max-w-[100%]
              `
            }`}>
            {message.content}
          </div>
        </div>
      ))}
      {isLoading && (
        <div className="text-left mb-4">
          <div className="inline-block px-4 py-2 rounded-lg text-neutral-800 dark:text-neutral-100">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-neutral-500 dark:bg-neutral-400 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-neutral-500 dark:bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
              <div className="w-2 h-2 bg-neutral-500 dark:bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: "0.4s" }}></div>
            </div>
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  )
}

export function ChatInput({ input, setInput, isLoading, useWebSearch, setUseWebSearch, onSubmit, isStreaming, onStop }: any) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  useEffect(() => {
            const textarea = textareaRef.current
            if (textarea) {
              textarea.style.height = "auto"
              textarea.style.height = textarea.scrollHeight + "px"
            }
          }, [input])
          
  return (
    <form onSubmit={onSubmit} className="w-full max-w-xl mx-auto">
      <div className="
      border border-neutral-300 
      dark:border-neutral-700 
      p-2
      rounded-3xl
      shadow-xl 
      mt-4
      text-responsive-base
      ">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          rows={1}
          className="
            w-full
            resize-none
            overflow-hidden
            p-2
            font-medium
            focus:outline-none
            text-neutral-700 
            dark:text-neutral-300
          "
          onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            onSubmit(e);
          }
          }}
        />
        <div className="flex items-center gap-2 justify-between w-full">
          <button
            type="button"
            onClick={() => setUseWebSearch(!useWebSearch)}
            className={`flex items-center gap-1 px-3 py-2 rounded-3xl ${
              useWebSearch
                ? `
                  bg-blue-50
                  dark:bg-blue-950
                  text-neutral-700 
                  dark:text-neutral-300
                  hover:bg-blue-100 
                  dark:hover:bg-blue-900
                  `
                : `
                  bg-neutral-100                  
                  dark:bg-neutral-800
                  text-neutral-700 
                  dark:text-neutral-300
                  hover:bg-neutral-200 
                  dark:hover:bg-neutral-700
                  `
            }`}
          >
            <Search size={16}/>
            <span className="text-responsive-sm font-semibold">Search</span>
          </button>
          {isStreaming ? (
            <button
              type="button"
              onClick={onStop}
              className="p-2 rounded-full bg-red-500 text-white font-semibold hover:bg-red-600 flex items-center justify-center"
            >
              <Square size={16} fill="white"/>
            </button>
          ) : (
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="p-2 rounded-full bg-green-500 text-white font-semibold hover:bg-green-600 flex items-center justify-center"
            >
              <ArrowUp size={16} />
            </button>
          )}
        </div>
      </div>
    </form>
  )
}