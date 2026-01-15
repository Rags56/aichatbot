'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Cpu, Zap, Activity, RefreshCw, Server, AlertCircle, CheckCircle2, Monitor } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface DebugInfo {
  model: string
  model_size?: number
  embedding_model: string
  gpu: string
  gpu_name: string
  tokens_per_second: number
  last_tokens_generated?: number
  ollama_url?: string
  available_models?: string[]
  error?: string
  gpu_utilization?: string
  gpu_memory?: string
}

interface PipelineTiming {
  user_context_ms?: number
  memory_retrieval_ms?: number
  query_processing_ms?: number
  embedding_generation_ms?: number
  search_ms?: number
  keyword_search_ms?: number
  vector_search_ms?: number
  merge_ms?: number
  prompt_building_ms?: number
  llm_inference_ms?: number
  response_processing_ms?: number
  untracked_overhead_ms?: number
  total_ms?: number
}

interface BackendStatus {
  online: boolean
  status?: string
  service?: string
  error?: string
  lastCheck?: Date
}

export function DebugPanel() {
  const [debugInfo, setDebugInfo] = useState<DebugInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())
  const [backendStatus, setBackendStatus] = useState<BackendStatus>({ online: false })
  const [checkingBackend, setCheckingBackend] = useState(false)
  const [lastPipelineTiming, setLastPipelineTiming] = useState<PipelineTiming | null>(null)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'

  const checkBackendHealth = async (showRetry = false) => {
    if (showRetry) {
      setCheckingBackend(true)
    }
    try {
      const response = await fetch(`${API_URL}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000), // 5 second timeout
      })
      if (response.ok) {
        const data = await response.json()
        setBackendStatus({
          online: true,
          status: data.status,
          service: data.service,
          lastCheck: new Date(),
        })
      } else {
        setBackendStatus({
          online: false,
          status: 'error',
          error: `HTTP ${response.status}`,
          lastCheck: new Date(),
        })
      }
    } catch (error: any) {
      setBackendStatus({
        online: false,
        status: 'offline',
        error: error.name === 'AbortError' ? 'Connection timeout' : 'Connection failed',
        lastCheck: new Date(),
      })
    } finally {
      if (showRetry) {
        setCheckingBackend(false)
      }
    }
  }

  const fetchDebugInfo = async () => {
    try {
      const response = await fetch(`${API_URL}/api/ai/debug`)
      if (response.ok) {
        const data = await response.json()
        setDebugInfo(data)
        setLastUpdate(new Date())
      }
    } catch (error) {
      console.error('Error fetching debug info:', error)
    } finally {
      setLoading(false)
    }
  }

  // Listen for pipeline timing from chat responses
  useEffect(() => {
    const handleStorageChange = () => {
      const timing = sessionStorage.getItem('lastPipelineTiming')
      if (timing) {
        try {
          const parsed = JSON.parse(timing)
          setLastPipelineTiming(parsed)
        } catch (e) {
          // Ignore parse errors
        }
      }
    }
    
    // Check immediately
    handleStorageChange()
    
    // Poll for changes (since storage events don't fire for same-origin)
    const interval = setInterval(handleStorageChange, 500)
    
    return () => {
      clearInterval(interval)
    }
  }, [])

  useEffect(() => {
    // Check backend health first
    checkBackendHealth()
    fetchDebugInfo()
    
    // Refresh every 5 seconds
    const interval = setInterval(() => {
      checkBackendHealth()
      fetchDebugInfo()
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  const formatModelSize = (size: number) => {
    if (!size) return 'Unknown'
    const gb = size / (1024 * 1024 * 1024)
    if (gb >= 1) return `${gb.toFixed(2)} GB`
    const mb = size / (1024 * 1024)
    return `${mb.toFixed(2)} MB`
  }

  if (loading && !debugInfo) {
    return (
      <Card className="mb-4 border-blue-200 bg-blue-50/50">
        <CardContent className="p-3">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Activity className="w-4 h-4 animate-spin" />
            <span>Loading debug info...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      {/* Backend Status Card */}
      <Card className={`mb-3 ${backendStatus.online ? 'border-green-300 bg-green-50/80' : 'border-red-300 bg-red-50/80'} shadow-sm`}>
        <CardContent className="p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {backendStatus.online ? (
                <Badge variant="outline" className="bg-green-100 border-green-400 text-green-800">
                  <CheckCircle2 className="w-3 h-3 mr-1" />
                  <span className="font-mono text-xs">Backend Online</span>
                </Badge>
              ) : (
                <Badge variant="outline" className="bg-red-100 border-red-400 text-red-800">
                  <AlertCircle className="w-3 h-3 mr-1" />
                  <span className="font-mono text-xs">Backend Offline</span>
                </Badge>
              )}
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-gray-600" />
                <span className="text-xs font-mono text-gray-700">{API_URL}</span>
              </div>
              {backendStatus.service && (
                <Badge variant="outline" className="bg-white/80 text-xs">
                  {backendStatus.service}
                </Badge>
              )}
              {backendStatus.error && (
                <span className="text-xs text-red-600 font-mono">{backendStatus.error}</span>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => checkBackendHealth(true)}
              disabled={checkingBackend}
              className="h-7 px-2 text-xs"
            >
              <RefreshCw className={`w-3 h-3 mr-1 ${checkingBackend ? 'animate-spin' : ''}`} />
              {checkingBackend ? 'Checking...' : 'Retry'}
            </Button>
          </div>
          {backendStatus.lastCheck && (
            <div className="mt-1 text-xs text-gray-500">
              Last check: {backendStatus.lastCheck.toLocaleTimeString()}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Debug Info Card */}
      <Card className="mb-4 border-blue-200 bg-gradient-to-r from-blue-50/80 to-indigo-50/80 shadow-sm">
        <CardContent className="p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4 flex-wrap">
              {/* Model Info */}
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="bg-white/80">
                <Activity className="w-3 h-3 mr-1" />
                <span className="font-mono text-xs">
                  Model: {debugInfo?.model || 'Unknown'}
                </span>
              </Badge>
            </div>

            {/* GPU Info */}
            <div className="flex items-center gap-2">
              {debugInfo?.gpu === 'GPU' ? (
                <Badge variant="outline" className="bg-green-50 border-green-300 text-green-700">
                  <Monitor className="w-3 h-3 mr-1" />
                  <span className="font-mono text-xs">
                    {debugInfo.gpu_name || 'GPU'}
                  </span>
                </Badge>
              ) : (
                <Badge variant="outline" className="bg-gray-50 border-gray-300 text-gray-700">
                  <Cpu className="w-3 h-3 mr-1" />
                  <span className="font-mono text-xs">CPU</span>
                </Badge>
              )}
            </div>

            {/* Tokens per Second */}
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="bg-purple-50 border-purple-300 text-purple-700">
                <Zap className="w-3 h-3 mr-1" />
                <span className="font-mono text-xs">
                  {debugInfo?.tokens_per_second?.toFixed(2) || '0.00'} tokens/s
                </span>
              </Badge>
            </div>

            {/* Last tokens generated */}
            {debugInfo?.last_tokens_generated && debugInfo.last_tokens_generated > 0 && (
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="bg-indigo-50 border-indigo-300 text-indigo-700">
                  <span className="font-mono text-xs">
                    {debugInfo.last_tokens_generated} tokens
                  </span>
                </Badge>
              </div>
            )}

            {/* Embedding Model */}
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="bg-amber-50 border-amber-300 text-amber-700">
                <span className="font-mono text-xs">
                  Embed: {debugInfo?.embedding_model?.split(':')[0] || 'Unknown'}
                </span>
              </Badge>
            </div>
          </div>

          {/* Refresh Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchDebugInfo}
            className="h-7 px-2 text-xs"
          >
            <RefreshCw className="w-3 h-3 mr-1" />
            Refresh
          </Button>
        </div>

        {/* Error Display */}
        {debugInfo?.error && (
          <div className="mt-2 text-xs text-red-600 font-mono">
            Error: {debugInfo.error}
          </div>
        )}

        {/* Last Update Time */}
        <div className="mt-1 text-xs text-gray-500">
          Last updated: {lastUpdate.toLocaleTimeString()}
        </div>
      </CardContent>
    </Card>

    {/* Pipeline Timing Breakdown - Always Visible */}
    <Card className="mb-4 border-purple-200 bg-purple-50/80 shadow-sm">
      <CardContent className="p-3">
        <div className="mb-2">
          <h3 className="text-sm font-semibold text-gray-900 mb-2">
            RAG Pipeline Timing Breakdown
            {!lastPipelineTiming && (
              <span className="ml-2 text-xs text-gray-500 font-normal">(Send a message to see timing)</span>
            )}
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
            <div className="flex items-center justify-between p-2 bg-white/80 rounded">
              <span className="text-gray-600">User Context:</span>
              <span className="font-mono font-semibold">{lastPipelineTiming?.user_context_ms?.toFixed(1) || '—'}ms</span>
            </div>
            <div className="flex items-center justify-between p-2 bg-white/80 rounded">
              <span className="text-gray-600">Memory:</span>
              <span className="font-mono font-semibold">{lastPipelineTiming?.memory_retrieval_ms?.toFixed(1) || '—'}ms</span>
            </div>
            <div className="flex items-center justify-between p-2 bg-white/80 rounded">
              <span className="text-gray-600">Query Processing:</span>
              <span className="font-mono font-semibold">{lastPipelineTiming?.query_processing_ms?.toFixed(1) || '—'}ms</span>
            </div>
            <div className="flex items-center justify-between p-2 bg-green-100/80 rounded border border-green-300">
              <span className="text-gray-700">Embedding (GPU):</span>
              <span className="font-mono font-semibold text-green-700">{lastPipelineTiming?.embedding_generation_ms?.toFixed(1) || '—'}ms</span>
            </div>
            <div className="flex items-center justify-between p-2 bg-white/80 rounded">
              <span className="text-gray-600">Search Total:</span>
              <span className="font-mono font-semibold">{lastPipelineTiming?.search_ms?.toFixed(1) || '—'}ms</span>
            </div>
            {lastPipelineTiming?.keyword_search_ms !== undefined && (
              <div className="flex items-center justify-between p-2 bg-blue-50/80 rounded">
                <span className="text-gray-600 text-[10px]">Keyword:</span>
                <span className="font-mono text-[10px]">{lastPipelineTiming.keyword_search_ms.toFixed(1)}ms</span>
              </div>
            )}
            {lastPipelineTiming?.vector_search_ms !== undefined && (
              <div className="flex items-center justify-between p-2 bg-blue-50/80 rounded">
                <span className="text-gray-600 text-[10px]">Vector:</span>
                <span className="font-mono text-[10px]">{lastPipelineTiming.vector_search_ms.toFixed(1)}ms</span>
              </div>
            )}
            {lastPipelineTiming?.merge_ms !== undefined && (
              <div className="flex items-center justify-between p-2 bg-blue-50/80 rounded">
                <span className="text-gray-600 text-[10px]">Merge:</span>
                <span className="font-mono text-[10px]">{lastPipelineTiming.merge_ms.toFixed(1)}ms</span>
              </div>
            )}
            <div className="flex items-center justify-between p-2 bg-white/80 rounded">
              <span className="text-gray-600">Prompt Building:</span>
              <span className="font-mono font-semibold">{lastPipelineTiming?.prompt_building_ms?.toFixed(1) || '—'}ms</span>
            </div>
            <div className="flex items-center justify-between p-2 bg-green-100/80 rounded border border-green-300">
              <span className="text-gray-700">LLM Inference (GPU):</span>
              <span className="font-mono font-semibold text-green-700">{lastPipelineTiming?.llm_inference_ms?.toFixed(1) || '—'}ms</span>
            </div>
            <div className="flex items-center justify-between p-2 bg-white/80 rounded">
              <span className="text-gray-600">Response Processing:</span>
              <span className="font-mono font-semibold">{lastPipelineTiming?.response_processing_ms?.toFixed(1) || '—'}ms</span>
            </div>
            {lastPipelineTiming?.untracked_overhead_ms !== undefined && lastPipelineTiming.untracked_overhead_ms > 0 && (
              <div className="flex items-center justify-between p-2 bg-yellow-50/80 rounded border border-yellow-300">
                <span className="text-gray-600">Untracked Overhead:</span>
                <span className="font-mono font-semibold text-yellow-700">{lastPipelineTiming.untracked_overhead_ms.toFixed(1)}ms</span>
              </div>
            )}
            <div className="flex items-center justify-between p-2 bg-purple-100/80 rounded border-2 border-purple-400 col-span-2 md:col-span-3">
              <span className="text-gray-900 font-bold">TOTAL:</span>
              <span className="font-mono font-bold text-purple-900">{lastPipelineTiming?.total_ms?.toFixed(1) || '—'}ms</span>
            </div>
          </div>
        </div>
        {/* Bottleneck indicator */}
        {lastPipelineTiming?.total_ms && lastPipelineTiming.total_ms > 0 && (
          <div className="mt-2 pt-2 border-t border-purple-200">
            <div className="text-xs text-gray-600">
              <strong>Bottleneck:</strong>{' '}
              {(() => {
                const timings = [
                  { name: 'Embedding', time: lastPipelineTiming.embedding_generation_ms || 0 },
                  { name: 'Search', time: lastPipelineTiming.search_ms || 0 },
                  { name: 'LLM Inference', time: lastPipelineTiming.llm_inference_ms || 0 },
                  { name: 'Query Processing', time: lastPipelineTiming.query_processing_ms || 0 },
                ]
                timings.sort((a, b) => b.time - a.time)
                const bottleneck = timings[0]
                const percentage = ((bottleneck.time / (lastPipelineTiming.total_ms || 1)) * 100).toFixed(1)
                return `${bottleneck.name} (${bottleneck.time.toFixed(1)}ms, ${percentage}%)`
              })()}
            </div>
          </div>
        )}
        {!lastPipelineTiming && (
          <div className="mt-2 pt-2 border-t border-purple-200">
            <div className="text-xs text-gray-500 italic">
              Send a message to see detailed timing breakdown
            </div>
          </div>
        )}
      </CardContent>
    </Card>
    </>
  )
}
