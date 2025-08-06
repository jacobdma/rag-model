'use client'

import type React from "react"
import { useRef, useEffect } from "react"
import { Search, Edit2 } from "lucide-react"

export interface Message {
  role: "user" | "assistant"
  content: string
}

interface MessageListProps {
  messages: Message[]
  isLoading: boolean
  editingMessageIndex: number | null
  editingContent: string
  setEditingContent: (content: string) => void
  onEditMessage: (index: number, content: string) => void
  onSaveEdit: (e: React.FormEvent) => void
  onCancelEdit: () => void
  isStreaming: boolean
}

export function MessageList({ 
  messages, 
  isLoading,
  editingMessageIndex,
  editingContent,
  setEditingContent,
  onEditMessage,
  onSaveEdit,
  onCancelEdit,
  isStreaming
 }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const editTextareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  useEffect(() => {
    if (editTextareaRef.current) {
      editTextareaRef.current.style.height = "auto"
      editTextareaRef.current.style.height = editTextareaRef.current.scrollHeight + "px"
    }
  }, [editingContent])

  useEffect(() => {
    if (editingMessageIndex !== null && editTextareaRef.current) {
      editTextareaRef.current.focus()
      const length = editTextareaRef.current.value.length
      editTextareaRef.current.setSelectionRange(length, length)
    }
  }, [editingMessageIndex])

  return (
    <div className={`flex-col overflow-y-auto mb-4 w-full max-w-xl mx-auto ${messages.length === 0 ? "" : "flex-1"}`}>
      {messages.map((message, index) => (
        <div key={index} className={`mb-4 group ${message.role === "user" ? "text-right" : "text-left"}`}>
          {editingMessageIndex === index ? (
            // Editing mode
            <div className="w-full rounded-lg p-3
                    bg-neutral-200 dark:bg-neutral-800
                    text-neutral-700 dark:text-neutral-300
                    font-medium text-responsive-base">
              <form onSubmit={onSaveEdit} className="w-full">
                <textarea
                  ref={editTextareaRef}
                  value={editingContent}
                  onChange={(e) => setEditingContent(e.target.value)}
                  className={"w-full resize-none overflow-hidden focus:outline-none"}
                />
                <div className="flex gap-2 mt-2 justify-end">
                  <button
                    type="button"
                    onClick={onCancelEdit}
                    className="flex items-center gap-1 px-3 py-2 rounded-lg text-responsive-base
                      bg-white dark:bg-neutral-700
                      border border-neutral-300 dark:border-neutral-700
                      text-neutral-700 dark:text-neutral-300 font-semibold
                      hover:bg-neutral-100 dark:hover:bg-neutral-600"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={!editingContent.trim()}
                    className="flex items-center gap-1 px-3 py-2 rounded-lg
                      bg-green-500 hover:bg-green-600 disabled:bg-neutral-400
                      font-semibold text-white text-responsive-base"
                  >
                    Send
                  </button>
                </div>
              </form>
            </div>
          ) : (
            // Normal message display
            <div className="relative">
              <div className={`inline-block px-2 py-2 text-responsive-base rounded-lg break-words whitespace-pre-wrap text-left${
                message.role === "user" 
                ? `
                  bg-neutral-200                  
                  dark:bg-neutral-800
                  text-neutral-700 
                  dark:text-neutral-300
                  font-medium
                  max-w-[80%]
                  mr-8
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
              
              {/* Edit button - only show for user messages and when not currently streaming */}
              {message.role === "user" && !isStreaming && !isLoading && (
                <button
                  onClick={() => onEditMessage(index, message.content)}
                  className="absolute right-1 top-2 opacity-100 p-1 rounded-lg
                    text-neutral-500 hover:text-neutral-700 
                    dark:text-neutral-400 dark:hover:text-neutral-200
                    hover:bg-neutral-200 dark:hover:bg-neutral-700"
                  title="Edit message"
                >
                  <Edit2 size={14}/>
                </button>
              )}
            </div>
          )}
        </div>
      ))}
      {isLoading && (
        <div className="text-left mb-4">
          <div className="inline-block px-4 py-2 rounded-lg text-neutral-800 dark:text-neutral-100">
            <div className="flex space-x-1">
              <div className="w-1 h-1 bg-neutral-500 dark:bg-neutral-400 rounded-full animate-bounce"></div>
              <div className="w-1 h-1 bg-neutral-500 dark:bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }}></div>
              <div className="w-1 h-1 bg-neutral-500 dark:bg-neutral-400 rounded-full animate-bounce" style={{ animationDelay: "0.4s" }}></div>
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
      rounded-lg
      mt-4
      text-responsive-lg
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
        <div className="flex items-center justify-between w-full">
          <button
            type="button"
            onClick={() => setUseWebSearch(!useWebSearch)}
            className={`flex items-center gap-1 px-3 py-2 rounded-lg ${
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
                  bg-neutral-200                  
                  dark:bg-neutral-800
                  text-neutral-700 
                  dark:text-neutral-300
                  hover:bg-neutral-200 
                  dark:hover:bg-neutral-700
                  `
            }`}
          >
            <Search size={16}/>
            <span className="text-responsive-base font-semibold">Search</span>
          </button>
          {isStreaming ? (
            <button
              type="button"
              onClick={onStop}
              className="p-2 rounded-lg bg-red-500 text-white font-semibold hover:bg-red-600 flex items-center justify-center"
            >
              <span className="text-responsive-base font-semibold">Stop</span>
            </button>
          ) : (
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="px-3 py-2 rounded-lg bg-green-500 text-white font-semibold hover:bg-green-600 flex items-center justify-center"
            >
              <span className="text-responsive-base font-semibold">Send</span>
            </button>
          )}
        </div>
      </div>
    </form>
  )
}