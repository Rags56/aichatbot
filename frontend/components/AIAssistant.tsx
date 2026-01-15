'use client'

import { useState, useEffect, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/hooks/use-toast'
import { aiApi } from '@/lib/api'
import { Send, Bot, User, Copy, Check, FileText, Lightbulb, Download, Clock, TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface Source {
  document_id?: string
  title?: string
  chunk_id?: string
  source?: string
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  created_at?: string
  sources?: Source[]
  confidence?: number
  confidence_reasoning?: string
  suggestions?: string[]
  meta?: any
}

export function AIAssistant() {
  const { toast } = useToast()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [copiedMessageId, setCopiedMessageId] = useState<number | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = {
      role: 'user',
      content: input,
      created_at: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await aiApi.chat({
        message: input,
        conversation_id: conversationId,
        user_id: 1, // Default user ID
      })

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.data.message || response.data.answer || '',
        created_at: new Date().toISOString(),
        sources: response.data.sources || [],
        confidence: response.data.meta?.confidence,
        confidence_reasoning: response.data.meta?.confidence_reasoning,
        suggestions: response.data.meta?.suggestions || [],
        meta: response.data.meta || {}
      }

      setMessages((prev) => [...prev, assistantMessage])
      if (response.data.conversation_id) {
        setConversationId(response.data.conversation_id)
      }
    } catch (error: any) {
      console.error('Error sending message:', error)
      const errorMessage: Message = {
        role: 'assistant',
        content: error.response?.data?.message || error.response?.data?.error || 'Sorry, I encountered an error. Please try again.',
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errorMessage])
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.response?.data?.message || 'Failed to send message',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async (messageIndex: number) => {
    const message = messages[messageIndex]
    if (message) {
      await navigator.clipboard.writeText(message.content)
      setCopiedMessageId(messageIndex)
      toast({
        title: 'Copied',
        description: 'Message copied to clipboard',
      })
      setTimeout(() => setCopiedMessageId(null), 2000)
    }
  }

  const handleExport = () => {
    const conversationText = messages.map((msg, idx) => {
      const timestamp = msg.created_at ? new Date(msg.created_at).toLocaleString() : 'Unknown time'
      return `${msg.role === 'user' ? 'User' : 'Assistant'} (${timestamp}):\n${msg.content}\n${msg.sources && msg.sources.length > 0 ? `\nSources: ${msg.sources.map(s => s.title).join(', ')}\n` : ''}${msg.confidence !== undefined ? `\nConfidence: ${(msg.confidence * 100).toFixed(0)}%\n` : ''}\n---\n`
    }).join('\n')

    const blob = new Blob([conversationText], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `conversation-${conversationId || 'new'}-${new Date().toISOString().split('T')[0]}.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    
    toast({
      title: 'Exported',
      description: 'Conversation exported successfully',
    })
  }

  const getConfidenceColor = (confidence?: number) => {
    if (!confidence) return 'bg-gray-100 text-gray-700'
    if (confidence >= 0.8) return 'bg-green-100 text-green-700'
    if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-700'
    return 'bg-orange-100 text-orange-700'
  }

  const getConfidenceIcon = (confidence?: number) => {
    if (!confidence) return <Minus className="w-3 h-3" />
    if (confidence >= 0.8) return <TrendingUp className="w-3 h-3" />
    if (confidence >= 0.6) return <Minus className="w-3 h-3" />
    return <TrendingDown className="w-3 h-3" />
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="h-full flex flex-col">
      <Card className="flex-1 flex flex-col card-hover border-0 shadow-lg">
        <CardHeader className="pb-4 border-b border-gray-200/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center shadow-md">
                <Bot className="h-5 w-5 text-white" />
              </div>
              <div>
                <CardTitle className="text-2xl font-bold text-gray-900">AI Assistant</CardTitle>
                <CardDescription className="mt-1.5 text-gray-600">Ask questions about company documents and operations</CardDescription>
              </div>
            </div>
            {messages.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleExport}
                className="flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Export
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col pt-6">
          <div className="flex-1 overflow-y-auto mb-4 space-y-4 p-6 bg-gradient-to-br from-gray-50 to-blue-50/30 rounded-xl border border-gray-200/50">
            {messages.length === 0 ? (
              <div className="text-center text-gray-500 py-12">
                <div className="w-16 h-16 rounded-2xl gradient-primary flex items-center justify-center mx-auto mb-4 shadow-lg">
                  <Bot className="h-8 w-8 text-white" />
                </div>
                <p className="text-gray-600 font-medium">Start a conversation by asking a question</p>
                <p className="text-sm text-gray-400 mt-2">Try asking about documents, employees, or system status</p>
              </div>
            ) : (
              messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex gap-3 ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {message.role === 'assistant' && (
                    <div className="flex-shrink-0 w-10 h-10 rounded-xl gradient-primary flex items-center justify-center shadow-md">
                      <Bot className="h-5 w-5 text-white" />
                    </div>
                  )}
                  <div
                    className={`max-w-[75%] rounded-xl p-4 shadow-sm relative group ${
                      message.role === 'user'
                        ? 'gradient-primary text-white'
                        : 'bg-white border border-gray-200'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <p className={`text-sm whitespace-pre-wrap leading-relaxed flex-1 ${message.role === 'user' ? 'text-white' : 'text-gray-900'}`}>
                        {message.content}
                      </p>
                      <Button
                        variant="ghost"
                        size="sm"
                        className={`h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity ${message.role === 'user' ? 'text-white hover:bg-white/20' : 'text-gray-500 hover:bg-gray-100'}`}
                        onClick={() => handleCopy(index)}
                      >
                        {copiedMessageId === index ? (
                          <Check className="w-3 h-3" />
                        ) : (
                          <Copy className="w-3 h-3" />
                        )}
                      </Button>
                    </div>
                    
                    {/* Timestamp */}
                    {message.created_at && (
                      <div className={`text-xs mt-2 ${message.role === 'user' ? 'text-white/70' : 'text-gray-500'}`}>
                        <Clock className="w-3 h-3 inline mr-1" />
                        {new Date(message.created_at).toLocaleTimeString()}
                      </div>
                    )}
                    
                    {/* Confidence Score */}
                    {message.role === 'assistant' && message.confidence !== undefined && (
                      <div className="mt-2 flex items-center gap-2">
                        <Badge className={`${getConfidenceColor(message.confidence)} text-xs flex items-center gap-1`}>
                          {getConfidenceIcon(message.confidence)}
                          Confidence: {(message.confidence * 100).toFixed(0)}%
                        </Badge>
                        {message.confidence_reasoning && (
                          <span className="text-xs text-gray-500" title={message.confidence_reasoning}>
                            {message.confidence_reasoning}
                          </span>
                        )}
                      </div>
                    )}
                    
                    {/* Sources */}
                    {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        <div className="flex items-center gap-2 mb-2">
                          <FileText className="w-4 h-4 text-gray-500" />
                          <span className="text-xs font-semibold text-gray-700">Sources:</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {message.sources.map((source, idx) => (
                            <Badge key={idx} variant="outline" className="text-xs">
                              {source.title || 'Unknown Document'}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {/* Suggestions */}
                    {message.role === 'assistant' && message.suggestions && message.suggestions.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        <div className="flex items-center gap-2 mb-2">
                          <Lightbulb className="w-4 h-4 text-yellow-500" />
                          <span className="text-xs font-semibold text-gray-700">Suggested questions:</span>
                        </div>
                        <div className="flex flex-col gap-1">
                          {message.suggestions.map((suggestion, idx) => (
                            <button
                              key={idx}
                              onClick={() => {
                                setInput(suggestion)
                                // Auto-send after setting input
                                setTimeout(() => {
                                  handleSend()
                                }, 50)
                              }}
                              className="text-xs text-left text-blue-600 hover:text-blue-800 hover:underline p-2 rounded hover:bg-blue-50 transition-colors"
                            >
                              {suggestion}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  {message.role === 'user' && (
                    <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-gray-200 flex items-center justify-center border border-gray-300">
                      <User className="h-5 w-5 text-gray-600" />
                    </div>
                  )}
                </div>
              ))
            )}
            {loading && (
              <div className="flex gap-3 justify-start">
                <div className="flex-shrink-0 w-10 h-10 rounded-xl gradient-primary flex items-center justify-center shadow-md">
                  <Bot className="h-5 w-5 text-white" />
                </div>
                <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                    <p className="text-sm text-gray-500 ml-2">Thinking...</p>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          <div className="flex gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              disabled={loading}
              className="border-gray-300 focus:border-blue-500 focus:ring-blue-500"
            />
            <Button 
              onClick={handleSend} 
              disabled={loading || !input.trim()}
              className="gradient-primary text-white shadow-md hover:shadow-lg disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
