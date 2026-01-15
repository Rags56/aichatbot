"""
AI Enterprise Features Extension
Adds plugins, memory, tools, quality monitoring, and administration features
"""
import os
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
import requests

class AIEnterpriseFeatures:
    """Enterprise features for AI Chatbot"""
    
    def __init__(self, db_url: str, backend_core_url: str = None):
        self.db_url = db_url
        self.backend_core_url = backend_core_url or os.getenv('BACKEND_CORE_URL', 'http://backend-core:3001')
    
    def get_db_connection(self):
        """Get PostgreSQL connection"""
        return psycopg2.connect(self.db_url)
    
    # ========== PLUGIN SYSTEM ==========
    
    def get_plugins_for_user(self, user_id: str, user_permissions: List[str]) -> List[Dict]:
        """Get available plugins for a user based on permissions"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get plugins that user has access to
            cur.execute("""
                SELECT p.*, COUNT(pd.document_id) as document_count
                FROM kb_plugins p
                LEFT JOIN kb_plugin_documents pd ON p.id = pd.plugin_id
                WHERE p.status = 'active'
                AND (
                    p.access_permissions = '{}'::text[] OR
                    p.access_permissions && %s::text[]
                )
                GROUP BY p.id
                ORDER BY p.plugin_name
            """, (user_permissions,))
            
            plugins = cur.fetchall()
            cur.close()
            conn.close()
            
            return [dict(p) for p in plugins]
        except Exception as e:
            print(f"Error getting plugins: {e}")
            return []
    
    def get_plugin_documents(self, plugin_id: str, filters: Dict = None) -> List[Dict]:
        """Get documents for a specific plugin"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT d.*
                FROM kb_documents d
                JOIN kb_plugin_documents pd ON d.id = pd.document_id
                JOIN kb_plugins p ON pd.plugin_id = p.id
                WHERE p.plugin_id = %s
            """
            params = [plugin_id]
            
            if filters:
                if 'department' in filters:
                    query += " AND d.department = %s"
                    params.append(filters['department'])
                if 'classification' in filters:
                    query += " AND d.classification = %s"
                    params.append(filters['classification'])
            
            cur.execute(query, params)
            documents = cur.fetchall()
            cur.close()
            conn.close()
            
            return [dict(d) for d in documents]
        except Exception as e:
            print(f"Error getting plugin documents: {e}")
            return []
    
    def assign_document_to_plugin(self, document_id: str, plugin_id: str) -> bool:
        """Assign a document to a plugin"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            # Get plugin UUID
            cur.execute("SELECT id FROM kb_plugins WHERE plugin_id = %s", (plugin_id,))
            plugin = cur.fetchone()
            if not plugin:
                return False
            
            cur.execute("""
                INSERT INTO kb_plugin_documents (plugin_id, document_id)
                VALUES (%s, %s)
                ON CONFLICT (plugin_id, document_id) DO NOTHING
            """, (plugin[0], document_id))
            
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error assigning document to plugin: {e}")
            return False
    
    # ========== CONVERSATIONAL MEMORY ==========
    
    def save_memory(self, conversation_id: str, user_id: str, memory_type: str, 
                   content: str, importance_score: float = 0.0, expires_in_hours: int = None) -> str:
        """Save a memory (short-term or long-term)"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            memory_id = str(uuid.uuid4())
            expires_at = None
            if expires_in_hours:
                expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
            
            cur.execute("""
                INSERT INTO ai_conversation_memory 
                (id, conversation_id, user_id, memory_type, content, importance_score, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (memory_id, conversation_id, user_id, memory_type, content, importance_score, expires_at))
            
            conn.commit()
            cur.close()
            conn.close()
            return memory_id
        except Exception as e:
            print(f"Error saving memory: {e}")
            return None
    
    def get_memories(self, conversation_id: str, user_id: str = None, 
                    memory_type: str = None, include_expired: bool = False) -> List[Dict]:
        """Retrieve memories for a conversation"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT * FROM ai_conversation_memory
                WHERE conversation_id = %s
            """
            params = [conversation_id]
            
            if user_id:
                query += " AND user_id = %s"
                params.append(user_id)
            
            if memory_type:
                query += " AND memory_type = %s"
                params.append(memory_type)
            
            if not include_expired:
                query += " AND (expires_at IS NULL OR expires_at > NOW())"
            
            query += " ORDER BY importance_score DESC, created_at DESC LIMIT 20"
            
            cur.execute(query, params)
            memories = cur.fetchall()
            cur.close()
            conn.close()
            
            return [dict(m) for m in memories]
        except Exception as e:
            print(f"Error getting memories: {e}")
            return []
    
    def clear_expired_memories(self):
        """Clean up expired short-term memories"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                DELETE FROM ai_conversation_memory
                WHERE expires_at IS NOT NULL AND expires_at < NOW()
                AND memory_type = 'short_term'
            """)
            
            deleted = cur.rowcount
            conn.commit()
            cur.close()
            conn.close()
            return deleted
        except Exception as e:
            print(f"Error clearing expired memories: {e}")
            return 0
    
    # ========== TOOLS & ACTIONS ==========
    
    def get_available_tools(self, user_permissions: List[str]) -> List[Dict]:
        """Get tools available to user based on permissions"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("""
                SELECT * FROM ai_tools
                WHERE status = 'active'
                AND (
                    required_permissions = '{}'::text[] OR
                    required_permissions && %s::text[]
                )
                ORDER BY tool_name
            """, (user_permissions,))
            
            tools = cur.fetchall()
            cur.close()
            conn.close()
            
            return [dict(t) for t in tools]
        except Exception as e:
            print(f"Error getting tools: {e}")
            return []
    
    def execute_tool(self, tool_id: str, user_id: str, parameters: Dict, query_id: str = None) -> Dict:
        """Execute a tool/action"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get tool definition
            cur.execute("SELECT * FROM ai_tools WHERE tool_id = %s AND status = 'active'", (tool_id,))
            tool = cur.fetchone()
            if not tool:
                return {'success': False, 'error': 'Tool not found or disabled'}
            
            tool_dict = dict(tool)
            execution_id = str(uuid.uuid4())
            start_time = datetime.utcnow()
            
            # Log execution start
            cur.execute("""
                INSERT INTO ai_tool_executions 
                (id, query_id, tool_id, user_id, parameters, status)
                VALUES (%s, %s, %s, %s, %s, 'executing')
            """, (execution_id, query_id, tool_dict['id'], user_id, json.dumps(parameters)))
            conn.commit()
            
            # Execute based on tool type
            result = None
            error = None
            
            try:
                if tool_dict['tool_type'] == 'api':
                    result = self._execute_api_tool(tool_dict, parameters)
                elif tool_dict['tool_type'] == 'system':
                    result = self._execute_system_tool(tool_dict, parameters)
                elif tool_dict['tool_type'] == 'script':
                    result = self._execute_script_tool(tool_dict, parameters)
                elif tool_dict['tool_type'] == 'workflow':
                    result = self._execute_workflow_tool(tool_dict, parameters)
                else:
                    error = f"Unknown tool type: {tool_dict['tool_type']}"
            except Exception as e:
                error = str(e)
            
            elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Update execution record
            cur.execute("""
                UPDATE ai_tool_executions
                SET status = %s, result = %s, error_message = %s, execution_time_ms = %s, executed_at = NOW()
                WHERE id = %s
            """, (
                'success' if not error else 'failed',
                json.dumps(result) if result else None,
                error,
                elapsed_ms,
                execution_id
            ))
            conn.commit()
            cur.close()
            conn.close()
            
            return {
                'success': error is None,
                'result': result,
                'error': error,
                'execution_id': execution_id,
                'execution_time_ms': elapsed_ms
            }
        except Exception as e:
            print(f"Error executing tool: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_api_tool(self, tool: Dict, parameters: Dict) -> Dict:
        """Execute an API-based tool"""
        endpoint = tool.get('endpoint_url')
        if not endpoint:
            raise ValueError("API tool missing endpoint_url")
        
        # For now, implement specific tools
        tool_id = tool.get('tool_id')
        
        if tool_id == 'tool-fetch-logs':
            # Call backend-core system logs API
            service = parameters.get('service', 'backend-core')
            lines = parameters.get('lines', 50)
            level = parameters.get('level')
            
            url = f"{self.backend_core_url}/api/system-logs"
            params = {'limit': lines}
            if level:
                params['level'] = level
            if service:
                params['service'] = service
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {'logs': data.get('logs', [])[:lines]}
            else:
                raise Exception(f"Failed to fetch logs: {response.status_code}")
        
        elif tool_id == 'tool-server-status':
            # Placeholder - would call monitoring API
            return {'status': 'unknown', 'message': 'Server status check not implemented'}
        
        elif tool_id == 'tool-trigger-build':
            # Placeholder - would call CI/CD API
            return {'status': 'triggered', 'message': 'Build trigger not implemented'}
        
        elif tool_id == 'tool-create-ticket':
            # Placeholder - would call ticketing API
            return {'ticket_id': 'TICKET-123', 'message': 'Ticket creation not implemented'}
        
        else:
            raise ValueError(f"Unknown API tool: {tool_id}")
    
    def _execute_system_tool(self, tool: Dict, parameters: Dict) -> Dict:
        """Execute a system tool (requires careful security)"""
        tool_id = tool.get('tool_id')
        
        if tool_id == 'tool-restart-service':
            # Placeholder - in production, this would use proper service management
            service_name = parameters.get('service_name')
            return {'status': 'restarted', 'message': f'Service {service_name} restart not implemented (requires system access)'}
        
        raise ValueError(f"Unknown system tool: {tool_id}")
    
    def _execute_script_tool(self, tool: Dict, parameters: Dict) -> Dict:
        """Execute a script tool"""
        # Placeholder - in production, this would execute scripts securely
        return {'status': 'not_implemented', 'message': 'Script execution not implemented'}
    
    def _execute_workflow_tool(self, tool: Dict, parameters: Dict) -> Dict:
        """Execute a workflow tool"""
        tool_id = tool.get('tool_id')
        
        if tool_id == 'tool-update-kb':
            # Placeholder - would trigger KB update workflow
            article_id = parameters.get('article_id')
            return {'status': 'submitted', 'message': f'KB article {article_id} update submitted for approval'}
        
        raise ValueError(f"Unknown workflow tool: {tool_id}")
    
    # ========== KNOWLEDGE ADMINISTRATION ==========
    
    def create_dataset_version(self, dataset_id: str, description: str, created_by: str) -> Dict:
        """Create a new dataset version"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get latest version
            cur.execute("""
                SELECT MAX(version_number) as max_version
                FROM kb_dataset_versions
                WHERE dataset_id = %s
            """, (dataset_id,))
            result = cur.fetchone()
            next_version = (result['max_version'] or 0) + 1
            
            version_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO kb_dataset_versions
                (id, dataset_id, version_number, description, created_by, status)
                VALUES (%s, %s, %s, %s, %s, 'draft')
                RETURNING *
            """, (version_id, dataset_id, next_version, description, created_by))
            
            version = dict(cur.fetchone())
            conn.commit()
            cur.close()
            conn.close()
            
            return version
        except Exception as e:
            print(f"Error creating dataset version: {e}")
            return None
    
    def submit_for_validation(self, document_id: str, submitted_by: str) -> bool:
        """Submit a document for validation workflow"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO kb_validation_workflow
                (id, document_id, workflow_stage, submitted_by)
                VALUES (%s, %s, 'review', %s)
                ON CONFLICT DO NOTHING
            """, (str(uuid.uuid4()), document_id, submitted_by))
            
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error submitting for validation: {e}")
            return False
    
    def approve_document(self, document_id: str, approved_by: str, notes: str = None) -> bool:
        """Approve a document in validation workflow"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                UPDATE kb_validation_workflow
                SET workflow_stage = 'approved',
                    approved_by = %s,
                    approved_at = NOW(),
                    review_notes = %s
                WHERE document_id = %s
                AND workflow_stage = 'review'
            """, (approved_by, notes, document_id))
            
            conn.commit()
            cur.close()
            conn.close()
            return cur.rowcount > 0
        except Exception as e:
            print(f"Error approving document: {e}")
            return False
    
    def log_retrieval_debug(self, query_id: str, chunk_id: str, match_type: str,
                           similarity_score: float, keyword_score: float,
                           combined_score: float, rank_position: int,
                           matched_terms: List[str], debug_info: Dict = None):
        """Log retrieval debugging information"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO kb_retrieval_debug
                (id, query_id, chunk_id, match_type, similarity_score, keyword_score,
                 combined_score, rank_position, matched_terms, debug_info)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                str(uuid.uuid4()), query_id, chunk_id, match_type,
                similarity_score, keyword_score, combined_score, rank_position,
                matched_terms, json.dumps(debug_info or {})
            ))
            
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error logging retrieval debug: {e}")
    
    # ========== QUALITY MONITORING ==========
    
    def record_quality_metric(self, metric_date: str, metric_type: str, metrics: Dict):
        """Record quality metrics for monitoring"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO ai_quality_metrics
                (metric_date, metric_type, query_count, success_count, failure_count,
                 avg_response_time_ms, avg_relevance_score, harmful_response_count,
                 wrong_response_count, dataset_drift_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (metric_date, metric_type)
                DO UPDATE SET
                    query_count = ai_quality_metrics.query_count + EXCLUDED.query_count,
                    success_count = ai_quality_metrics.success_count + EXCLUDED.success_count,
                    failure_count = ai_quality_metrics.failure_count + EXCLUDED.failure_count,
                    avg_response_time_ms = (ai_quality_metrics.avg_response_time_ms + EXCLUDED.avg_response_time_ms) / 2,
                    avg_relevance_score = (ai_quality_metrics.avg_relevance_score + EXCLUDED.avg_relevance_score) / 2,
                    harmful_response_count = ai_quality_metrics.harmful_response_count + EXCLUDED.harmful_response_count,
                    wrong_response_count = ai_quality_metrics.wrong_response_count + EXCLUDED.wrong_response_count,
                    dataset_drift_score = EXCLUDED.dataset_drift_score,
                    updated_at = NOW()
            """, (
                metric_date, metric_type,
                metrics.get('query_count', 0),
                metrics.get('success_count', 0),
                metrics.get('failure_count', 0),
                metrics.get('avg_response_time_ms', 0),
                metrics.get('avg_relevance_score', 0.0),
                metrics.get('harmful_response_count', 0),
                metrics.get('wrong_response_count', 0),
                metrics.get('dataset_drift_score', 0.0)
            ))
            
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error recording quality metric: {e}")
    
    def get_quality_metrics(self, start_date: str = None, end_date: str = None, metric_type: str = 'daily') -> List[Dict]:
        """Get quality metrics"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            query = "SELECT * FROM ai_quality_metrics WHERE metric_type = %s"
            params = [metric_type]
            
            if start_date:
                query += " AND metric_date >= %s"
                params.append(start_date)
            if end_date:
                query += " AND metric_date <= %s"
                params.append(end_date)
            
            query += " ORDER BY metric_date DESC LIMIT 30"
            
            cur.execute(query, params)
            metrics = cur.fetchall()
            cur.close()
            conn.close()
            
            return [dict(m) for m in metrics]
        except Exception as e:
            print(f"Error getting quality metrics: {e}")
            return []
    
    # ========== CONTINUOUS SYNC ==========
    
    def create_sync_job(self, job_type: str, source_type: str, source_config: Dict) -> str:
        """Create a knowledge sync job"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            job_id = f"SYNC_{job_type}_{int(datetime.utcnow().timestamp())}"
            sync_id = str(uuid.uuid4())
            
            cur.execute("""
                INSERT INTO kb_sync_jobs
                (id, job_id, job_type, source_type, source_config, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
            """, (sync_id, job_id, job_type, source_type, json.dumps(source_config)))
            
            conn.commit()
            cur.close()
            conn.close()
            return job_id
        except Exception as e:
            print(f"Error creating sync job: {e}")
            return None
    
    def update_sync_job(self, job_id: str, status: str, documents_processed: int = 0,
                       chunks_created: int = 0, error_message: str = None):
        """Update a sync job status"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            update_fields = ['status = %s']
            params = [status]
            
            if documents_processed > 0:
                update_fields.append('documents_processed = %s')
                params.append(documents_processed)
            
            if chunks_created > 0:
                update_fields.append('chunks_created = %s')
                params.append(chunks_created)
            
            if error_message:
                update_fields.append('error_message = %s')
                params.append(error_message)
            
            if status == 'running' and 'started_at' not in update_fields:
                update_fields.append('started_at = NOW()')
            elif status in ['completed', 'failed']:
                update_fields.append('completed_at = NOW()')
            
            params.append(job_id)
            
            cur.execute(f"""
                UPDATE kb_sync_jobs
                SET {', '.join(update_fields)}
                WHERE job_id = %s
            """, params)
            
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error updating sync job: {e}")

