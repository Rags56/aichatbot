import axios from 'axios'

// API Configuration
const API_URL = process.env.NEXT_PUBLIC_API_URL || process.env.REACT_APP_API_URL || 'http://localhost:5000'

// AI API (for compatibility with AIAssistant component)
export const aiApi = {
  async chat(params: { message: string; conversation_id?: string | null; user_id?: number }) {
    const token = localStorage.getItem('token')
    const response = await axios.post(
      `${API_URL}/api/ai/chat`,
      { 
        message: params.message, 
        conversationId: params.conversation_id || undefined,
        userId: params.user_id || 1
      },
      {
        headers: {
          Authorization: token ? `Bearer ${token}` : undefined,
          'Content-Type': 'application/json'
        }
      }
    )
    return response
  },

  async query(params: { query: string; userId?: string; filters?: any; topK?: number; conversation_id?: string }) {
    const token = localStorage.getItem('token')
    const response = await axios.post(
      `${API_URL}/api/ai/query`,
      {
        query: params.query,
        userId: params.userId || '1',
        filters: params.filters || {},
        topK: params.topK || 6,
        conversation_id: params.conversation_id
      },
      {
        headers: {
          Authorization: token ? `Bearer ${token}` : undefined,
          'Content-Type': 'application/json'
        }
      }
    )
    return response
  }
}

// Chat API (alternative interface)
export const chatApi = {
  async chat(message: string, conversationId?: string) {
    const token = localStorage.getItem('token')
    const response = await axios.post(
      `${API_URL}/api/ai/chat`,
      { message, conversationId },
      {
        headers: {
          Authorization: token ? `Bearer ${token}` : undefined,
          'Content-Type': 'application/json'
        }
      }
    )
    return response.data
  }
}
