import { useState, useEffect, useRef } from "react"
import { DocumentUpload } from "@/components/DocumentUpload"

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

  return (
    <div
      className={`fixed top-0 right-0 z-40 w-[25vw] min-w-[200px] bg-neutral-200 dark:bg-neutral-800 h-screen min-h-[5rem] pl-2 pr-1 py-1`}
    >
        <div className="flex-1 overflow-y-auto space-y-4">
          {chatId && (
            <DocumentUpload 
              chatId={chatId}
              token={token}
              onDocumentsChange={handleDocumentsChange}
            />
          )}
        </div>

        <div className="flex-1 overflow-y-auto space-y-4 bg-white dark:bg-neutral-900 p-3 rounded-xl">
          <h3 className="text-responsive-base font-medium mb-3 text-neutral-700 dark:text-neutral-300">
            Sources
          </h3>
          {safeChunks.length > 0 ? (
            safeChunks.map((group, i) => {
              const fullText = group.surrounding_chunks.map((c: any) => c.content).join("")
              const preview = fullText.length > 300 ? fullText.slice(0, 220) + "..." : fullText
              const isExpanded = openIndex === i
              const fileName = getFileName(group.retrieved_chunk?.metadata?.source)
              return (
                <div key={i}>
                  <button
                    className="w-full text-left pb-3 font-semibold text-responsive-sm text-blue-700 dark:text-blue-300 rounded-t-xl focus:outline-none hover:bg-blue-50 dark:hover:bg-blue-900 transition-colors"
                    onClick={() => setOpenIndex(isExpanded ? null : i)}
                    aria-expanded={isExpanded}
                  >
                    <div className="flex items-center justify-between">
                      <span 
                        className="text-responsive-base truncate max-w-[70%]" 
                        title={fileName}
                      >
                        {fileName}
                      </span>
                      <span className="ml-2 text-responsive-sm text-neutral-500 dark:text-neutral-400 flex-shrink-0">
                        {isExpanded ? "Hide" : "Show"}
                      </span>
                    </div>
                    
                    <div className="w-full">
                      <span 
                        className="truncate block text-responsive-xs text-neutral-500 dark:text-neutral-400" 
                        title={group.retrieved_chunk?.metadata?.source}
                      >
                        {group.retrieved_chunk?.metadata?.source}
                      </span>
                    </div>
                  </button>
                  <div className="text-responsive-sm text-neutral-800 dark:text-neutral-200">
                    {isExpanded ? (
                      <div>{fullText}</div>
                    ) : (
                      <div className="text-neutral-600 dark:text-neutral-300">{preview}</div>
                    )}
                  </div>
                </div>
              )
            })
          ) : (
            <div className="text-neutral-500 dark:text-neutral-400">No retrieved data</div>
          )}
        </div>
      </div>
  )
}
