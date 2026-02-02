import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { LAW_CODES } from '../data/lawCodes'

export default function InputBar({ onSend, disabled, useRag, onUseRagChange, selectedCodes, onSelectedCodesChange }) {
  const [message, setMessage] = useState('')
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const textareaRef = useRef(null)
  const dropdownRef = useRef(null)

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px'
    }
  }, [message])

  // Focus on mount
  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const toggleCode = (codeId) => {
    if (selectedCodes.includes(codeId)) {
      onSelectedCodesChange(selectedCodes.filter((id) => id !== codeId))
    } else {
      onSelectedCodesChange([...selectedCodes, codeId])
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    const trimmed = message.trim()
    if (trimmed && !disabled) {
      onSend(trimmed)
      setMessage('')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
      className="relative bg-white border-t border-stone-250"
    >
      {/* Decorative top border */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-legal-gold/20 to-transparent" />

      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto p-4">
        <div className="relative flex items-end gap-3">
          {/* Input container with decorative border */}
          <div className="flex-1 relative">
            <div className="relative bg-legal-cream rounded-xl border border-stone-250 shadow-inner-subtle overflow-hidden transition-all duration-200 focus-within:border-legal-gold/40 focus-within:shadow-[0_0_0_3px_rgba(201,162,39,0.1)]">
              {/* Decorative corner */}
              <div className="absolute top-2 left-3 text-legal-gold/20 font-serif text-sm select-none pointer-events-none">

              </div>

              <textarea
                ref={textareaRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={disabled}
                placeholder="Posez votre question juridique..."
                rows={1}
                className="w-full px-4 py-3 pl-8 bg-transparent font-sans text-legal-ink placeholder:text-legal-mist resize-none outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ minHeight: '48px', maxHeight: '150px' }}
              />

              {/* Character hint */}
              <div className="absolute bottom-2 right-3 text-[10px] text-legal-mist font-sans opacity-0 transition-opacity duration-200" style={{ opacity: message.length > 0 ? 0.7 : 0 }}>
                Entree pour envoyer
              </div>
            </div>
          </div>

          {/* Send button */}
          <motion.button
            type="submit"
            disabled={disabled || !message.trim()}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="flex-shrink-0 w-12 h-12 rounded-xl bg-gradient-to-br from-legal-navy to-legal-slate text-white shadow-legal hover:shadow-legal-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center group"
          >
            {disabled ? (
              <LoadingSpinner />
            ) : (
              <svg
                className="w-5 h-5 transition-transform duration-200 group-hover:translate-x-0.5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"
                />
              </svg>
            )}
          </motion.button>
        </div>

        {/* RAG toggle and codes selector */}
        <div className="mt-2 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 flex-wrap">
            <label className="flex items-center gap-2 cursor-pointer group">
              <input
                type="checkbox"
                checked={useRag}
                onChange={(e) => onUseRagChange(e.target.checked)}
                className="w-4 h-4 rounded border-stone-300 text-legal-navy focus:ring-legal-gold/50 cursor-pointer"
              />
              <span className="text-[11px] text-legal-mist font-sans group-hover:text-legal-ink transition-colors">
                Contexte juridique
              </span>
            </label>

            {/* Codes dropdown */}
            {useRag && (
              <div className="relative" ref={dropdownRef}>
                <button
                  type="button"
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className="flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-sans bg-stone-100 hover:bg-stone-200 rounded-lg border border-stone-250 transition-colors"
                >
                  <svg className="w-3.5 h-3.5 text-legal-mist" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                  <span className="text-legal-ink">
                    {selectedCodes.length === 0
                      ? 'Tous les codes'
                      : `${selectedCodes.length} code${selectedCodes.length > 1 ? 's' : ''}`}
                  </span>
                  <svg className={`w-3 h-3 text-legal-mist transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                <AnimatePresence>
                  {isDropdownOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      transition={{ duration: 0.15 }}
                      className="absolute bottom-full left-0 mb-2 w-72 max-h-64 overflow-y-auto bg-white rounded-xl border border-stone-200 shadow-legal-lg z-50"
                    >
                      <div className="p-2 border-b border-stone-100 flex justify-between items-center">
                        <span className="text-[11px] font-medium text-legal-ink">Filtrer par code</span>
                        {selectedCodes.length > 0 && (
                          <button
                            type="button"
                            onClick={() => onSelectedCodesChange([])}
                            className="text-[10px] text-legal-mist hover:text-legal-ink transition-colors"
                          >
                            Effacer
                          </button>
                        )}
                      </div>
                      <div className="p-1">
                        {LAW_CODES.map((code) => (
                          <label
                            key={code.id}
                            className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-stone-50 cursor-pointer transition-colors"
                          >
                            <input
                              type="checkbox"
                              checked={selectedCodes.includes(code.id)}
                              onChange={() => toggleCode(code.id)}
                              className="w-3.5 h-3.5 rounded border-stone-300 text-legal-navy focus:ring-legal-gold/50 cursor-pointer"
                            />
                            <span className="text-[11px] text-legal-ink font-sans truncate">
                              {code.name}
                            </span>
                          </label>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </div>

          <p className="text-[11px] text-legal-mist font-sans flex-shrink-0">
            <span className="hidden sm:inline">
              <kbd className="px-1.5 py-0.5 bg-stone-150 rounded text-[10px] font-medium">Shift + Entree</kbd> saut de ligne
            </span>
            <span className="sm:hidden">Appuyez pour envoyer</span>
          </p>
        </div>
      </form>
    </motion.div>
  )
}

function LoadingSpinner() {
  return (
    <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}
