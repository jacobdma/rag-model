import { ChevronLeft, ChevronRight, SquarePen, Trash2 } from "lucide-react"
import type { Message } from "@/components/chat"

type ChatSession = {
  id: string
  name: string
  messages: Message[]
}

type SidebarProps = {
  chats: { id: string; name: string; messages: Message[] }[]
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
  currentChatIsEmpty
}: SidebarProps) {

  function createNewChat() {
    const title = "New Chat"
    const newChat: ChatSession = {
      id: crypto.randomUUID(),
      name: title,
      messages: [],
    }
    setChats((prev) => [...prev, newChat])
    setActiveChatId(newChat.id)
  }
  
  function deleteChat(chatId: string) {
    setChats((prev) => prev.filter((chat) => chat.id !== chatId))
    if (chatId === activeChatId) {
        const remaining = chats.filter((chat) => chat.id !== chatId)
        setActiveChatId(remaining.length > 0 ? remaining[0].id : null)
        }
  }

  return (
    <div className="fixed inset-y-0 left-0 flex items-center">
      <button
      className="z-2 py-5 mr-3 flex items-center gap-2
      rounded-r-2xl
      text-neutral-700 dark:text-neutral-300 font-semibold
      hover:bg-neutral-200 dark:hover:bg-neutral-800"
      onClick={() => setSidebarOpen(!sidebarOpen)}
      >
      {sidebarOpen ? <ChevronLeft size={25} /> : <ChevronRight size={25} />}
      </button>
      <div className="h-full flex flex-col justify-center"> 
        <div className={`
        border border-neutral-300 dark:border-neutral-700
        transition-all duration-200
        p-2 rounded-3xl  shadow-lg
        ${sidebarOpen ? "translate-x-0 w-72" : "-translate-x-72 w-0"} 
        `}>
          {sidebarOpen && (
            <>
              <button
                onClick={createNewChat}
                disabled={currentChatIsEmpty}
                className="flex items-center gap-2 justify-between px-3 py-2 mb-2 rounded-3xl
                          hover:bg-neutral-200 hover:dark:bg-neutral-800 
                          text-sm text-neutral-700 dark:text-neutral-300"
              >
                <SquarePen size={20} />
                <span className="font-semibold text-neutral-700 dark:text-neutral-300">New Chat</span>
              </button>

              <div className="overflow-y-auto">
                <ul className="space-y-2">
                  {chats.map((chat) => (
                    <li key={chat.id}>
                      <div className={`group flex justify-center rounded-3xl ${
                          chat.id === activeChatId
                            ? `bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700
                              font-semibold text-neutral-700 dark:text-neutral-300`
                            : `hover:bg-neutral-100 hover:dark:bg-neutral-800
                              font-medium text-neutral-500 dark:text-neutral-400`
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
                          className={`group-hover:opacity-100 transition-opacity
                            text-neutral-400 hover:text-red-500  
                            mr-3 ${chat.id == activeChatId 
                                ? "opacity-100" 
                                : "opacity-0"
                                }`}
                          title="Delete chat"
                        >
                          <Trash2 size={20} />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}