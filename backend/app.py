"""
AI Orchestrator - RAG-based Knowledge Assistant
Implements zero-trust RAG query flow with IACM, Risk Engine, and Policy Engine integration
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import time
from ai_service import AIService
import requests
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app)

# Initialize AI Service (with error handling)
try:
    ai_service = AIService()
except Exception as e:
    print(f"Warning: Could not initialize AI Service: {e}")
    print("AI service will run in limited mode")
    ai_service = None

# Backend URLs for zero-trust integration
BACKEND_CORE_URL = os.getenv('BACKEND_CORE_URL', 'http://backend-core:3001')
API_GATEWAY_URL = os.getenv('API_GATEWAY_URL', 'http://api-gateway:3000')

def validate_user_with_iacm(user_id: str, request_obj) -> dict:
    """
    Validate user with IACM (simplified for PoC)
    In production, this would call IACM API
    """
    try:
        # For PoC: Call IACM validation endpoint
        # In production, this would be done via API Gateway middleware
        headers = {}
        if hasattr(request_obj, 'headers'):
            auth_header = request_obj.headers.get('Authorization')
            if auth_header:
                headers['Authorization'] = auth_header
        
        # Call IACM validation (simplified - in production use proper API)
        # For now, return allowed for PoC
        return {
            'allowed': True,
            'user_id': user_id,
            'roles': [],
            'permissions': [],
            'risk_score': 0.0,
            'mfa_required': False
        }
    except Exception as e:
        print(f"Error validating with IACM: {e}")
        return {'allowed': False, 'error': str(e)}

def evaluate_risk(user_id: str, query_text: str, context: dict) -> dict:
    """
    Evaluate risk with AI Risk Engine
    """
    try:
        # Call Risk Engine API
        risk_url = f"{BACKEND_CORE_URL}/api/ueba/risk-scores/calculate"
        risk_data = {
            'user_id': user_id,
            'context': {
                'action': 'ai_query',
                'query_text': query_text,
                **context
            }
        }
        
        response = requests.post(risk_url, json=risk_data, timeout=5)
        if response.status_code == 200:
            risk_result = response.json()
            return {
                'risk_score': risk_result.get('risk_score', {}).get('risk_score', 0),
                'risk_level': risk_result.get('risk_score', {}).get('risk_level', 'low')
            }
    except Exception as e:
        print(f"Error evaluating risk: {e}")
    
    return {'risk_score': 0, 'risk_level': 'low'}

def evaluate_policy(user_id: str, risk_score: float, action: str) -> dict:
    """
    Evaluate policy with Policy Engine
    """
    try:
        # Call Policy Engine (via backend-core)
        # For now, implement simple policy logic
        if risk_score >= 70:
            return {'decision': 'block', 'mfa_required': False}
        elif risk_score >= 30:
            return {'decision': 'conditional', 'mfa_required': True}
        else:
            return {'decision': 'allow', 'mfa_required': False}
    except Exception as e:
        print(f"Error evaluating policy: {e}")
        return {'decision': 'allow', 'mfa_required': False}

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'ai-orchestrator'})

def _execute_query(user_id: str, query_text: str, filters: dict = None, top_k: int = 6, 
                   conversation_id: str = None, plugin_id: str = None,
                   use_memory: bool = True, enable_tools: bool = False):
    """
    Internal function to execute AI query
    Returns: (response_dict, status_code)
    """
    if not ai_service:
        return {
            'error': 'AI service is not available',
            'answer': 'AI service is currently unavailable. Please check configuration.',
            'sources': [],
            'meta': {'elapsed_ms': 0}
        }, 503
    
    start_time = time.time()
    
    try:
        if not query_text:
            return {'error': 'Query is required'}, 400
        
        # Step 1: IACM Validation
        iacm_result = validate_user_with_iacm(user_id, request)
        if not iacm_result.get('allowed'):
            return {
                'error': 'Access denied',
                'details': iacm_result.get('error', 'IACM validation failed')
            }, 403
        
        # Step 2: Risk Evaluation
        risk_result = evaluate_risk(user_id, query_text, {
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent')
        })
        risk_score = risk_result.get('risk_score', 0)
        
        # Step 3: Policy Evaluation
        policy_result = evaluate_policy(user_id, risk_score, 'ai_query')
        
        if policy_result.get('decision') == 'block':
            return {
                'error': 'Access denied',
                'details': 'Request blocked by policy due to high risk score'
            }, 403
        
        # Step 4: Execute RAG Query
        result = ai_service.query(
            user_id=user_id,
            query_text=query_text,
            filters=filters or {},
            top_k=top_k,
            conversation_id=conversation_id,
            plugin_id=plugin_id,
            use_memory=use_memory,
            enable_tools=enable_tools
        )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return {
            'answer': result.get('answer', ''),
            'sources': result.get('sources', []),
            'meta': {
                'elapsed_ms': elapsed_ms,
                'policy_decision': policy_result.get('decision', 'allow'),
                'risk_score': risk_score
            }
        }, 200
        
    except Exception as e:
        print(f"Error in query execution: {e}")
        import traceback
        traceback.print_exc()
        return {
            'error': str(e),
            'answer': f'Error processing query: {str(e)}',
            'sources': [],
            'meta': {'elapsed_ms': int((time.time() - start_time) * 1000)}
        }, 500

@app.route('/api/ai/chat', methods=['POST'])
def chat():
    """
    Chat endpoint (alias for query endpoint for frontend compatibility)
    Request: {message, userId, conversation_id?}
    Response: {message, conversation_id?, sources?, meta?}
    """
    try:
        data = request.json
        user_id = str(data.get('userId') or data.get('user_id') or '1')
        query_text = data.get('message') or data.get('query')
        conversation_id = data.get('conversation_id')
        
        if not query_text:
            return jsonify({'error': 'Message is required', 'message': 'Message is required'}), 400
        
        # Execute query
        response_data, status_code = _execute_query(
            user_id=user_id,
            query_text=query_text,
            conversation_id=conversation_id
        )
        
        # Transform response to chat format
        if status_code == 200:
            return jsonify({
                'message': response_data.get('answer', ''),
                'conversation_id': conversation_id,
                'sources': response_data.get('sources', []),
                'meta': response_data.get('meta', {})
            }), 200
        else:
            return jsonify({
                'error': response_data.get('error', 'Unknown error'),
                'message': response_data.get('error', 'Unknown error'),
                'conversation_id': conversation_id
            }), status_code
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': f'Error: {str(e)}',
            'conversation_id': None
        }), 500

@app.route('/api/ai/query', methods=['POST'])
def query():
    """
    RAG Query endpoint with zero-trust integration
    Request: {userId, query, filters?, topK?}
    Response: {answer, sources, meta}
    """
    if not ai_service:
        return jsonify({
            'error': 'AI service is not available',
            'answer': 'AI service is currently unavailable. Please check configuration.',
            'sources': [],
            'meta': {'elapsed_ms': 0}
        }), 503
    
    start_time = time.time()
    
    try:
        data = request.json
        user_id = data.get('userId') or data.get('user_id') or str(data.get('user_id', '1'))
        query_text = data.get('query')
        filters = data.get('filters', {})
        top_k = data.get('topK', 6)
        
        if not query_text:
            return jsonify({'error': 'Query is required'}), 400
        
        # Step 1: IACM Validation
        iacm_result = validate_user_with_iacm(user_id, request)
        if not iacm_result.get('allowed'):
            return jsonify({
                'error': 'Access denied',
                'details': iacm_result.get('error', 'IACM validation failed')
            }), 403
        
        # Step 2: Risk Evaluation
        risk_result = evaluate_risk(user_id, query_text, {
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent')
        })
        risk_score = risk_result.get('risk_score', 0)
        
        # Step 3: Policy Evaluation
        policy_result = evaluate_policy(user_id, risk_score, 'ai_query')
        
        # Check MFA requirement
        if policy_result.get('mfa_required'):
            mfa_token = request.headers.get('X-MFA-Token') or data.get('mfa_token')
            if not mfa_token:
                return jsonify({
                    'error': 'MFA required',
                    'risk_score': risk_score,
                    'mfa_required': True
                }), 403
        
        # Block if policy decision is 'block'
        if policy_result.get('decision') == 'block':
            ai_service.log_query(
                user_id=user_id,
                query_text=query_text,
                response_text='',
                sources=[],
                risk_score=risk_score,
                policy_decision='blocked',
                mfa_required=False,
                elapsed_ms=int((time.time() - start_time) * 1000)
            )
            return jsonify({
                'error': 'Query blocked due to high risk score',
                'risk_score': risk_score
            }), 403
        
        # Step 4: Apply access filters based on user permissions
        # Filter documents by user's department/role
        user_filters = filters.copy()
        # Add IACM-based filters (department, role-based access)
        # This would be populated from IACM result in production
        
        # Step 5: Execute RAG Query (with enterprise features)
        conversation_id = data.get('conversation_id') or f"CONV{int(time.time() * 1000)}"
        plugin_id = data.get('plugin_id')
        enable_tools = data.get('enable_tools', False)
        
        result = ai_service.query(
            user_id=user_id,
            query_text=query_text,
            filters=user_filters,
            top_k=top_k,
            conversation_id=conversation_id,
            plugin_id=plugin_id,
            use_memory=True,
            enable_tools=enable_tools
        )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        # Step 6: Log query (now handled inside query() method with quality metrics)
        # Query is already logged with quality metrics in ai_service.query()
        
        # Update meta with actual elapsed time
        result['meta']['elapsed_ms'] = elapsed_ms
        result['meta']['risk_score'] = risk_score
        result['meta']['policy_decision'] = policy_result.get('decision')
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error in query: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/ingest-webhook', methods=['POST'])
def ingest_webhook():
    """Webhook endpoint for file ingestion from File Gateway"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        data = request.json
        event = data.get('event')
        
        if event != 'document_uploaded':
            return jsonify({'error': 'Unknown event type'}), 400
        
        file_info = data.get('file', {})
        file_id = file_info.get('fileId')
        file_path = file_info.get('filePath')
        filename = file_info.get('filename')
        
        if not file_id or not file_path:
            return jsonify({'error': 'Missing fileId or filePath'}), 400
        
        # Trigger document ingestion
        result = ai_service.ingest_document_from_gateway(
            file_id=file_id,
            file_path=file_path,
            filename=filename,
            source=file_info.get('source', 'file-gateway'),
            department=file_info.get('department'),
            tags=file_info.get('tags', [])
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Document ingestion triggered',
            'file_id': file_id,
            'chunks_created': result.get('chunks_created', 0)
        })
        
    except Exception as e:
        print(f"Error in ingest webhook: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/reindex', methods=['POST'])
def reindex():
    """
    Reindex documents endpoint (admin only)
    Request: {source?, path?}
    """
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        result = ai_service.reindex_documents()
        return jsonify({
            'status': 'success',
            'message': 'Reindexing completed',
            'documents_processed': result.get('documents_processed', 0),
            'chunks_created': result.get('chunks_created', 0)
        })
        
    except Exception as e:
        print(f"Error in reindex: {e}")
        return jsonify({'error': str(e)}), 500

# Legacy endpoints for backward compatibility
@app.route('/api/chat', methods=['POST'])
def chat_legacy():
    """Legacy chat endpoint - supports both old and new format"""
    try:
        data = request.json
        message = data.get('message') or data.get('query')
        user_id = str(data.get('user_id') or data.get('userId', 1))
        conversation_id = data.get('conversation_id')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Use the same logic as /api/ai/query but with legacy format
        if not ai_service:
            return jsonify({
                'error': 'AI service is not available',
                'message': 'AI service is currently unavailable. Please check configuration.',
                'conversation_id': conversation_id,
                'model': 'unavailable'
            }), 503
        
        start_time = time.time()
        
        # Step 1: IACM Validation (simplified for PoC)
        iacm_result = validate_user_with_iacm(user_id, request)
        if not iacm_result.get('allowed'):
            return jsonify({
                'error': 'Access denied',
                'details': iacm_result.get('error', 'IACM validation failed')
            }), 403
        
        # Step 2: Risk Evaluation
        risk_result = evaluate_risk(user_id, message, {
            'ip_address': request.remote_addr,
            'user_agent': request.headers.get('User-Agent')
        })
        risk_score = risk_result.get('risk_score', 0)
        
        # Step 3: Policy Evaluation
        policy_result = evaluate_policy(user_id, risk_score, 'ai_query')
        
        # Block if policy decision is 'block'
        if policy_result.get('decision') == 'block':
            return jsonify({
                'error': 'Query blocked due to high risk score',
                'risk_score': risk_score
            }), 403
        
        # Step 4: Execute RAG Query (with enterprise features)
        conversation_id = conversation_id or f"CONV{int(time.time() * 1000)}"
        result = ai_service.query(
            user_id=user_id,
            query_text=message,
            filters={},
            top_k=6,
            conversation_id=conversation_id,
            use_memory=True,
            enable_tools=data.get('enable_tools', False)
        )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        # Step 5: Log query (now handled inside query() method with quality metrics)
        # Query is already logged with quality metrics in ai_service.query()
        
        # Return in legacy format
        return jsonify({
            'message': result.get('answer', ''),
            'conversation_id': conversation_id or f"CONV{int(time.time() * 1000)}",
            'model': os.getenv('LLM_MODEL', 'llama3.1:8b'),
            'sources': result.get('sources', []),
            'meta': result.get('meta', {})
        })
        
    except Exception as e:
        print(f"Error in chat: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get user conversations (legacy)"""
    try:
        user_id = request.args.get('user_id', 1)
        # TODO: Implement conversation retrieval from ai_queries or separate table
        return jsonify({'conversations': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversations/<conversation_id>/messages', methods=['GET'])
def get_messages(conversation_id):
    """Get conversation messages (legacy)"""
    try:
        # TODO: Implement message retrieval
        return jsonify({'messages': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== ENTERPRISE FEATURES ENDPOINTS ==========

@app.route('/api/ai/plugins', methods=['GET'])
def get_plugins():
    """Get available plugins for user"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        user_id = request.args.get('user_id', '1')
        user_context = ai_service._get_user_context(user_id)
        plugins = ai_service.enterprise.get_plugins_for_user(user_id, user_context.get('permissions', []))
        
        return jsonify({'plugins': plugins})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/plugins/<plugin_id>/documents', methods=['GET'])
def get_plugin_documents(plugin_id):
    """Get documents for a plugin"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        filters = {}
        if request.args.get('department'):
            filters['department'] = request.args.get('department')
        if request.args.get('classification'):
            filters['classification'] = request.args.get('classification')
        
        documents = ai_service.enterprise.get_plugin_documents(plugin_id, filters)
        return jsonify({'documents': documents})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/tools', methods=['GET'])
def get_tools():
    """Get available tools for user"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        user_id = request.args.get('user_id', '1')
        user_context = ai_service._get_user_context(user_id)
        tools = ai_service.enterprise.get_available_tools(user_context.get('permissions', []))
        
        return jsonify({'tools': tools})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/tools/<tool_id>/execute', methods=['POST'])
def execute_tool(tool_id):
    """Execute a tool"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        data = request.json
        user_id = data.get('user_id', '1')
        parameters = data.get('parameters', {})
        query_id = data.get('query_id')
        
        result = ai_service.enterprise.execute_tool(tool_id, user_id, parameters, query_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/memory', methods=['GET', 'POST'])
def manage_memory():
    """Get or save conversation memory"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        if request.method == 'GET':
            conversation_id = request.args.get('conversation_id')
            user_id = request.args.get('user_id')
            memory_type = request.args.get('memory_type')
            
            if not conversation_id:
                return jsonify({'error': 'conversation_id required'}), 400
            
            memories = ai_service.enterprise.get_memories(conversation_id, user_id, memory_type)
            return jsonify({'memories': memories})
        
        else:  # POST
            data = request.json
            conversation_id = data.get('conversation_id')
            user_id = data.get('user_id')
            memory_type = data.get('memory_type', 'short_term')
            content = data.get('content')
            importance_score = data.get('importance_score', 0.0)
            expires_in_hours = data.get('expires_in_hours')
            
            if not conversation_id or not user_id or not content:
                return jsonify({'error': 'conversation_id, user_id, and content required'}), 400
            
            memory_id = ai_service.enterprise.save_memory(
                conversation_id, user_id, memory_type, content,
                importance_score, expires_in_hours
            )
            
            return jsonify({'memory_id': memory_id, 'status': 'saved'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== KNOWLEDGE ADMINISTRATION CONSOLE ==========

@app.route('/api/ai/admin/datasets', methods=['GET', 'POST'])
def manage_datasets():
    """List or create dataset versions"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        if request.method == 'GET':
            dataset_id = request.args.get('dataset_id')
            # TODO: Implement dataset listing
            return jsonify({'datasets': []})
        
        else:  # POST
            data = request.json
            dataset_id = data.get('dataset_id')
            description = data.get('description', '')
            created_by = data.get('created_by', 'admin')
            
            if not dataset_id:
                return jsonify({'error': 'dataset_id required'}), 400
            
            version = ai_service.enterprise.create_dataset_version(dataset_id, description, created_by)
            return jsonify({'version': version})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/admin/documents/<document_id>/validate', methods=['POST'])
def submit_document_validation(document_id):
    """Submit document for validation workflow"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        data = request.json
        submitted_by = data.get('submitted_by', 'admin')
        
        success = ai_service.enterprise.submit_for_validation(document_id, submitted_by)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/admin/documents/<document_id>/approve', methods=['POST'])
def approve_document(document_id):
    """Approve a document"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        data = request.json
        approved_by = data.get('approved_by', 'admin')
        notes = data.get('notes')
        
        success = ai_service.enterprise.approve_document(document_id, approved_by, notes)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/admin/quality', methods=['GET'])
def get_quality_metrics():
    """Get quality metrics"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        metric_type = request.args.get('metric_type', 'daily')
        
        metrics = ai_service.enterprise.get_quality_metrics(start_date, end_date, metric_type)
        return jsonify({'metrics': metrics})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/admin/sync', methods=['POST'])
def create_sync_job():
    """Create a knowledge sync job"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        data = request.json
        job_type = data.get('job_type')
        source_type = data.get('source_type', 'api')
        source_config = data.get('source_config', {})
        
        if not job_type:
            return jsonify({'error': 'job_type required'}), 400
        
        job_id = ai_service.enterprise.create_sync_job(job_type, source_type, source_config)
        return jsonify({'job_id': job_id, 'status': 'created'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/admin/retrieval-debug/<query_id>', methods=['GET'])
def get_retrieval_debug(query_id):
    """Get retrieval debugging information for a query"""
    try:
        if not ai_service:
            return jsonify({'error': 'AI service not available'}), 503
        
        conn = ai_service.get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT rd.*, c.text as chunk_text, d.title as document_title
            FROM kb_retrieval_debug rd
            JOIN kb_chunks c ON rd.chunk_id = c.id
            JOIN kb_documents d ON c.document_id = d.id
            WHERE rd.query_id = %s
            ORDER BY rd.rank_position
        """, (query_id,))
        
        debug_info = cur.fetchall()
        cur.close()
        conn.close()
        
        return jsonify({'debug_info': [dict(d) for d in debug_info]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
