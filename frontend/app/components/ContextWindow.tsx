import { useState, useEffect, useRef } from "react"

function getFileName(path: string) {
  if (!path) return "Unknown Source"
  const parts = path.split(/[/\\]/)
  return parts[parts.length - 1]
}

export function ContextWindow({ contextChunks }: { contextChunks: any[] }) {
  const [isOpen, setIsOpen] = useState(false)
  const [openIndex, setOpenIndex] = useState<number | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Always treat contextChunks as an array
  const safeChunks = Array.isArray(contextChunks) ? contextChunks : []

  // Automatically open/close popup based on contextChunks
  useEffect(() => {
    if (safeChunks.length > 0) {
      setIsOpen(true)
    } else {
      setIsOpen(false)
      setOpenIndex(null)
    }
  }, [contextChunks])

  // Calculate dynamic height
  const getContentHeight = () => {
    if (!containerRef.current) return undefined
    if (openIndex !== null) {
      return "max-h-[75vh]"
    }
    // Otherwise, shrink to fit previews (min-h for header)
    return ""
  }

  if (!isOpen) return null

  // Dynamic height classes
  const dynamicHeightClass = openIndex !== null ? "max-h-[75vh]" : ""

  return (
    <div
      ref={containerRef}
      className={`fixed top-0 right-0 z-40 w-[25vw] min-w-[200px] flex flex-col bg-neutral-100 dark:bg-neutral-800 h-screen min-h-[5rem] p-2`}
    >
      <div className="sticky top-0 flex items-center justify-between px-6 py-4 bg-neutral-100 dark:bg-neutral-800 z-10">
        <h2 className="text-responsive-sm font-medium text-neutral-800 dark:text-neutral-100">Retrieved Context</h2>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-4">
        {safeChunks.length > 0 ? (
          safeChunks.map((group, i) => {
            const fullText = group.surrounding_chunks.map((c: any) => c.content).join("")
            const preview = fullText.length > 100 ? fullText.slice(0, 100) + "..." : fullText
            const isExpanded = openIndex === i
            const fileName = getFileName(group.retrieved_chunk?.metadata?.source)
            return (
              <div key={i} className="border border-neutral-200 dark:border-neutral-700 rounded-xl bg-neutral-50 dark:bg-neutral-800">
                <button
                  className="w-full text-left px-4 py-3 font-semibold text-responsive-sm text-blue-700 dark:text-blue-300 rounded-t-xl focus:outline-none hover:bg-blue-50 dark:hover:bg-blue-900 transition-colors"
                  onClick={() => setOpenIndex(isExpanded ? null : i)}
                  aria-expanded={isExpanded}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span 
                      className="truncate max-w-[70%]" 
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
                      className="truncate block text-responsive-xs text-neutral-500 dark:text-neutral-400" 
                      title={group.retrieved_chunk?.metadata?.source}
                    >
                      {group.retrieved_chunk?.metadata?.source}
                    </span>
                  </div>
                </button>
                
                <div className="px-4 pb-4 pt-2 text-responsive-sm text-neutral-800 dark:text-neutral-200">
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
