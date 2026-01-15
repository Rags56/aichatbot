'use client'

import { AIAssistant } from '@/components/AIAssistant'

export default function AIAssistantPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">AI Assistant</h1>
        </div>
        <AIAssistant />
      </div>
    </div>
  )
}
