import { useState, useEffect } from "react"
import { DocumentUpload } from "@/components/DocumentUpload"
import { FolderX } from "lucide-react"

function getFileName(path: string) {
  if (!path) return "Unknown Source"
  const parts = path.split(/[/\\]/)
  return parts[parts.length - 1]
}

interface ContextWindowProps {
  contextChunks: any[]
  isOpen?: boolean
  setIsOpen?: (open: boolean) => void
  chatId: string | null
  token: string | null
}

export function ContextWindow({ 
  contextChunks, 
  isOpen: externalIsOpen, 
  setIsOpen: externalSetIsOpen,
  chatId,
  token
}: ContextWindowProps) {
  const [internalIsOpen, setInternalIsOpen] = useState(false)
  const [openIndex, setOpenIndex] = useState<number | null>(null)
  const [fullTextModalIndex, setFullTextModalIndex] = useState<number | null>(null)
  const [uploadedDocuments, setUploadedDocuments] = useState<any[]>([])

  const isOpen = externalIsOpen !== undefined ? externalIsOpen : internalIsOpen
  const setIsOpen = externalSetIsOpen || setInternalIsOpen
  const safeChunks = Array.isArray(contextChunks) ? contextChunks : []

  useEffect(() => {
    if (safeChunks.length > 0) {
      setIsOpen(true)
    } else {
      setIsOpen(false)
      setOpenIndex(null)
    }
  }, [contextChunks])

  const handleDocumentsChange = (documents: any[]) => {
    setUploadedDocuments(documents)
    if (documents.length > 0) {
      setIsOpen(true)
    } else if (safeChunks.length === 0) {
      setIsOpen(false)
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
      <div
        className={`fixed top-0 right-0 z-40 w-[25vw] min-w-[200px] bg-neutral-200 dark:bg-neutral-800 h-screen flex flex-col`}
      >
        <div className="flex-shrink-0 p-2 pb-0">
          {chatId && (
            <DocumentUpload 
              chatId={chatId}
              token={token}
              onDocumentsChange={handleDocumentsChange}
            />
          )}
        </div>

        <div className="flex-1 overflow-hidden flex flex-col bg-white dark:bg-neutral-900 m-2 mt-0 rounded-lg">
          <h3 className="flex-shrink-0 text-responsive-lg font-medium p-3 pb-1 text-neutral-700 dark:text-neutral-300">
            Sources
          </h3>
          
          <div className="flex-1 overflow-y-auto p-3 pt-2 space-y-2">
            {safeChunks.length > 0 ? (
              safeChunks.map((group, i) => {
                const fullText = group.surrounding_chunks.map((c: any) => c.content).join("")
                const preview = fullText.length > 200 ? fullText.slice(0, 180) + "..." : fullText
                const isExpanded = openIndex === i
                const fileName = getFileName(group.retrieved_chunk?.metadata?.source)
                
                return (
                  <div key={i} className="border border-neutral-200 dark:border-neutral-700 rounded-md">
                    <button
                      className="w-full text-left p-3 font-semibold text-responsive-sm text-blue-700 dark:text-blue-300 focus:outline-none hover:bg-blue-50 dark:hover:bg-blue-900 transition-colors rounded-t-md"
                      onClick={() => setOpenIndex(isExpanded ? null : i)}
                      aria-expanded={isExpanded}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span 
                          className="text-responsive-base truncate max-w-[70%] font-medium" 
                          title={fileName}
                        >
                          {fileName}
                        </span>
                        <span className="ml-2 text-responsive-xs text-neutral-500 dark:text-neutral-400 flex-shrink-0">
                          {isExpanded ? "Hide" : "Show"}
                        </span>
                      </div>
                      
                      <div className="w-full">
                        <span 
                          className="truncate block text-responsive-xs text-neutral-500 dark:text-neutral-400 font-normal" 
                          title={group.retrieved_chunk?.metadata?.source}
                        >
                          {group.retrieved_chunk?.metadata?.source}
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
                        
                        {fullText.length > 200 && (
                          <div className="px-3 pb-3">
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                openFullTextModal(i)
                              }}
                              className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 text-responsive-xs underline transition-colors"
                            >
                              View Full Text
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
                <FolderX className="size-16 mx-auto text-red-400" />
                <div className="text-neutral-400 text-center py-8">
                  No retrieved data
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {fullTextModalIndex !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-[6px]">
          <div className="bg-white dark:bg-neutral-900 rounded-lg max-w-4xl max-h-[80vh] w-full flex flex-col">
            
            <div className="flex-shrink-0 flex items-center justify-between p-4 border-b border-neutral-200 dark:border-neutral-700">
              
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 truncate">
                  {getFileName(safeChunks[fullTextModalIndex]?.retrieved_chunk?.metadata?.source)}
                </h3>
                <p className="text-sm text-neutral-500 dark:text-neutral-400 truncate">
                  {safeChunks[fullTextModalIndex]?.retrieved_chunk?.metadata?.source}
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
                  {safeChunks[fullTextModalIndex]?.surrounding_chunks.map((c: any) => c.content).join("")}
                </div>
              </div>
            </div>

          </div>
        </div>
      )}
    </>
  )
}