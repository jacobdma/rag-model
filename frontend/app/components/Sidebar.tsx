import { MessageCircle, SquarePen, Trash2, User, Settings2, LogOut, Search } from "lucide-react"
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
      {/* Top section */}
      <div className="flex flex-col items-center gap-4 py-4">
        {/* New Chat button */}
        <button
          onClick={createNewChat}
          disabled={currentChatIsEmpty}
          className="p-3 rounded-full hover:bg-neutral-200 hover:dark:bg-neutral-700 text-neutral-800 dark:text-neutral-100 disabled:opacity-50"
          title="New Chat"
        >
          <SquarePen size={20} />
        </button>
        
        {/* Chat list button */}
        <button
          onClick={() => setChatModalOpen(true)}
          className="p-3 rounded-full hover:bg-neutral-200 hover:dark:bg-neutral-700 text-neutral-800 dark:text-neutral-100"
          title="Chat History"
        >
          <MessageCircle size={20} />
        </button>
      </div>

      {/* Bottom section - Profile */}
      <div className="relative pb-4">
        <button
          className="p-3 rounded-full hover:bg-neutral-200 hover:dark:bg-neutral-700 text-neutral-800 dark:text-neutral-100"
          onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
          title={username || "Sign In"}
        >
          <User size={20} />
        </button>

        {/* Profile Dropdown */}
        {profileDropdownOpen && (
          <div 
            ref={profileDropdownRef}
            className="absolute bottom-full mb-2 left-0 bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-700 py-2 min-w-[160px] z-50"
          >
            {username ? (
              <>
                <div className="px-4 py-2 text-sm font-medium text-neutral-800 dark:text-neutral-100 border-b border-neutral-200 dark:border-neutral-700">
                  {username}
                </div>
                <button
                  onClick={() => {
                    onOpenSettings()
                    setProfileDropdownOpen(false)
                  }}
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700"
                >
                  <Settings2 size={16} />
                  Settings
                </button>
                <button
                  onClick={() => {
                    onSignOut()
                    setProfileDropdownOpen(false)
                  }}
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700"
                >
                  <LogOut size={16} />
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => {
                    onSignIn()
                    setProfileDropdownOpen(false)
                  }}
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700"
                >
                  <User size={16} />
                  Sign In
                </button>
                <button
                  onClick={() => {
                    onOpenSettings()
                    setProfileDropdownOpen(false)
                  }}
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-700"
                >
                  <Settings2 size={16} />
                  Settings
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )

  return (
    <>
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-[7vw] bg-neutral-100 dark:bg-neutral-800 z-40 flex flex-col">
        {sidebarContent}
      </div>

      {/* Chat Modal */}
      {chatModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 backdrop-blur-[6px]" />
          <div 
            ref={chatModalRef}
            className="relative bg-white dark:bg-neutral-900 rounded-3xl shadow-2xl border border-neutral-200 dark:border-neutral-700 w-full max-w-md mx-auto p-6 z-10 max-h-[80vh] flex flex-col"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="relative flex-1 mr-3">
                <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-neutral-400" />
                <input
                  type="text"
                  placeholder="Search chats..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-3 py-2 text-sm bg-neutral-100 dark:bg-neutral-800 rounded-3xl text-neutral-800 dark:text-neutral-100"
                />
              </div>
              <button
                onClick={() => {
                  createNewChat()
                  setChatModalOpen(false)
                }}
                disabled={currentChatIsEmpty}
                className="flex items-center gap-2 p-3 rounded-3xl hover:bg-neutral-100 dark:hover:bg-neutral-800 text-sm text-neutral-600 dark:text-neutral-400"
                title="New Chat"
              >
                <SquarePen size={16} />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto">
              {filteredChats.length === 0 ? (
                <p className="text-neutral-500 dark:text-neutral-400 text-center py-8">
                  {searchQuery ? "No chats found" : "No chats yet"}
                </p>
              ) : (
                <ul className="space-y-2">
                  {filteredChats.map((chat) => (
                    <li key={chat.id}>
                      <div className={`group flex items-center rounded-3xl text-sm ${
                        chat.id === activeChatId
                          ? `bg-neutral-200 dark:bg-neutral-700 font-semibold text-neutral-800 dark:text-neutral-100`
                          : `hover:bg-neutral-100 dark:hover:bg-neutral-800 font-medium text-neutral-600 dark:text-neutral-400`
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