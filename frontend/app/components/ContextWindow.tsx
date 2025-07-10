import { useState } from "react"

export function ContextWindow({ contextChunks }: { contextChunks: any[] }) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <>
      <button onClick={() => setIsOpen(true)} className="mt-4 underline text-sm text-blue-600">
        View Context Chunks
      </button>
      {isOpen && (
        <div className="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full">
            <h2 className="text-lg font-semibold mb-4">Retrieved Context</h2>
            <div className="overflow-y-auto max-h-[60vh] text-sm whitespace-pre-wrap">
              {contextChunks.map((chunk, i) => (
                <div key={i} className="mb-4 border-b pb-2">
                  <div className="text-gray-500 mb-1">Source: {chunk.metadata?.source}</div>
                  <div className="text-gray-500 mb-1">Chunk: {chunk.metadata?.chunk_number}</div>
                  <pre>{chunk.content}</pre>
                </div>
              ))}
            </div>
            <button onClick={() => setIsOpen(false)} className="mt-4 bg-gray-200 px-4 py-1 rounded">
              Close
            </button>
          </div>
        </div>
      )}
    </>
  )
}
