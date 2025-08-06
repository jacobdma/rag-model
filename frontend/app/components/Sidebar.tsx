import { MessageCircle, Plus, Trash2, User, Settings2, LogOut, Search, X, SearchX } from "lucide-react"
import type { Message } from "@/components/chat"
import { v4 } from "uuid"
import { useState, useRef, useEffect } from "react"

type ChatSession = {
  id: string
  name: string
  history: Message[]
}

type SidebarProps = {
  chats: { id: string; name: string; history: Message[] }[]
  activeChatId: string | null
  setActiveChatId: (id: string | null) => void
  setChats: React.Dispatch<React.SetStateAction<ChatSession[]>>
  currentChatIsEmpty: boolean
  loadingChats: Set<string>
  setLoadingChats: React.Dispatch<React.SetStateAction<Set<string>>>
  streamController: AbortController | null
}

export function Sidebar({
  chats,
  activeChatId,
  setActiveChatId,
  setChats,
  currentChatIsEmpty,
  loadingChats,
  setLoadingChats,
  streamController,
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
  const [chatModalOpen, setChatModalOpen] = useState(false)
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const chatModalRef = useRef<HTMLDivElement>(null)
  const profileDropdownRef = useRef<HTMLDivElement>(null)

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
    setChats((prev) => prev.filter((chat) => chat.id !== chatId));
    if (chatId === activeChatId) {
      const remaining = chats.filter((chat) => chat.id !== chatId);
      setActiveChatId(remaining.length > 0 ? remaining[0].id : null);
    }

    // If chat is loading, abort it first
    if (loadingChats.has(chatId) && streamController) {
      streamController.abort() // Stop generation if chat is loading
      setLoadingChats(prev => {
        const newSet = new Set(prev)
        newSet.delete(chatId)
        return newSet
      })
    }

    try {
      const token = localStorage.getItem("access_token");
      await fetch(`http://${process.env.NEXT_PUBLIC_HOST_IP}:${process.env.NEXT_PUBLIC_BACKEND_PORT}/chats/${chatId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
    } catch (error) {
      console.error("Failed to delete chat:", error);
    }
  }

  function selectChat(chatId: string) {
    setActiveChatId(chatId)
    setChatModalOpen(false)
    setSearchQuery("") // Clear search when chat is selected
  }

  // Filter chats based on search query
  const filteredChats = chats.filter(chat => 
    chat.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Close chat modal on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (chatModalOpen && chatModalRef.current && !chatModalRef.current.contains(e.target as Node)) {
        setChatModalOpen(false)
        setSearchQuery("") // Clear search when modal closes
      }
    }
    if (chatModalOpen) {
      document.addEventListener("mousedown", handleClick)
    }
    return () => document.removeEventListener("mousedown", handleClick)
  }, [chatModalOpen])

  // Close profile dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (profileDropdownOpen && profileDropdownRef.current && !profileDropdownRef.current.contains(e.target as Node)) {
        setProfileDropdownOpen(false)
      }
    }
    if (profileDropdownOpen) {
      document.addEventListener("mousedown", handleClick)
    }
    return () => document.removeEventListener("mousedown", handleClick)
  }, [profileDropdownOpen])

  const sidebarContent = (
    <div className="h-full flex flex-col justify-between items-center">
      <div className="flex flex-col items-center gap-4 py-4">
        <button
          onClick={createNewChat}
          className="p-2 rounded-lg bg-green-500 hover:bg-green-600 dark:hover:bg-green-400 text-neutral-50"
          title="New Chat"
        >
          <Plus size={20} />
        </button>
        
        <button
          onClick={() => setChatModalOpen(true)}
          className="p-2 rounded-lg bg-neutral-50 dark:bg-neutral-700 text-neutral-800 dark:text-neutral-200 hover:bg-neutral-100 dark:hover:bg-neutral-600"
          title="Chat History"
        >
          <MessageCircle size={20} />
        </button>
      </div>

      <div className="relative pb-4">
        <button
          className="p-2 rounded-lg hover:bg-neutral-300 hover:dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300"
          onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
          title={username || "Sign In"}
        >
          <User size={20} />
        </button>

        {profileDropdownOpen && (
          <div 
            ref={profileDropdownRef}
            className="absolute bottom-full mb-2 left-0 bg-white dark:bg-neutral-800 rounded-lg border-neutral-200 dark:border-neutral-700 py-2 min-w-[160px] z-50"
          >
            {username ? (
              <div className="px-2">
                <div className="flex items-center gap-2 p-2 text-neutral-700 dark:text-neutral-300">
                  <User size={16} />
                  <div className="text-sm">
                    {username}
                  </div>
                </div>
                <button
                  onClick={() => {
                    onOpenSettings()
                    setProfileDropdownOpen(false)
                  }}
                  className="w-full flex items-center gap-2 p-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-lg"
                >
                  <Settings2 size={16} />
                  Settings
                </button>
                <button
                  onClick={() => {
                    onSignOut()
                    setProfileDropdownOpen(false)
                  }}
                  className="w-full flex items-center gap-2 p-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-lg"
                >
                  <LogOut size={16} />
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="px-2">
                <button
                  onClick={() => {
                    onSignIn()
                    setProfileDropdownOpen(false)
                  }}
                  className="w-full flex items-center gap-2 p-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-lg"
                >
                  <User size={16} />
                  Sign In
                </button>
                <button
                  onClick={() => {
                    onOpenSettings()
                    setProfileDropdownOpen(false)
                  }}
                  className="w-full flex items-center gap-2 p-2 text-sm text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-700 rounded-lg"
                >
                  <Settings2 size={16} />
                  Settings
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )

  return (
    <>
      <div className="fixed inset-y-0 left-0 w-[4vw] bg-neutral-200 dark:bg-neutral-800 z-51 flex flex-col">
        {sidebarContent}
      </div>

      {chatModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 backdrop-blur-[6px]" />
          <div 
            ref={chatModalRef}
            className="relative bg-white dark:bg-neutral-900 rounded-lg border border-neutral-200 dark:border-neutral-700 w-full max-w-md mx-auto p-6 z-10 max-h-[80vh] flex flex-col"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="relative flex-1 mr-3">
                <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-neutral-400" />
                <input
                  type="text"
                  placeholder="Search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-3 py-2 text-sm bg-neutral-200 dark:bg-neutral-800 rounded-lg text-neutral-800 dark:text-neutral-100 font-medium focus:outline-none"
                />
              </div>
              <button
                onClick={() => {
                  createNewChat()
                  setChatModalOpen(false)
                }}
                disabled={currentChatIsEmpty}
                className="flex items-center gap-2 p-2 rounded-lg bg-green-500 hover:bg-green-600 dark:hover:bg-green-400 text-neutral-50"
                title="New Chat"
              >
                <Plus size={20} />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto">
              {filteredChats.length === 0 ? (
                <div className="flex flex-1 flex-col items-center justify-center h-full mt-4">
                  {searchQuery ? <SearchX className="size-12 mx-auto text-red-400" /> : <X className="size-12 mx-auto text-neutral-400" />}
                  <p className="text-neutral-400 text-center py-4">
                    {searchQuery ? "No chats found" : "No chats yet"}
                  </p>
                </div>
              ) : (
                <ul className="space-y-2">
                  {filteredChats.map((chat) => (
                    <li key={chat.id}>
                      <div className={`group flex items-center rounded-lg text-sm ${
                        chat.id === activeChatId
                          ? `bg-neutral-200 dark:bg-neutral-700 font-semibold text-neutral-800 dark:text-neutral-100`
                          : `hover:bg-neutral-200 dark:hover:bg-neutral-800 font-medium text-neutral-600 dark:text-neutral-400`
                      }`}>
                        <button
                          onClick={() => selectChat(chat.id)}
                          className="px-3 py-2 w-full text-left truncate"
                          title={chat.name}
                        >
                          {chat.name}
                        </button>
                        <button
                          onClick={() => deleteChat(chat.id)}
                          className={`group-hover:opacity-100 transition-opacity text-neutral-400 hover:text-red-500 mr-3 ${chat.id === activeChatId ? "opacity-100" : "opacity-0"}`}
                          title="Delete chat"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}