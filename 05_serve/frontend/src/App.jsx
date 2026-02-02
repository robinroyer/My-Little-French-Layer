import { useState, useCallback } from 'react'
import Header from './components/Header'
import ChatWindow from './components/ChatWindow'
import InputBar from './components/InputBar'

export default function App() {
  const [messages, setMessages] = useState([])
  const [sources, setSources] = useState({})
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [useRag, setUseRag] = useState(true)
  const [selectedCodes, setSelectedCodes] = useState([])

  const sendMessage = useCallback(async (content) => {
    const timestamp = new Date().toISOString()
    const userMessage = { role: 'user', content, timestamp }

    setMessages((prev) => [...prev, userMessage])
    setError(null)
    setIsLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: content,
          history: messages,
          use_rag: useRag,
          selected_codes: selectedCodes,
        }),
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Erreur ${response.status}`)
      }

      const data = await response.json()

      const assistantMessage = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, assistantMessage])

      // Store sources indexed by message position
      if (data.sources && data.sources.length > 0) {
        setSources((prev) => ({
          ...prev,
          [messages.length + 1]: data.sources,
        }))
      }
    } catch (err) {
      console.error('Chat error:', err)
      setError(err.message || 'Une erreur est survenue')

      // Add error message to chat
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Desole, une erreur s'est produite : ${err.message}. Veuillez reessayer.`,
          timestamp: new Date().toISOString(),
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }, [messages, useRag, selectedCodes])

  const clearChat = useCallback(() => {
    setMessages([])
    setSources({})
    setError(null)
  }, [])

  const exportChat = useCallback(async (format) => {
    if (messages.length === 0) return

    try {
      const response = await fetch(`/api/export?format=${format}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ history: messages }),
      })

      if (!response.ok) throw new Error('Export failed')

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `mlfl_conversation.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Export error:', err)
      setError('Erreur lors de l\'export')
    }
  }, [messages])

  return (
    <div className="h-screen flex flex-col bg-legal-parchment">
      {/* Background texture */}
      <div className="fixed inset-0 pointer-events-none opacity-30">
        <div className="absolute inset-0 bg-gradient-to-b from-legal-cream via-legal-parchment to-stone-150" />
        <div className="absolute inset-0 bg-parchment-grain opacity-50" />
      </div>

      {/* Main content */}
      <div className="relative flex flex-col h-full z-10">
        <Header
          onClear={clearChat}
          onExport={exportChat}
          hasMessages={messages.length > 0}
        />

        <ChatWindow
          messages={messages}
          sources={sources}
          isLoading={isLoading}
        />

        <InputBar
          onSend={sendMessage}
          disabled={isLoading}
          useRag={useRag}
          onUseRagChange={setUseRag}
          selectedCodes={selectedCodes}
          onSelectedCodesChange={setSelectedCodes}
        />

        {/* Disclaimer */}
        <div className="px-4 py-2 text-center text-xs text-stone-500 bg-stone-100/50 border-t border-stone-200">
          <p>
            Cet outil est un assistant technique et ne constitue pas un conseil juridique.
            Pour toute question juridique, consultez un professionnel du droit.
          </p>
        </div>

        {/* Error toast */}
        {error && (
          <div className="fixed bottom-24 left-1/2 -translate-x-1/2 px-4 py-2 bg-red-50 text-red-700 rounded-lg shadow-legal border border-red-200 text-sm font-sans animate-fade-in z-50">
            {error}
            <button
              onClick={() => setError(null)}
              className="ml-3 text-red-500 hover:text-red-700"
            >
              x
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
