"""
AI Knowledge Base Service - RAG Implementation
Implements Retrieval-Augmented Generation with zero-trust integration
"""
import os
import json
import time
import uuid
import base64
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import requests
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from meilisearch import Client
import tiktoken
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import hashlib
from ai_enterprise import AIEnterpriseFeatures

class AIService:
    def __init__(self):
        # Local LLM configuration (Ollama)
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.llm_model = os.getenv('LLM_MODEL', 'llama3.1:8b')
        self.embedding_model = os.getenv('EMBEDDING_MODEL', 'llama3.1:8b')  # Same model or use nomic-embed-text
        
        # Test Ollama connection
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                print(f"✓ Connected to Ollama at {self.ollama_url}")
                # Check if model is available
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                if self.llm_model not in model_names:
                    print(f"⚠ Warning: Model '{self.llm_model}' not found. Available models: {model_names}")
                    print(f"  Run: ollama pull {self.llm_model}")
            else:
                print(f"⚠ Warning: Ollama not responding at {self.ollama_url}")
        except Exception as e:
            print(f"⚠ Warning: Could not connect to Ollama at {self.ollama_url}: {e}")
            print("  Make sure Ollama is running: ollama serve")
        
        # Meilisearch client
        self.meilisearch_client = None
        if os.getenv('MEILISEARCH_URL'):
            self.meilisearch_client = Client(
                os.getenv('MEILISEARCH_URL', 'http://localhost:7700'),
                os.getenv('MEILISEARCH_KEY', 'masterKey123')
            )
            self._initialize_meilisearch_index()
        
        # Database connection
        self.db_url = os.getenv('DATABASE_URL', 'postgresql://zerotrust:zerotrust123@postgres:5432/zerotrust_db')
        
        # Configuration
        self.max_chunk_tokens = int(os.getenv('MAX_CHUNK_TOKENS', '800'))
        self.chunk_overlap = int(os.getenv('CHUNK_OVERLAP', '50'))
        self.top_k = int(os.getenv('TOP_K', '6'))
        self.ai_backend = os.getenv('AI_BACKEND', 'ollama')
        
        # Encryption key for decrypting files (must match backend-core)
        self.encryption_master_key = os.getenv('ENCRYPTION_MASTER_KEY', '')
        if not self.encryption_master_key:
            # Try to get from backend-core or use default for PoC
            print("Warning: ENCRYPTION_MASTER_KEY not set. File decryption may fail.")
        
        # Tokenizer for chunking
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except:
            self.tokenizer = None
        
        # Enterprise features
        self.enterprise = AIEnterpriseFeatures(
            self.db_url,
            os.getenv('BACKEND_CORE_URL', 'http://backend-core:3001')
        )
    
    def _initialize_meilisearch_index(self):
        """Initialize Meilisearch index for kb_chunks"""
        try:
            index_name = 'kb_chunks'
            try:
                # Try to get existing index
                index = self.meilisearch_client.get_index(index_name)
            except:
                # Create index if it doesn't exist
                index = self.meilisearch_client.create_index(index_name, {'primaryKey': 'id'})
            
            # Configure index settings
            index.update_searchable_attributes(['text', 'title'])
            index.update_displayed_attributes(['id', 'title', 'text', 'source', 'document_id', 'tags', 'department'])
            index.update_filterable_attributes(['source', 'department', 'tags', 'created_at'])
            
            print(f"Meilisearch index '{index_name}' initialized")
        except Exception as e:
            print(f"Error initializing Meilisearch index: {e}")
            # Try to create index with different method
            try:
                self.meilisearch_client.create_index(index_name, {'primaryKey': 'id'})
                print(f"Created Meilisearch index '{index_name}'")
            except Exception as e2:
                print(f"Failed to create index: {e2}")
    
    def get_db_connection(self):
        """Get PostgreSQL connection"""
        return psycopg2.connect(self.db_url)
    
    def _get_user_context(self, user_id: str) -> Dict:
        """Get user context including permissions and roles"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get user with roles and permissions
            cur.execute("""
                SELECT u.*, 
                       ARRAY_AGG(DISTINCT r.role_id) as roles,
                       ARRAY_AGG(DISTINCT p.permission_id) as permissions
                FROM iacm_users u
                LEFT JOIN iacm_user_roles ur ON u.id = ur.user_id
                LEFT JOIN iacm_roles r ON ur.role_id = r.id
                LEFT JOIN iacm_role_permissions rp ON r.id = rp.role_id
                LEFT JOIN iacm_permissions p ON rp.permission_id = p.id
                WHERE u.user_id = %s OR u.id::text = %s OR u.email = %s
                GROUP BY u.id
                LIMIT 1
            """, (user_id, user_id, user_id))
            
            user = cur.fetchone()
            cur.close()
            conn.close()
            
            if user:
                return {
                    'user_id': str(user['id']),
                    'username': user.get('username'),
                    'email': user.get('email'),
                    'roles': user.get('roles', []) or [],
                    'permissions': user.get('permissions', []) or []
                }
            else:
                # Default permissions for PoC
                return {
                    'user_id': user_id,
                    'username': 'user',
                    'email': f'{user_id}@zerotrust.local',
                    'roles': ['ROLE_USER'],
                    'permissions': ['PERM_DOCUMENTS_READ']
                }
        except Exception as e:
            print(f"Error getting user context: {e}")
            return {
                'user_id': user_id,
                'username': 'user',
                'permissions': []
            }
    
    def _derive_key(self, file_id: str) -> bytes:
        """Derive encryption key from master key and file ID (matches backend-core logic)"""
        if not self.encryption_master_key:
            # For PoC: generate a default key if not set
            # In production, this must match backend-core's ENCRYPTION_MASTER_KEY
            master_key_bytes = hashlib.sha256(b'default-master-key-for-poc').digest()
        else:
            # Convert hex string to bytes (Node.js uses hex encoding)
            try:
                # Try hex decode first (Node.js format)
                if len(self.encryption_master_key) == 64:  # 32 bytes = 64 hex chars
                    master_key_bytes = bytes.fromhex(self.encryption_master_key)
                else:
                    # If not hex or wrong length, use as-is and truncate/pad to 32 bytes
                    master_key_bytes = self.encryption_master_key.encode('utf-8')[:32]
                    if len(master_key_bytes) < 32:
                        # Pad with zeros if too short
                        master_key_bytes = master_key_bytes + b'\x00' * (32 - len(master_key_bytes))
            except ValueError:
                # Not valid hex, use as string and pad/truncate
                master_key_bytes = self.encryption_master_key.encode('utf-8')[:32]
                if len(master_key_bytes) < 32:
                    master_key_bytes = master_key_bytes + b'\x00' * (32 - len(master_key_bytes))
        
        # PBKDF2 key derivation (matches Node.js crypto.pbkdf2Sync)
        # Node.js: crypto.pbkdf2Sync(masterKey, fileId, 100000, 32, 'sha256')
        # Python: PBKDF2HMAC with salt=fileId, iterations=100000, length=32
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=file_id.encode('utf-8'),  # fileId is the salt in Node.js
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(master_key_bytes)
        return key
    
    def _decrypt_file(self, encrypted_content: bytes, iv: bytes, tag: bytes, file_id: str) -> bytes:
        """Decrypt file content using AES-256-GCM (matches backend-core logic)"""
        try:
            key = self._derive_key(file_id)
            aesgcm = AESGCM(key)
            # AESGCM.decrypt expects: nonce (iv), data (encrypted + tag), associated_data (None)
            decrypted = aesgcm.decrypt(iv, encrypted_content + tag, None)
            return decrypted
        except Exception as e:
            print(f"Decryption error: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to decrypt file: {str(e)}")
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding using local Ollama"""
        try:
            # Ollama embeddings API
            response = requests.post(
                f"{self.ollama_url}/api/embeddings",
                json={
                    "model": self.embedding_model,
                    "prompt": text
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('embedding')
            else:
                print(f"Error generating embedding: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error generating embedding: {e}")
            # Fallback: return None, will use keyword search only
            return None
        except Exception as e:
            print(f"Unexpected error generating embedding: {e}")
            return None
    
    def search_chunks(self, query: str, query_embedding: Optional[List[float]], 
                     filters: Optional[Dict] = None, top_k: int = 6, 
                     query_id: str = None, debug: bool = False) -> List[Dict]:
        """Hybrid search: vector + keyword"""
        if not self.meilisearch_client:
            return []
        
        try:
            index = self.meilisearch_client.index('kb_chunks')
            results = []
            
            # Keyword search
            search_params = {
                'limit': top_k * 2  # Get more for merging
            }
            if filters and self._build_filter(filters):
                search_params['filter'] = self._build_filter(filters)
            
            keyword_response = index.search(query, search_params)
            
            # Extract hits from response (Meilisearch returns dict with 'hits' key)
            keyword_hits = keyword_response.get('hits', []) if isinstance(keyword_response, dict) else []
            
            # Vector search (if embedding available) - Meilisearch v1.5+ supports vector search
            vector_hits = []
            if query_embedding:
                try:
                    # Meilisearch vector search (if supported)
                    vector_response = index.search('', {
                        'vector': query_embedding,
                        'limit': top_k * 2,
                        'filter': self._build_filter(filters) if filters and self._build_filter(filters) else None
                    })
                    vector_hits = vector_response.get('hits', []) if isinstance(vector_response, dict) else []
                except Exception as e:
                    # Fallback if vector search not supported
                    print(f"Vector search not available: {e}")
                    pass
            
            # Merge results (hybrid: 60% vector, 40% keyword)
            merged = self._merge_search_results(keyword_hits, vector_hits, top_k)
        
            # Log retrieval debug info if enabled
            if debug and query_id:
                for rank, chunk in enumerate(merged[:top_k], 1):
                    similarity = chunk.get('_rankingScore', 0.0) or 0.0
                    keyword_score = 1.0 - (rank / len(merged)) if merged else 0.0
                    combined = (similarity * 0.6) + (keyword_score * 0.4)
                    
                    # Extract matched terms (simple keyword matching)
                    matched_terms = []
                    query_words = query.lower().split()
                    chunk_text = chunk.get('text', '').lower()
                    for word in query_words:
                        if len(word) > 3 and word in chunk_text:
                            matched_terms.append(word)
                    
                    self.enterprise.log_retrieval_debug(
                        query_id, chunk.get('id'),
                        'hybrid' if query_embedding else 'keyword',
                        similarity, keyword_score, combined, rank,
                        matched_terms, {'chunk_text_preview': chunk.get('text', '')[:100]}
                    )
            
            return merged
        except Exception as e:
            print(f"Error searching chunks: {e}")
            return []
    
    def _build_filter(self, filters: Dict) -> str:
        """Build Meilisearch filter string"""
        if not filters:
            return None
        
        filter_parts = []
        if 'department' in filters:
            filter_parts.append(f"department = '{filters['department']}'")
        if 'source' in filters:
            filter_parts.append(f"source = '{filters['source']}'")
        if 'tags' in filters:
            if isinstance(filters['tags'], list):
                tag_filter = ' OR '.join([f"tags = '{tag}'" for tag in filters['tags']])
                filter_parts.append(f"({tag_filter})")
            else:
                filter_parts.append(f"tags = '{filters['tags']}'")
        
        return ' AND '.join(filter_parts) if filter_parts else None
    
    def _merge_search_results(self, keyword_hits: List, vector_hits: List, top_k: int) -> List[Dict]:
        """Merge keyword and vector search results with weighted scoring"""
        # Create a map of chunk_id -> best score
        chunk_scores = {}
        
        # Process keyword results (40% weight)
        for i, hit in enumerate(keyword_hits[:top_k * 2]):
            chunk_id = hit.get('id')
            keyword_score = (len(keyword_hits) - i) / len(keyword_hits) if keyword_hits else 0
            if chunk_id not in chunk_scores:
                chunk_scores[chunk_id] = {'chunk': hit, 'score': 0}
            chunk_scores[chunk_id]['score'] += keyword_score * 0.4
        
        # Process vector results (60% weight)
        for i, hit in enumerate(vector_hits[:top_k * 2]):
            chunk_id = hit.get('id')
            vector_score = hit.get('_rankingScore', (len(vector_hits) - i) / len(vector_hits) if vector_hits else 0)
            if chunk_id not in chunk_scores:
                chunk_scores[chunk_id] = {'chunk': hit, 'score': 0}
            chunk_scores[chunk_id]['score'] += vector_score * 0.6
        
        # Sort by combined score and return top_k
        sorted_chunks = sorted(chunk_scores.values(), key=lambda x: x['score'], reverse=True)
        return [item['chunk'] for item in sorted_chunks[:top_k]]
    
    def _detect_topic_from_query(self, query: str, chunks: List[Dict]) -> List[str]:
        """Detect topic/keywords from query and chunks to identify what the user is asking about"""
        import re
        
        topic_keywords = []
        
        # Extract document titles from chunks
        if chunks:
            for chunk in chunks:
                doc_title = chunk.get('title', '')
                if doc_title:
                    # Extract meaningful words from document title
                    words = re.findall(r'\b[a-z]+\b', doc_title.lower())
                    # Filter out common words
                    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'document', 'file', 'doc'}
                    meaningful = [w for w in words if w not in stop_words and len(w) > 3]
                    topic_keywords.extend(meaningful[:3])  # Top 3 words per document
        
        # Extract keywords from query
        query_lower = query.lower()
        # Look for document references
        doc_ref_match = re.search(r'(?:the\s+)?([a-z]+)\s+document', query_lower)
        if doc_ref_match:
            topic_keywords.append(doc_ref_match.group(1))
        
        # Extract capitalized words (might be document names or important terms)
        capitalized = re.findall(r'\b[A-Z][a-z]+\b', query)
        topic_keywords.extend([w.lower() for w in capitalized if len(w) > 3])
        
        # Extract meaningful nouns from query
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'please', 'can', 'you', 'summarize', 'document', 'documents', 'file', 'files', 'tell', 'me', 'about', 'what', 'is', 'are', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'tell', 'me', 'about'}
        words = re.findall(r'\b[a-z]+\b', query_lower)
        meaningful_words = [w for w in words if w not in stop_words and len(w) > 3]
        topic_keywords.extend(meaningful_words[:5])
        
        # Remove duplicates and return
        return list(set(topic_keywords))[:10]  # Limit to 10 unique keywords
    
    def _expand_query(self, query: str, conversation_memories: List[Dict] = None) -> str:
        """Expand query with synonyms, related terms, and context from conversation"""
        import re
        
        # Query expansion patterns
        expansions = {
            r'\bsummarize\b': ['summary', 'overview', 'key points', 'main points'],
            r'\bwhat\b': ['information about', 'details about', 'explain'],
            r'\bhow\b': ['method', 'process', 'procedure', 'steps'],
            r'\bwhy\b': ['reason', 'rationale', 'explanation', 'cause'],
            r'\bwhen\b': ['time', 'date', 'schedule', 'timeline'],
            r'\bwhere\b': ['location', 'place', 'position'],
            r'\bwho\b': ['person', 'individual', 'team', 'department'],
        }
        
        expanded_terms = [query]
        
        # Add expansions based on query patterns
        query_lower = query.lower()
        for pattern, synonyms in expansions.items():
            if re.search(pattern, query_lower):
                expanded_terms.extend(synonyms[:2])  # Add top 2 synonyms
        
        # Add context from recent conversation if available
        if conversation_memories:
            for mem in conversation_memories[:2]:  # Last 2 memories
                mem_content = mem.get('content', '')
                # Extract key terms from memory
                words = re.findall(r'\b[a-z]{4,}\b', mem_content.lower())
                # Add unique meaningful words
                expanded_terms.extend([w for w in words if w not in query_lower][:3])
        
        # Combine and deduplicate
        expanded = ' '.join(expanded_terms)
        return expanded
    
    def _detect_query_intent(self, query: str) -> Dict[str, any]:
        """Detect query intent and type for better handling"""
        import re
        
        query_lower = query.lower()
        
        intent = {
            'type': 'general',  # general, question, command, comparison, list
            'question_type': None,  # what, how, why, when, where, who, yes_no
            'action': None,  # summarize, explain, find, list, compare
            'entities': [],  # document names, topics mentioned
            'complexity': 'simple'  # simple, medium, complex
        }
        
        # Detect question type
        question_patterns = {
            'what': r'\bwhat\b',
            'how': r'\bhow\b',
            'why': r'\bwhy\b',
            'when': r'\bwhen\b',
            'where': r'\bwhere\b',
            'who': r'\bwho\b',
            'yes_no': r'\b(is|are|do|does|did|will|would|can|could|should|has|have)\b'
        }
        
        for q_type, pattern in question_patterns.items():
            if re.search(pattern, query_lower):
                intent['question_type'] = q_type
                intent['type'] = 'question'
                break
        
        # Detect actions
        action_patterns = {
            'summarize': r'\b(summarize|summary|overview)\b',
            'explain': r'\b(explain|describe|tell me about)\b',
            'find': r'\b(find|search|locate|show me)\b',
            'list': r'\b(list|show|display|what are|what do)\b',
            'compare': r'\b(compare|difference|different|same|similar)\b'
        }
        
        for action, pattern in action_patterns.items():
            if re.search(pattern, query_lower):
                intent['action'] = action
                break
        
        # Detect entities (document names, topics)
        # Look for capitalized words or "the X document" patterns
        doc_refs = re.findall(r'(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:document|file|doc)', query)
        intent['entities'].extend([ref.lower() for ref in doc_refs])
        
        # Detect complexity
        word_count = len(query.split())
        if word_count > 20 or 'and' in query_lower or 'or' in query_lower:
            intent['complexity'] = 'complex'
        elif word_count > 10:
            intent['complexity'] = 'medium'
        
        return intent
    
    def _resolve_pronouns_and_references(self, query: str, conversation_memories: List[Dict] = None) -> str:
        """Resolve pronouns and references in follow-up questions"""
        import re
        
        # Common pronouns and references
        pronouns = {
            'it': None,
            'this': None,
            'that': None,
            'they': None,
            'them': None,
            'the document': None,
            'the file': None,
            'the previous': None,
            'the last': None
        }
        
        query_lower = query.lower()
        resolved_query = query
        
        # Check if query contains pronouns/references
        has_reference = any(pronoun in query_lower for pronoun in pronouns.keys())
        
        if has_reference and conversation_memories:
            # Find the most recent memory that mentions a document or topic
            for mem in conversation_memories[:3]:  # Check last 3 memories
                mem_content = mem.get('content', '')
                
                # Extract document names or topics from memory
                # Look for patterns like "document X" or capitalized terms
                doc_patterns = [
                    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:document|file)',
                    r'document[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                    r'\[DOC[^\]]*title:\s*([^\]]+)\]'
                ]
                
                for pattern in doc_patterns:
                    matches = re.findall(pattern, mem_content)
                    if matches:
                        # Replace pronouns with the found document/topic
                        for match in matches[:1]:  # Use first match
                            if 'it' in query_lower or 'this' in query_lower or 'that' in query_lower:
                                resolved_query = re.sub(
                                    r'\b(it|this|that)\b',
                                    match,
                                    query,
                                    flags=re.IGNORECASE
                                )
                            elif 'the document' in query_lower or 'the file' in query_lower:
                                resolved_query = re.sub(
                                    r'\b(the\s+(?:document|file))\b',
                                    match,
                                    query,
                                    flags=re.IGNORECASE
                                )
                        break
                
                if resolved_query != query:
                    break  # Found a resolution
        
        return resolved_query if resolved_query != query else query
    
    def _rerank_chunks(self, chunks: List[Dict], query: str, query_intent: Dict) -> List[Dict]:
        """Re-rank chunks based on relevance to query intent and content"""
        import re
        
        query_lower = query.lower()
        query_words = set(re.findall(r'\b[a-z]{3,}\b', query_lower))
        
        scored_chunks = []
        
        for chunk in chunks:
            score = chunk.get('score', 0.5)  # Start with existing score
            
            chunk_text = chunk.get('text', '').lower()
            chunk_title = chunk.get('title', '').lower()
            
            # Boost score for title matches
            title_words = set(re.findall(r'\b[a-z]{3,}\b', chunk_title))
            title_overlap = len(query_words & title_words)
            if title_overlap > 0:
                score += 0.2 * (title_overlap / max(len(query_words), 1))
            
            # Boost score for content matches
            content_words = set(re.findall(r'\b[a-z]{3,}\b', chunk_text))
            content_overlap = len(query_words & content_words)
            if content_overlap > 0:
                score += 0.15 * (content_overlap / max(len(query_words), 1))
            
            # Boost for action-specific matches
            if query_intent.get('action') == 'summarize':
                # Prefer chunks with overview-like content
                if any(word in chunk_text for word in ['overview', 'summary', 'introduction', 'overall', 'general']):
                    score += 0.1
            elif query_intent.get('action') == 'explain':
                # Prefer chunks with explanatory content
                if any(word in chunk_text for word in ['explain', 'description', 'details', 'information']):
                    score += 0.1
            
            # Boost for question type matches
            if query_intent.get('question_type') == 'how':
                # Prefer chunks with procedural content
                if any(word in chunk_text for word in ['step', 'process', 'procedure', 'method', 'way']):
                    score += 0.1
            
            scored_chunks.append((chunk, score))
        
        # Sort by score and return
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, score in scored_chunks]
    
    def _filter_relevant_memories(self, memories: List[Dict], current_topic_keywords: List[str], current_query: str) -> List[Dict]:
        """Filter memories to only include those relevant to the current topic"""
        if not current_topic_keywords:
            # If we can't detect a topic, return empty to avoid confusion
            return []
        
        relevant_memories = []
        current_query_lower = current_query.lower()
        
        for mem in memories:
            mem_content = mem.get('content', '').lower()
            mem_importance = mem.get('importance_score', 0) or 0
            
            # Check if memory is relevant to current topic
            relevance_score = 0
            
            # Check for keyword matches
            for keyword in current_topic_keywords:
                if keyword in mem_content or keyword in current_query_lower:
                    relevance_score += 1
            
            # Only include memories with some relevance OR very important memories
            if relevance_score > 0 or mem_importance > 70:
                relevant_memories.append((mem, relevance_score + (mem_importance / 100)))
        
        # Sort by relevance score (relevance + importance)
        relevant_memories.sort(key=lambda x: x[1], reverse=True)
        
        # Return only the memory objects (without scores)
        return [mem for mem, score in relevant_memories]
    
    def _is_document_query(self, query: str, chunks: List[Dict]) -> bool:
        """Determine if the query is actually about documents or a general question"""
        import re
        
        query_lower = query.lower()
        
        # Explicit document-related keywords
        document_keywords = [
            'document', 'documents', 'file', 'files', 'pdf', 'docx', 'txt',
            'summarize', 'summary', 'contract', 'policy', 'procedure', 'manual',
            'report', 'guide', 'specification', 'spec'
        ]
        
        # Check if query explicitly mentions documents
        has_doc_keyword = any(keyword in query_lower for keyword in document_keywords)
        
        # Check for document reference patterns
        doc_patterns = [
            r'the\s+[a-z]+\s+document',
            r'[a-z]+\s+document',
            r'document\s+about',
            r'file\s+about',
            r'what\s+does\s+.*\s+say',
            r'what\s+is\s+in\s+.*',
            r'content\s+of',
            r'information\s+in'
        ]
        
        has_doc_pattern = any(re.search(pattern, query_lower) for pattern in doc_patterns)
        
        # If chunks were found AND query seems document-related, it's a document query
        if chunks and len(chunks) > 0:
            # Only consider it a document query if the query actually mentions documents
            # OR if the chunks are highly relevant (high scores)
            avg_score = sum(c.get('score', 0) for c in chunks) / len(chunks) if chunks else 0
            if has_doc_keyword or has_doc_pattern or avg_score > 0.7:
                return True
        
        # If query explicitly mentions documents, it's a document query
        if has_doc_keyword or has_doc_pattern:
            return True
        
        # General questions (hi, how are you, what can you do, etc.)
        general_patterns = [
            r'^hi\b', r'^hello\b', r'^hey\b',
            r'how\s+are\s+you',
            r'what\s+can\s+you\s+do',
            r'what\s+do\s+you\s+help',
            r'who\s+are\s+you',
            r'what\s+are\s+you'
        ]
        
        is_general = any(re.search(pattern, query_lower) for pattern in general_patterns)
        if is_general:
            return False
        
        # Default: if no clear indication, don't assume it's about documents
        return False
    
    def build_prompt(self, query: str, chunks: List[Dict], memory_context: str = "") -> Tuple[str, str]:
        """Build system and user prompts with context"""
        # Determine if this is actually a document query
        is_doc_query = self._is_document_query(query, chunks)
        
        # Updated system prompt to allow general questions
        system_prompt = """You are a helpful internal company AI assistant. You can answer both general questions and questions about company documents.

CRITICAL: DO NOT MENTION DOCUMENTS UNLESS THE USER EXPLICITLY ASKS ABOUT THEM.
- If the user asks a general question (like "hi", "what can you do", "how are you"), answer naturally WITHOUT mentioning documents.
- Only talk about documents when the user explicitly asks about documents, files, or document content.
- Do NOT say things like "based on the documents" or "from the documents" when answering general questions.

CRITICAL LANGUAGE RULE - READ CAREFULLY:
- If the user's question is in ENGLISH, you MUST respond ONLY in ENGLISH. Do not start with Arabic.
- If the user's question is in ARABIC, you MUST respond ONLY in ARABIC. Do not start with English.
- NEVER mix languages in a single response.
- NEVER start with one language and switch to another.
- The language of your response must EXACTLY match the language of the question.

INTELLIGENT CONTEXT SWITCHING - BE SMART ABOUT TOPIC CHANGES:
- When a user asks about a NEW document or topic, focus ONLY on that new topic. Ignore previous conversation context if it's about a different document/topic.
- If the user asks about "document 1" then later asks about "document 2" or mentions a different document name, understand they've switched topics.
- Examples of topic switches: "tell me about the contract" → "what about the policy document?" (switched from contract to policy)
- When you detect a topic switch, prioritize the CURRENT question and its context over previous conversation.
- Only use previous conversation context if it's directly relevant to the CURRENT question.

INTELLIGENT DOCUMENT UNDERSTANDING - BE PROACTIVE:
- When a user asks about "the [word] document" or "[word] document", understand they're referring to a document with that word in its title.
- Examples: "the switch document" = document with "switch" in the title, "summarize the contract" = document with "contract" in the title, "the PDF" = any PDF document.
- If document context is provided in the user prompt, USE IT IMMEDIATELY. Don't say you don't have access if context is provided.
- Be proactive: if context shows document titles or content, assume you can answer questions about them.
- When summarizing, provide comprehensive summaries based on ALL provided context chunks.
- If asked to summarize and you have context, provide a detailed summary immediately without saying you don't have access.

For general questions (about how to use the system, what you can help with, what you have access to, etc.), answer directly and helpfully. Examples:
- "hi" → Greet the user and explain what you can help with (in the SAME language as "hi")
- "what can you help me with" → List your capabilities clearly (in English if asked in English)
- "what do I have access to" → Explain what information and features are available (in the SAME language as the question)

For questions about company-specific information (policies, procedures, documents):
- ALWAYS check if document context is provided in the user prompt before saying you don't have access.
- If document excerpts are provided, use them immediately to answer the question comprehensively.
- If no relevant documents are provided, explain that documents may need to be indexed, but you can still help with general questions.
- When summarizing documents, provide comprehensive summaries based on ALL provided context chunks.

When using document excerpts, provide citations to the document titles. Keep answers concise, professional, and in the same language as the question."""
        
        # Only include document context if this is actually a document query
        if is_doc_query and chunks and len(chunks) > 0:
            # This is a document query - include document context
            context_parts = []
            for chunk in chunks:
                doc_title = chunk.get('title', 'Unknown Document')
                chunk_text = chunk.get('text', '')
                context_parts.append(f"[DOC - title: {doc_title}]\n{chunk_text}")
            
            context = "\n\n".join(context_parts)
            
            # Truncate context to token budget
            if self.tokenizer:
                context_tokens = self.tokenizer.encode(context)
                if len(context_tokens) > 1500:  # Leave room for query and response
                    context = self.tokenizer.decode(context_tokens[:1500])
            
            # Add memory context if available
            memory_section = f"\n\n{memory_context}" if memory_context else ""
            
            user_prompt = f"""Context from company documents:
{context}{memory_section}

Question: {query}

IMPORTANT INSTRUCTIONS:
1. Answer ONLY in the same language as the question (English if question is in English, Arabic if question is in Arabic).
2. FOCUS ON THE CURRENT QUESTION: If the question is about a specific document or topic, focus ONLY on that document/topic. Ignore previous conversation context if it's about something different.
3. If the question asks about a document (e.g., 'summarize the switch document', 'the contract document', 'what's in the PDF'), use the provided context to answer IMMEDIATELY and comprehensively.
4. If the question asks about what documents are available, list ALL document titles from the context above.
5. When summarizing, provide a comprehensive, detailed summary based on ALL the context chunks provided. Include key points, deliverables, scope, and important details.
6. Do NOT say you don't have access if context is provided - use the context to answer the question.
7. Be proactive and helpful - if context is provided, use it to give a complete answer without hesitation.
8. If previous conversation context is provided but seems unrelated to the current question, IGNORE IT and focus only on the current question and its document context."""
        else:
            # This is a GENERAL question - NO document context should be included
            # Add memory context only if relevant (and it doesn't mention documents)
            memory_section = ""
            if memory_context:
                # Only include memory if it doesn't force document discussion
                if 'document' not in memory_context.lower() and 'file' not in memory_context.lower():
                    memory_section = f"\n\nPrevious conversation: {memory_context}"
            
            user_prompt = f"""Question: {query}{memory_section}

IMPORTANT INSTRUCTIONS:
1. Answer ONLY in the same language as the question.
2. This is a GENERAL question - DO NOT mention documents, files, or document content unless the user explicitly asks about them.
3. Answer naturally and conversationally - like a helpful assistant, not a document search system.
4. If the user asks "what can you do" or "how can you help", explain your capabilities WITHOUT automatically mentioning documents.
5. Only talk about documents if the user explicitly asks about documents or document content.
6. Be friendly, helpful, and natural in your responses."""
        
        return system_prompt, user_prompt
    
    def generate_answer(self, system_prompt: str, user_prompt: str, query_intent: Dict = None) -> Tuple[str, Dict]:
        """Generate answer using local Ollama LLM with confidence scoring"""
        try:
            # Adjust temperature based on query complexity
            temperature = 0.7
            if query_intent and query_intent.get('complexity') == 'complex':
                temperature = 0.5  # Lower temperature for complex queries (more focused)
            elif query_intent and query_intent.get('complexity') == 'simple':
                temperature = 0.8  # Higher temperature for simple queries (more natural)
            
            # Adjust num_predict (max tokens) based on query type
            num_predict = 1024
            if query_intent and query_intent.get('action') == 'summarize':
                num_predict = 1536  # More tokens for summaries
            elif query_intent and query_intent.get('question_type') == 'yes_no':
                num_predict = 512  # Fewer tokens for yes/no questions
            
            # Combine system and user prompts for Ollama (it doesn't have separate system role in all versions)
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": full_prompt,
                    "system": system_prompt,  # Some Ollama versions support system prompt
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": num_predict,
                        "top_p": 0.9,
                        "top_k": 40
                    }
                },
                timeout=120  # Longer timeout for local inference
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('response', '').strip()
                
                if not answer:
                    return "AI service returned an empty response. Please check configuration.", {'confidence': 0.0, 'reasoning': 'Empty response'}
                
                # Calculate confidence score based on answer quality indicators
                confidence = self._calculate_answer_confidence(answer, user_prompt, query_intent)
                
                return answer, {'confidence': confidence, 'reasoning': self._get_confidence_reasoning(confidence, answer)}
            else:
                error_msg = f"Ollama API error: {response.status_code} - {response.text}"
                print(error_msg)
                return f"Error generating answer: {error_msg}", {'confidence': 0.0, 'reasoning': error_msg}
        except requests.exceptions.Timeout:
            return "AI service timeout. The model may be too slow or unavailable.", {'confidence': 0.0, 'reasoning': 'Timeout'}
        except requests.exceptions.RequestException as e:
            error_msg = f"Error connecting to Ollama: {str(e)}"
            print(error_msg)
            return f"AI service is not available. Please check that Ollama is running at {self.ollama_url}", {'confidence': 0.0, 'reasoning': error_msg}
        except Exception as e:
            print(f"Error generating answer: {e}")
            import traceback
            traceback.print_exc()
            return f"Error generating answer: {str(e)}", {'confidence': 0.0, 'reasoning': f'Error: {str(e)}'}
    
    def _calculate_answer_confidence(self, answer: str, user_prompt: str, query_intent: Dict = None) -> float:
        """Calculate confidence score for the answer (0.0 to 1.0)"""
        import re
        
        confidence = 0.5  # Base confidence
        
        # Check if answer is too short (might be incomplete)
        if len(answer) < 50:
            confidence -= 0.2
        elif len(answer) > 200:
            confidence += 0.1
        
        # Check if answer contains uncertainty phrases
        uncertainty_phrases = ['i don\'t know', 'i\'m not sure', 'unclear', 'uncertain', 'might be', 'could be', 'possibly']
        if any(phrase in answer.lower() for phrase in uncertainty_phrases):
            confidence -= 0.3
        
        # Check if answer contains citations/references (good sign)
        if '[DOC' in answer or 'document' in answer.lower() or 'source' in answer.lower():
            confidence += 0.2
        
        # Check if answer directly addresses the question type
        if query_intent:
            if query_intent.get('question_type') == 'yes_no':
                # Yes/no questions should have clear yes/no answers
                if re.search(r'\b(yes|no|correct|incorrect|true|false)\b', answer.lower()):
                    confidence += 0.2
            elif query_intent.get('action') == 'summarize':
                # Summaries should be comprehensive
                if len(answer.split()) > 50:
                    confidence += 0.1
        
        # Check for specific information (numbers, dates, names - indicates concrete answer)
        if re.search(r'\b\d+\b', answer) or re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', answer):
            confidence += 0.1
        
        # Normalize to 0.0-1.0 range
        confidence = max(0.0, min(1.0, confidence))
        
        return round(confidence, 2)
    
    def _get_confidence_reasoning(self, confidence: float, answer: str) -> str:
        """Get human-readable reasoning for confidence score"""
        if confidence >= 0.8:
            return "High confidence - answer is comprehensive and directly addresses the question"
        elif confidence >= 0.6:
            return "Moderate confidence - answer is relevant but may need verification"
        elif confidence >= 0.4:
            return "Low-moderate confidence - answer may be incomplete or uncertain"
        else:
            return "Low confidence - answer may not fully address the question"
    
    def log_query(self, user_id: str, query_text: str, response_text: str, 
                  sources: List[Dict], risk_score: Optional[float] = None,
                  policy_decision: Optional[str] = None, mfa_required: bool = False,
                  elapsed_ms: int = 0, query_id: str = None) -> str:
        """Log query to database for audit and quality monitoring"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            if not query_id:
                query_id = str(uuid.uuid4())
            
            cur.execute("""
                INSERT INTO ai_queries (id, user_id, query_text, response_text, sources, 
                                      risk_score, policy_decision, mfa_required, elapsed_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (query_id, user_id, query_text, response_text, json.dumps(sources), 
                  risk_score, policy_decision, mfa_required, elapsed_ms))
            conn.commit()
            
            # Record quality metrics
            today = datetime.utcnow().date().isoformat()
            success = policy_decision != 'blocked' and elapsed_ms < 30000  # 30s timeout
            relevance_score = len(sources) * 10.0 if sources else 0.0  # Simple relevance metric
            
            self.enterprise.record_quality_metric(today, 'daily', {
                'query_count': 1,
                'success_count': 1 if success else 0,
                'failure_count': 0 if success else 1,
                'avg_response_time_ms': elapsed_ms,
                'avg_relevance_score': relevance_score,
                'harmful_response_count': 0,  # Would be determined by content analysis
                'wrong_response_count': 0,  # Would be determined by feedback
                'dataset_drift_score': 0.0  # Would be calculated from dataset changes
            })
            
            cur.close()
            conn.close()
            return query_id
        except Exception as e:
            print(f"Error logging query: {e}")
            return query_id or str(uuid.uuid4())
    
    def query(self, user_id: str, query_text: str, filters: Optional[Dict] = None, 
             top_k: int = 6, conversation_id: str = None, plugin_id: str = None,
             use_memory: bool = True, enable_tools: bool = False) -> Dict:
        """
        Main RAG query flow with enterprise features
        Returns: {answer, sources, meta, tools_used?, memory_used?}
        """
        start_time = time.time()
        
        # Generate query_id early for debug logging (used throughout the function)
        query_id_for_logging = str(uuid.uuid4())
        
        # Get user context for plugins and permissions
        user_context = self._get_user_context(user_id)
        user_permissions = user_context.get('permissions', [])
        
        # Get conversation memories for context resolution
        conversation_memories = []
        if use_memory and conversation_id:
            conversation_memories = self.enterprise.get_memories(conversation_id, user_id)
        
        # Resolve pronouns and references in follow-up questions
        resolved_query = self._resolve_pronouns_and_references(query_text, conversation_memories)
        if resolved_query != query_text:
            print(f"Resolved query: '{query_text}' -> '{resolved_query}'")
            query_text = resolved_query
        
        # Detect query intent for smarter handling
        query_intent = self._detect_query_intent(query_text)
        print(f"Query intent: {query_intent}")
        
        # Check if user is asking about document availability or specific documents
        doc_availability_keywords = ['what documents', 'what files', 'list documents', 'show documents', 
                                    'documents uploaded', 'documents available', 'documents do you have',
                                    'documents can you access', 'what do you have access to', 'do you know']
        is_doc_list_query = any(keyword in query_text.lower() for keyword in doc_availability_keywords) or query_intent.get('action') == 'list'
        
        # Expand query for better search (add synonyms, related terms)
        expanded_query = self._expand_query(query_text, conversation_memories)
        
        # Extract search terms from query - smart document name detection
        search_query = query_text
        import re
        
        # Strategy 1: If query contains a full document filename, extract keywords
        doc_name_match = re.search(r'([A-Za-z0-9_\-]+\.(docx?|pdf|txt))', query_text, re.IGNORECASE)
        if doc_name_match:
            doc_name = doc_name_match.group(1)
            # Extract keywords from document name (remove extensions, underscores, numbers)
            keywords = re.sub(r'[._0-9]+', ' ', doc_name).split()
            if keywords:
                search_query = ' '.join([k for k in keywords if len(k) > 3]) or query_text
                print(f"Extracted search keywords from document name: {search_query}")
        else:
            # Strategy 2: Check if user mentions "the [word] document" or "[word] document"
            # This handles queries like "summarize the switch document"
            doc_reference_match = re.search(r'(?:the\s+)?([a-z]+)\s+document', query_text.lower())
            if doc_reference_match:
                doc_keyword = doc_reference_match.group(1)
                # Check if this keyword matches any document title in the database
                try:
                    conn = self.get_db_connection()
                    cur = conn.cursor(cursor_factory=RealDictCursor)
                    cur.execute("""
                        SELECT title FROM kb_documents 
                        WHERE LOWER(title) LIKE LOWER(%s)
                        LIMIT 1
                    """, (f'%{doc_keyword}%',))
                    matching_doc = cur.fetchone()
                    cur.close()
                    conn.close()
                    
                    if matching_doc:
                        # Found a matching document - extract keywords from its title
                        doc_title = matching_doc['title']
                        keywords = re.sub(r'[._0-9]+', ' ', doc_title).split()
                        if keywords:
                            # Use the keyword from query + other meaningful words from title
                            search_query = f"{doc_keyword} {' '.join([k for k in keywords if len(k) > 3 and k.lower() != doc_keyword][:3])}"
                            print(f"Matched document reference '{doc_keyword}' to '{doc_title}', using search: {search_query}")
                except Exception as e:
                    print(f"Error checking document reference: {e}")
            
            # Strategy 3: Extract key nouns/terms from the query for better search
            # Remove common stop words and extract meaningful terms
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'please', 'can', 'you', 'summarize', 'document', 'documents', 'file', 'files', 'tell', 'me', 'about', 'what', 'is', 'are', 'do', 'does', 'did', 'will', 'would', 'should', 'could'}
            words = re.findall(r'\b[a-z]+\b', query_text.lower())
            meaningful_words = [w for w in words if w not in stop_words and len(w) > 2]
            if meaningful_words:
                # Prioritize longer, more specific words
                meaningful_words.sort(key=lambda x: (len(x), x), reverse=True)
                # Use top 3 most meaningful words
                search_query = ' '.join(meaningful_words[:3])
                print(f"Extracted meaningful terms from query: {search_query}")
        
        # Step 1: Generate query embedding (use expanded query for better semantic search)
        query_embedding = self.generate_embedding(expanded_query if expanded_query != query_text else search_query)
        
        # Step 2: Search chunks (hybrid search) - but don't require documents
        # For document list queries, search for all documents or get from DB
        if is_doc_list_query:
            # Get all documents from database
            try:
                conn = self.get_db_connection()
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT d.id, d.title, d.source, d.path, d.uploaded_at
                    FROM kb_documents d
                    ORDER BY d.uploaded_at DESC
                    LIMIT 20
                """)
                all_docs = cur.fetchall()
                cur.close()
                conn.close()
                
                # Create chunks from document titles for context
                chunks = []
                for doc in all_docs:
                    chunks.append({
                        'id': str(doc['id']),
                        'document_id': str(doc['id']),
                        'title': doc['title'],
                        'text': f"Document: {doc['title']} (Source: {doc['source']})",
                        'source': doc['source']
                    })
            except Exception as e:
                print(f"Error fetching documents list: {e}")
                chunks = self.search_chunks(search_query, query_embedding, filters, top_k)
        else:
            # For regular queries, search for relevant chunks using extracted search query
            chunks = self.search_chunks(search_query, query_embedding, filters, top_k * 2,  # Get more for re-ranking
                                      query_id=query_id_for_logging, debug=True)
            
            # Re-rank chunks based on query intent and relevance
            if chunks:
                chunks = self._rerank_chunks(chunks, query_text, query_intent)
                chunks = chunks[:top_k]  # Keep top K after re-ranking
            
            # If no chunks found, try multiple fallback strategies
            if len(chunks) == 0:
                # Fallback 1: Try searching with original query
                if search_query != query_text:
                    chunks = self.search_chunks(query_text, query_embedding, filters, top_k,
                                              query_id=query_id_for_logging, debug=True)
                
                # Fallback 2: If still no results, check if user is asking about a specific document
                if len(chunks) == 0:
                    try:
                        conn = self.get_db_connection()
                        cur = conn.cursor(cursor_factory=RealDictCursor)
                        
                        # Extract potential document keywords from query
                        query_lower = query_text.lower()
                        # Look for document-related patterns
                        doc_patterns = [
                            r'(?:the\s+)?([a-z]+)\s+document',
                            r'summarize\s+([a-z]+)',
                            r'([a-z]+)\s+file',
                            r'([a-z]+)\s+uploaded'
                        ]
                        
                        potential_keywords = []
                        for pattern in doc_patterns:
                            matches = re.findall(pattern, query_lower)
                            potential_keywords.extend(matches)
                        
                        # Also extract any capitalized words (might be document names)
                        capitalized_words = re.findall(r'\b[A-Z][a-z]+\b', query_text)
                        potential_keywords.extend([w.lower() for w in capitalized_words])
                        
                        # Search for documents matching any of these keywords
                        if potential_keywords:
                            for keyword in potential_keywords[:3]:  # Try top 3 keywords
                                if len(keyword) > 2:  # Skip very short words
                                    cur.execute("""
                                        SELECT d.id, d.title, d.source, COUNT(c.id) as chunk_count
                                        FROM kb_documents d
                                        LEFT JOIN kb_chunks c ON c.document_id = d.id
                                        WHERE LOWER(d.title) LIKE LOWER(%s)
                                        GROUP BY d.id, d.title, d.source
                                        LIMIT 5
                                    """, (f'%{keyword}%',))
                                    matching_docs = cur.fetchall()
                                    
                                    if matching_docs:
                                        for doc in matching_docs:
                                            chunk_count = doc.get('chunk_count', 0) or 0
                                            if chunk_count > 0:
                                                # Found indexed document - search for its content
                                                doc_title = doc['title']
                                                # Extract keywords from document title for search
                                                title_keywords = re.sub(r'[._0-9]+', ' ', doc_title).split()
                                                search_terms = ' '.join([k for k in title_keywords if len(k) > 3][:5])
                                                if search_terms:
                                                    chunks = self.search_chunks(search_terms, query_embedding, filters, top_k * 2,
                                                                              query_id=query_id_for_logging, debug=True)
                                                    if chunks:
                                                        print(f"Found document '{doc_title}' using keyword '{keyword}', retrieved {len(chunks)} chunks")
                                                        break
                                        if chunks:
                                            break
                        
                        cur.close()
                        conn.close()
                    except Exception as e:
                        print(f"Error in fallback document search: {e}")
                        import traceback
                        traceback.print_exc()
        
        # Apply plugin filtering if plugin_id is specified
        if plugin_id:
            plugin_docs = self.enterprise.get_plugin_documents(plugin_id, filters)
            if plugin_docs:
                # Filter chunks to only include documents from this plugin
                plugin_doc_ids = [str(doc['id']) for doc in plugin_docs]
                chunks = [c for c in chunks if c.get('document_id') in plugin_doc_ids]
        
        # Detect current topic/document from query for smart context filtering
        # Do this BEFORE getting memory so we can filter memories by relevance
        current_topic_keywords = self._detect_topic_from_query(query_text, chunks)
        
        # Get conversation memory if enabled - filter by relevance to current topic
        memory_context = ""
        if use_memory and conversation_id:
            memories = self.enterprise.get_memories(conversation_id, user_id)
            if memories:
                # Filter memories by relevance to current topic
                relevant_memories = self._filter_relevant_memories(memories, current_topic_keywords, query_text)
                
                if relevant_memories:
                    memory_context = "\n\nPrevious conversation context (relevant to current question):\n"
                    for mem in relevant_memories[:3]:  # Limit to 3 most relevant memories
                        memory_context += f"- {mem['content']}\n"
                # If no relevant memories but user is clearly switching topics, don't include old context
                elif current_topic_keywords and len(chunks) > 0:
                    # User is asking about a new topic - don't confuse with old context
                    memory_context = ""
        
        # Step 3: Build prompt (works with or without chunks)
        # Only pass chunks if this is actually a document query
        # This prevents the AI from mentioning documents when answering general questions
        chunks_for_prompt = chunks if self._is_document_query(query_text, chunks) else []
        system_prompt, user_prompt = self.build_prompt(query_text, chunks_for_prompt, memory_context)
        
        # Check if tools should be used
        tools_used = []
        if enable_tools:
            available_tools = self.enterprise.get_available_tools(user_permissions)
            # Simple tool detection - in production, use LLM to determine if tools are needed
            tool_keywords = {
                'tool-fetch-logs': ['logs', 'log', 'error', 'debug'],
                'tool-server-status': ['status', 'health', 'server'],
                'tool-restart-service': ['restart', 'reboot', 'service'],
                'tool-trigger-build': ['build', 'deploy', 'ci/cd'],
                'tool-create-ticket': ['ticket', 'issue', 'bug', 'problem']
            }
            
            query_lower = query_text.lower()
            for tool in available_tools:
                tool_id = tool.get('tool_id')
                keywords = tool_keywords.get(tool_id, [])
                if any(kw in query_lower for kw in keywords):
                    # Execute tool (simplified - in production, extract parameters from query)
                    tool_result = self.enterprise.execute_tool(tool_id, user_id, {}, None)
                    if tool_result.get('success'):
                        tools_used.append({
                            'tool_id': tool_id,
                            'tool_name': tool.get('tool_name'),
                            'result': tool_result.get('result')
                        })
                        # Add tool result to context
                        user_prompt += f"\n\nTool Result ({tool.get('tool_name')}): {json.dumps(tool_result.get('result', {}))}"
        
        # Step 4: Generate answer (always generate, even without documents)
        answer, confidence_info = self.generate_answer(system_prompt, user_prompt, query_intent)
        
        # Step 5: Extract sources (if any)
        sources = []
        if chunks:
            sources = [
                {
                    'document_id': chunk.get('document_id'),
                    'title': chunk.get('title', 'Unknown'),
                    'chunk_id': chunk.get('id'),
                    'source': chunk.get('source')
                }
                for chunk in chunks
            ]
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        # Log query with query_id for retrieval debugging
        logged_query_id = self.log_query(
            user_id=user_id,
            query_text=query_text,
            response_text=answer,
            sources=sources,
            risk_score=None,  # Would be set by caller
            policy_decision=None,  # Would be set by caller
            mfa_required=False,  # Would be set by caller
            elapsed_ms=elapsed_ms,
            query_id=query_id_for_logging
        )
        
        # Save important information to memory
        if use_memory and conversation_id and answer:
            # Determine if this should be saved as long-term memory
            importance_keywords = ['policy', 'procedure', 'important', 'critical', 'update', 'change']
            is_important = any(kw in query_text.lower() or kw in answer.lower() for kw in importance_keywords)
            
            if is_important:
                self.enterprise.save_memory(
                    conversation_id, user_id, 'long_term',
                    f"Q: {query_text}\nA: {answer[:200]}",  # Truncate for storage
                    importance_score=80.0
                )
            else:
                # Save as short-term memory (expires in 24 hours)
                self.enterprise.save_memory(
                    conversation_id, user_id, 'short_term',
                    f"Q: {query_text}\nA: {answer[:200]}",
                    importance_score=30.0,
                    expires_in_hours=24
                )
        
        # Generate proactive suggestions for related questions
        suggestions = self._generate_suggestions(query_text, chunks, query_intent)
        
        result = {
            'answer': answer,
            'sources': sources,
            'meta': {
                'elapsed_ms': elapsed_ms,
                'confidence': confidence_info.get('confidence', 0.5),
                'confidence_reasoning': confidence_info.get('reasoning', ''),
                'query_intent': query_intent,
                'suggestions': suggestions
            }
        }
        
        if tools_used:
            result['tools_used'] = tools_used
        
        if memory_context:
            result['meta']['memory_used'] = True
        
        return result
    
    def _generate_suggestions(self, query: str, chunks: List[Dict], query_intent: Dict) -> List[str]:
        """Generate proactive suggestions for related questions"""
        suggestions = []
        
        if not chunks or len(chunks) == 0:
            return suggestions
        
        # Extract topics from retrieved chunks
        topics = set()
        for chunk in chunks[:3]:  # Top 3 chunks
            title = chunk.get('title', '')
            if title:
                # Extract key terms from title
                import re
                words = re.findall(r'\b[A-Z][a-z]+\b', title)
                topics.update([w.lower() for w in words if len(w) > 3])
        
        # Generate suggestions based on query intent and topics
        if query_intent.get('action') == 'summarize':
            # If summarizing, suggest specific questions
            for topic in list(topics)[:2]:
                suggestions.append(f"What are the key points about {topic}?")
                suggestions.append(f"Tell me more about {topic}")
        elif query_intent.get('question_type') == 'what':
            # If asking "what", suggest "how" or "why"
            for topic in list(topics)[:1]:
                suggestions.append(f"How does {topic} work?")
                suggestions.append(f"Why is {topic} important?")
        else:
            # General suggestions
            for topic in list(topics)[:2]:
                suggestions.append(f"Tell me more about {topic}")
        
        # Limit to 3 suggestions
        return suggestions[:3]
    
    def extract_text_from_file(self, file_path: str, content_type: str) -> str:
        """Extract text from file based on content type"""
        try:
            if content_type == 'application/pdf' or file_path.lower().endswith('.pdf'):
                import PyPDF2
                text = ""
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                return text
            elif content_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword'] or file_path.lower().endswith(('.docx', '.doc')):
                from docx import Document
                doc = Document(file_path)
                return "\n".join([para.text for para in doc.paragraphs])
            elif content_type == 'text/plain' or file_path.lower().endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                # Try to read as text
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except:
                    return ""
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            return ""
    
    def chunk_text(self, text: str, max_tokens: int = None) -> List[str]:
        """Split text into chunks"""
        if not max_tokens:
            max_tokens = self.max_chunk_tokens
        
        if not self.tokenizer:
            # Fallback: simple character-based chunking
            chunk_size = max_tokens * 4  # Rough estimate: 4 chars per token
            chunks = []
            for i in range(0, len(text), chunk_size - self.chunk_overlap * 4):
                chunks.append(text[i:i + chunk_size])
            return chunks
        
        # Token-based chunking
        tokens = self.tokenizer.encode(text)
        chunks = []
        overlap_tokens = self.chunk_overlap
        
        for i in range(0, len(tokens), max_tokens - overlap_tokens):
            chunk_tokens = tokens[i:i + max_tokens]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text)
        
        return chunks
    
    def ingest_document_from_gateway(self, file_id: str, file_path: str, filename: str,
                                     source: str = 'file-gateway', department: str = None,
                                     tags: List[str] = None) -> Dict:
        """Ingest a document from File Gateway"""
        try:
            # Step 1: Get decrypted file content from backend-core API
            # This avoids sharing encryption keys between services
            backend_url = os.getenv('BACKEND_CORE_URL', 'http://backend-core:3001')
            decrypt_url = f"{backend_url}/api/file-gateway/internal/decrypt-for-ai"
            
            print(f"Requesting decrypted file from backend-core for file_id: {file_id}")
            
            try:
                response = requests.post(decrypt_url, json={'fileId': file_id}, timeout=30)
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        decrypted_content = base64.b64decode(result['content'])
                        content_type = result.get('content_type', 'application/octet-stream')
                        
                        # Save decrypted content to temp file for extraction
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
                            temp_file.write(decrypted_content)
                            temp_path = temp_file.name
                        
                        print(f"Successfully decrypted file via API, saved to: {temp_path}")
                    else:
                        return {'chunks_created': 0, 'error': 'Backend decryption failed'}
                else:
                    print(f"Failed to decrypt via API: {response.status_code} - {response.text}")
                    # Fallback: try local decryption
                    return self._ingest_with_local_decryption(file_id, file_path, filename, source, department, tags)
            except requests.exceptions.RequestException as e:
                print(f"Error calling decrypt API: {e}")
                # Fallback: try local decryption
                return self._ingest_with_local_decryption(file_id, file_path, filename, source, department, tags)
            
            # Step 2: Extract text from decrypted file
            if filename.lower().endswith('.pdf'):
                content_type = 'application/pdf'
            elif filename.lower().endswith(('.docx', '.doc')):
                content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            elif filename.lower().endswith('.txt'):
                content_type = 'text/plain'
            else:
                content_type = 'application/octet-stream'
            
            text = self.extract_text_from_file(temp_path, content_type)
            
            # Clean up temp file
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            
            if not text or len(text.strip()) < 10:
                return {'chunks_created': 0, 'error': 'No text extracted from file'}
            
            # Step 4: Create document record
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            # Check if document already exists
            cur.execute("SELECT id FROM kb_documents WHERE path = %s", (file_path,))
            existing = cur.fetchone()
            
            if existing:
                doc_id = existing[0]
            else:
                cur.execute("""
                    INSERT INTO kb_documents (title, source, path, uploaded_by, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (filename, source, file_path, 'system', json.dumps({
                    'file_id': file_id,
                    'department': department,
                    'tags': tags or []
                })))
                doc_id = cur.fetchone()[0]
            
            # Step 5: Chunk text
            chunks = self.chunk_text(text)
            
            # Step 6: Create chunks and embeddings
            chunks_created = 0
            for idx, chunk_text in enumerate(chunks):
                if not chunk_text.strip():
                    continue
                
                # Insert chunk
                cur.execute("""
                    INSERT INTO kb_chunks (document_id, chunk_index, text, metadata)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (doc_id, idx, chunk_text, json.dumps({})))
                chunk_id = cur.fetchone()[0]
                
                # Generate embedding
                embedding = self.generate_embedding(chunk_text)
                if embedding:
                    # Insert embedding
                    cur.execute("""
                        INSERT INTO kb_embeddings (chunk_id, vector)
                        VALUES (%s, %s)
                    """, (chunk_id, json.dumps(embedding)))
                
                # Index in Meilisearch
                if self.meilisearch_client:
                    try:
                        index = self.meilisearch_client.index('kb_chunks')
                        index.add_documents([{
                            'id': str(chunk_id),
                            'document_id': str(doc_id),
                            'title': filename,
                            'text': chunk_text,
                            'source': source,
                            'department': department,
                            'tags': tags or [],
                            'chunk_index': idx
                        }])
                    except Exception as e:
                        print(f"Error indexing chunk in Meilisearch: {e}")
                
                chunks_created += 1
            
            conn.commit()
            cur.close()
            conn.close()
            
            return {
                'chunks_created': chunks_created,
                'document_id': str(doc_id)
            }
            
        except Exception as e:
            print(f"Error ingesting document: {e}")
            return {'chunks_created': 0, 'error': str(e)}
    
    def _ingest_with_local_decryption(self, file_id: str, file_path: str, filename: str,
                                      source: str, department: str, tags: List[str]) -> Dict:
        """Fallback: Try to decrypt and ingest locally (when API is unavailable)"""
        try:
            # Files are stored in shared volume: /app/storage/secure-files/
            storage_path = os.getenv('STORAGE_PATH', '/app/storage')
            filename_only = os.path.basename(file_path)
            full_path = os.path.join(storage_path, 'secure-files', filename_only)
            
            if not os.path.exists(full_path):
                if file_path.startswith('/storage/'):
                    alt_path = file_path.replace('/storage/', '/app/storage/')
                    if os.path.exists(alt_path):
                        full_path = alt_path
                    else:
                        return {'chunks_created': 0, 'error': f'File not accessible: {filename_only}'}
                else:
                    return {'chunks_created': 0, 'error': f'File not accessible at {full_path}'}
            
            # Try to decrypt locally (requires ENCRYPTION_MASTER_KEY to match backend-core)
            with open(full_path, 'rb') as f:
                encrypted_data = f.read()
            
            if len(encrypted_data) < 32:
                # File might not be encrypted
                text = self.extract_text_from_file(full_path, 'application/octet-stream')
            else:
                iv = encrypted_data[:16]
                tag = encrypted_data[16:32]
                encrypted_content = encrypted_data[32:]
                
                try:
                    decrypted_content = self._decrypt_file(encrypted_content, iv, tag, file_id)
                except Exception as e:
                    print(f"Local decryption failed: {e}")
                    return {'chunks_created': 0, 'error': f'Decryption failed: {str(e)}. ENCRYPTION_MASTER_KEY may not match backend-core.'}
                
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
                    temp_file.write(decrypted_content)
                    temp_path = temp_file.name
                
                content_type = 'application/octet-stream'
                if filename.lower().endswith('.pdf'):
                    content_type = 'application/pdf'
                elif filename.lower().endswith(('.docx', '.doc')):
                    content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                
                text = self.extract_text_from_file(temp_path, content_type)
                os.unlink(temp_path)
            
            if not text or len(text.strip()) < 10:
                return {'chunks_created': 0, 'error': 'No text extracted from file'}
            
            # Continue with document creation (same as main function)
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            cur.execute("SELECT id FROM kb_documents WHERE path = %s", (file_path,))
            existing = cur.fetchone()
            
            if existing:
                doc_id = existing[0]
            else:
                cur.execute("""
                    INSERT INTO kb_documents (title, source, path, uploaded_by, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (filename, source, file_path, 'system', json.dumps({
                    'file_id': file_id,
                    'department': department,
                    'tags': tags or []
                })))
                doc_id = cur.fetchone()[0]
            
            chunks = self.chunk_text(text)
            chunks_created = 0
            
            for idx, chunk_text in enumerate(chunks):
                if not chunk_text.strip():
                    continue
                
                cur.execute("""
                    INSERT INTO kb_chunks (document_id, chunk_index, text, metadata)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (doc_id, idx, chunk_text, json.dumps({})))
                chunk_id = cur.fetchone()[0]
                
                if self.meilisearch_client:
                    try:
                        index = self.meilisearch_client.index('kb_chunks')
                        index.add_documents([{
                            'id': str(chunk_id),
                            'document_id': str(doc_id),
                            'title': filename,
                            'text': chunk_text,
                            'source': source,
                            'department': department,
                            'tags': tags or [],
                            'chunk_index': idx
                        }])
                    except Exception as e:
                        print(f"Error indexing chunk in Meilisearch: {e}")
                
                chunks_created += 1
            
            conn.commit()
            cur.close()
            conn.close()
            
            return {
                'chunks_created': chunks_created,
                'document_id': str(doc_id)
            }
        except Exception as e:
            print(f"Error in local decryption fallback: {e}")
            import traceback
            traceback.print_exc()
            return {'chunks_created': 0, 'error': str(e)}
    
    def reindex_documents(self) -> Dict:
        """Reindex all documents from secure_files table"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get all active files from secure_files
            cur.execute("""
                SELECT file_id, filename, file_path, department, tags, content_type
                FROM secure_files
                WHERE status = 'active' AND dlp_scan_status = 'clean'
            """)
            files = cur.fetchall()
            
            documents_processed = 0
            total_chunks = 0
            
            for file_row in files:
                result = self.ingest_document_from_gateway(
                    file_id=file_row['file_id'],
                    file_path=file_row['file_path'],
                    filename=file_row['filename'],
                    source='file-gateway',
                    department=file_row.get('department'),
                    tags=file_row.get('tags') or []
                )
                if result.get('chunks_created', 0) > 0:
                    documents_processed += 1
                    total_chunks += result.get('chunks_created', 0)
            
            cur.close()
            conn.close()
            
            return {
                'documents_processed': documents_processed,
                'chunks_created': total_chunks
            }
            
        except Exception as e:
            print(f"Error reindexing documents: {e}")
            return {'documents_processed': 0, 'chunks_created': 0, 'error': str(e)}

