import { ChevronLeft, ChevronRight, SquarePen, Trash2, User, Settings2 } from "lucide-react"
import type { Message } from "@/components/chat"
import { v4 } from "uuid"
import { useState } from "react"

type ChatSession = {
  id: string
  name: string
  history: Message[]
}

type SidebarProps = {
  chats: { id: string; name: string; history: Message[] }[]
  sidebarOpen: boolean
  activeChatId: string | null
  setActiveChatId: (id: string | null) => void
  setChats: React.Dispatch<React.SetStateAction<ChatSession[]>>
  setSidebarOpen: React.Dispatch<React.SetStateAction<boolean>>
  currentChatIsEmpty: boolean
}

export function Sidebar({
  chats,
  sidebarOpen,
  activeChatId,
  setActiveChatId,
  setChats,
  setSidebarOpen,
  currentChatIsEmpty,
  username,
  onSignIn,
  onSignOut,
  onOpenSettings
}: SidebarProps & {
  username: string | null,
  onSignIn: () => void,
  onSignOut: () => void,
  onOpenSettings: () => void
}) {

  function createNewChat() {
    const title = "New Chat"
    const newChat: ChatSession = {
      id: v4(),
      name: title,
      history: [],
    }
    setChats((prev) => [...prev, newChat])
    setActiveChatId(newChat.id)
  }
  
  async function deleteChat(chatId: string) {
    const token = localStorage.getItem("access_token");
    await fetch(`http://${process.env.NEXT_PUBLIC_HOST_IP}:8000/chats/${chatId}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    setChats((prev) => prev.filter((chat) => chat.id !== chatId));
    if (chatId === activeChatId) {
      const remaining = chats.filter((chat) => chat.id !== chatId);
      setActiveChatId(remaining.length > 0 ? remaining[0].id : null);
    }
  }

  // Sidebar content
  const sidebarContent = (
    <div className="h-full flex flex-col justify-between">
      {/* New Chat button with extra spacing */}
      <div className="px-2 py-4">
        <button
          onClick={createNewChat}
          disabled={currentChatIsEmpty}
          className="flex items-center gap-2 px-3 py-2 rounded-3xl hover:bg-neutral-200 hover:dark:bg-neutral-700 text-responsive-base text-neutral-800 dark:text-neutral-100 font-semibold w-full"
        >
          <SquarePen size={16} />
          <span>New Chat</span>
        </button>
      </div>
      {/* Chat list with extra spacing */}
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        <ul className="space-y-2">
          {chats.map((chat) => (
            <li key={chat.id}>
              <div className={`group flex justify-center rounded-3xl text-responsive-base ${
                chat.id === activeChatId
                  ? `bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-400 dark:hover:bg-neutral-600 font-semibold text-neutral-800 dark:text-neutral-100`
                  : `hover:bg-neutral-200 hover:dark:bg-neutral-700 font-medium text-neutral-600 dark:text-neutral-400`
              }`}>
                <button
                  onClick={() => setActiveChatId(chat.id)}
                  className="px-3 py-2 w-full text-left truncate"
                  title={chat.name}
                >
                  {chat.name}
                </button>
                <button
                  onClick={() => deleteChat(chat.id)}
                  className={`group-hover:opacity-100 transition-opacity text-neutral-400 hover:text-red-500 mr-3 ${chat.id == activeChatId ? "opacity-100" : "opacity-0"}`}
                  title="Delete chat"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>
      {/* Bottom row: Profile & Settings */}
      <div className="flex items-center justify-between gap-2 px-2 pt-4 pb-2">
        <button
          className="flex items-center gap-2 rounded-3xl pr-3 hover:bg-neutral-200 hover:dark:bg-neutral-700 text-responsive-base text-neutral-800 dark:text-neutral-100 font-semibold"
          onClick={username ? onSignOut : onSignIn}
        >
          <span className="inline-flex items-center justify-center p-2 rounded-full bg-neutral-200 dark:bg-neutral-700 mr-1">
            <User size={18} className="text-neutral-500 dark:text-neutral-200" />
          </span>
          {username ? username : "Sign In"}
        </button>
        <button
          className="flex items-center gap-2 p-2 rounded-3xl hover:bg-neutral-200 hover:dark:bg-neutral-700 text-responsive-sm text-neutral-800 dark:text-neutral-100 font-semibold"
          onClick={onOpenSettings}
        >
          <Settings2 size={16} />
        </button>
      </div>
    </div>
  )

  return (
    <div className="fixed inset-y-0 left-0 w-[18vw] max-w-[18vw] min-w-[200px] bg-neutral-100 dark:bg-neutral-800 z-40 flex flex-col">
      {sidebarContent}
    </div>
  )
}