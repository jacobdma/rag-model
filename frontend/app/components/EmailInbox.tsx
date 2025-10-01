import { useState, useEffect } from "react"
import { MailX, LogIn, RefreshCw } from "lucide-react"

interface Email {
  id: string
  subject: string
  sender: string
  datetime_received: string
  body: string
  synced_at: string
}

interface EmailInboxProps {
  userId: string | null
  token: string | null
  emailCredentials?: {
    username: string | null
    password: string | null
    email_address: string
    server: string
  }
}

export function EmailInbox({ userId, token, emailCredentials }: EmailInboxProps) {
  const [emails, setEmails] = useState<Email[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)
  const [openIndex, setOpenIndex] = useState<number | null>(null)
  const [fullTextModalIndex, setFullTextModalIndex] = useState<number | null>(null)
  const [syncMessage, setSyncMessage] = useState("")

  // Load emails on mount
  useEffect(() => {
    loadEmails()
  }, [userId])

  const loadEmails = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/emails/${userId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      
      if (response.ok) {
        const data = await response.json()
        setEmails(data.emails || [])
      }
    } catch (error) {
      console.error("Failed to load emails:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const syncEmails = async () => {
    if (!emailCredentials) {
      setSyncMessage("Email credentials not configured")
      return
    }

    setIsSyncing(true)
    setSyncMessage("Syncing emails...")

    try {
      const response = await fetch('http://localhost:8000/sync-emails', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          ...emailCredentials,
          user_id: userId
        })
      })

      if (response.ok) {
        const data = await response.json()
        setSyncMessage(data.message)
        
        // Reload emails after sync
        await loadEmails()
      } else {
        const error = await response.json()
        setSyncMessage(`Sync failed: ${typeof error.detail === "object" ? JSON.stringify(error.detail) : error.detail}`)
      }
    } catch (error) {
      console.error("Sync error:", error)
      setSyncMessage("Sync failed. Please try again.")
    } finally {
      setIsSyncing(false)
      
      // Clear message after 3 seconds
      setTimeout(() => setSyncMessage(""), 3000)
    }
  }

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
    } catch {
      return dateString
    }
  }

  const openFullTextModal = (index: number) => {
    setFullTextModalIndex(index)
  }

  const closeFullTextModal = () => {
    setFullTextModalIndex(null)
  }

  return (
    <>
      <div className="fixed top-0 right-0 z-40 w-[25vw] min-w-[200px] bg-neutral-200 dark:bg-neutral-800 h-screen flex flex-col">
        
        {/* Sync Button */}
        <div className="flex-shrink-0 p-2">
          {(emailCredentials && emailCredentials.password) ? (
            <button
              onClick={syncEmails}
              disabled={isSyncing}
              className={`w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors
                ${isSyncing 
                  ? 'bg-neutral-300 dark:bg-neutral-700 cursor-not-allowed' 
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
                }
              `}
            >
              <RefreshCw className={`size-4 ${isSyncing ? 'animate-spin' : ''}`} />
              {isSyncing ? 'Syncing...' : 'Sync Emails'}
            </button>
          ) : null}
          {syncMessage && (
            <div className="mt-2 text-xs text-center text-neutral-600 dark:text-neutral-400">
              {syncMessage}
            </div>
          )}
        </div>

        {/* Email List */}
        <div className="flex-1 overflow-hidden flex flex-col bg-white dark:bg-neutral-900 m-2 mt-0 rounded-lg">
          <h3 className="flex-shrink-0 text-responsive-lg font-medium p-3 pb-1 text-neutral-700 dark:text-neutral-300">
            Email Sources
          </h3>
          
          <div className="flex-1 overflow-y-auto p-3 pt-2 space-y-2">
            {isLoading ? (
              <div className="flex items-center justify-center h-full">
                <RefreshCw className="size-8 animate-spin text-blue-500" />
              </div>
            ) : emails.length > 0 ? (
              emails.map((email, i) => {
                const preview = email.body.length > 200 ? email.body.slice(0, 180) + "..." : email.body
                const isExpanded = openIndex === i
                
                return (
                  <div key={email.id} className="border border-neutral-200 dark:border-neutral-700 rounded-md">
                    <button
                      className="w-full text-left p-3 font-semibold text-responsive-sm text-blue-700 dark:text-blue-300 focus:outline-none hover:bg-blue-50 dark:hover:bg-blue-900 transition-colors rounded-t-md"
                      onClick={() => setOpenIndex(isExpanded ? null : i)}
                      aria-expanded={isExpanded}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span 
                          className="text-responsive-base truncate max-w-[70%] font-medium" 
                          title={email.subject}
                        >
                          {email.subject}
                        </span>
                        <span className="ml-2 text-responsive-xs text-neutral-500 dark:text-neutral-400 flex-shrink-0">
                          {isExpanded ? "Hide" : "Show"}
                        </span>
                      </div>
                      
                      <div className="w-full space-y-1">
                        <span 
                          className="truncate block text-responsive-xs text-neutral-500 dark:text-neutral-400 font-normal" 
                          title={email.sender}
                        >
                          From: {email.sender}
                        </span>
                        <span 
                          className="truncate block text-responsive-xs text-neutral-500 dark:text-neutral-400 font-normal"
                        >
                          {formatDate(email.datetime_received)}
                        </span>
                      </div>
                    </button>
                    
                    {isExpanded && (
                      <div className="border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50">
                        <div className="p-3 text-responsive-sm text-neutral-800 dark:text-neutral-200 max-h-48 overflow-y-auto">
                          <div className="whitespace-pre-wrap leading-relaxed">
                            {preview}
                          </div>
                        </div>
                        
                        {email.body.length > 200 && (
                          <div className="px-3 pb-3">
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                openFullTextModal(i)
                              }}
                              className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 text-responsive-xs underline transition-colors"
                            >
                              View Full Email
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })
            ) : (
              <div className="flex flex-1 flex-col items-center justify-center h-full">
                {(emailCredentials && emailCredentials.password) ? (
                  <>
                    <MailX className="size-16 mx-auto text-blue-400" />
                    <div className="text-neutral-400 text-center py-8">
                      No emails synced yet
                    </div>
                  </>
                ) : (
                  <>
                    <LogIn className="size-16 mx-auto text-blue-400" />
                    <div className="text-neutral-400 text-center py-8">
                      Sign in to view emails
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Full Text Modal */}
      {fullTextModalIndex !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-[6px]">
          <div className="bg-white dark:bg-neutral-900 rounded-lg max-w-4xl max-h-[80vh] w-full flex flex-col">
            
            <div className="flex-shrink-0 flex items-center justify-between p-4 border-b border-neutral-200 dark:border-neutral-700">
              
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 truncate">
                  {emails[fullTextModalIndex]?.subject}
                </h3>
                <p className="text-sm text-neutral-500 dark:text-neutral-400 truncate">
                  From: {emails[fullTextModalIndex]?.sender}
                </p>
                <p className="text-xs text-neutral-400 dark:text-neutral-500">
                  {formatDate(emails[fullTextModalIndex]?.datetime_received)}
                </p>
              </div>

              <button
                onClick={closeFullTextModal}
                className="ml-4 flex-shrink-0 p-2 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-md transition-colors"
                aria-label="Close modal"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>

            </div>
            
            <div className="flex-1 overflow-y-auto p-4">
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <div className="whitespace-pre-wrap leading-relaxed text-neutral-800 dark:text-neutral-200">
                  {emails[fullTextModalIndex]?.body}
                </div>
              </div>
            </div>

          </div>
        </div>
      )}
    </>
  )
}