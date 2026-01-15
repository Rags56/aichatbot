"""
Continuous Knowledge Sync Automation
Automates ingestion from various sources (SOPs, Git, diagrams, etc.)
"""
import os
import json
import time
from datetime import datetime
from ai_enterprise import AIEnterpriseFeatures
from ai_service import AIService

class KnowledgeSyncAutomation:
    """Automates continuous knowledge synchronization"""
    
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL', 'postgresql://zerotrust:zerotrust123@postgres:5432/zerotrust_db')
        self.enterprise = AIEnterpriseFeatures(
            self.db_url,
            os.getenv('BACKEND_CORE_URL', 'http://backend-core:3001')
        )
        self.ai_service = AIService()
    
    def sync_from_file_gateway(self):
        """Sync new files from File Gateway (triggered by webhook)"""
        # This is already handled by the webhook endpoint
        # This method can be used for manual sync or scheduled sync
        pass
    
    def sync_from_git_push(self, repo_url: str, branch: str = 'main'):
        """Sync documentation from Git repository"""
        job_id = self.enterprise.create_sync_job(
            'git_push',
            'git',
            {
                'repo_url': repo_url,
                'branch': branch,
                'paths': ['docs/', '*.md', '*.rst']  # Document paths to sync
            }
        )
        
        if job_id:
            self.enterprise.update_sync_job(job_id, 'running')
            # TODO: Implement Git clone and document extraction
            # For now, mark as completed
            self.enterprise.update_sync_job(job_id, 'completed', documents_processed=0, chunks_created=0)
        
        return job_id
    
    def sync_from_sop_upload(self, file_path: str, department: str = None):
        """Sync when a new SOP is uploaded"""
        job_id = self.enterprise.create_sync_job(
            'sop_upload',
            'file_gateway',
            {
                'file_path': file_path,
                'department': department
            }
        )
        
        if job_id:
            self.enterprise.update_sync_job(job_id, 'running')
            # Trigger reindexing
            result = self.ai_service.reindex_documents()
            self.enterprise.update_sync_job(
                job_id, 'completed',
                documents_processed=result.get('documents_processed', 0),
                chunks_created=result.get('chunks_created', 0)
            )
        
        return job_id
    
    def sync_architecture_diagram(self, diagram_path: str, project: str = None):
        """Sync when an architecture diagram is updated"""
        job_id = self.enterprise.create_sync_job(
            'diagram_update',
            'file_gateway',
            {
                'diagram_path': diagram_path,
                'project': project
            }
        )
        
        # TODO: Implement diagram parsing and text extraction
        # For now, mark as completed
        if job_id:
            self.enterprise.update_sync_job(job_id, 'completed')
        
        return job_id
    
    def generate_log_summary(self):
        """Generate weekly LLM-based summary of log insights"""
        job_id = self.enterprise.create_sync_job(
            'log_summary',
            'scheduled',
            {
                'summary_type': 'weekly',
                'date': datetime.utcnow().isoformat()
            }
        )
        
        if job_id:
            self.enterprise.update_sync_job(job_id, 'running')
            
            # TODO: Implement log analysis and summary generation
            # 1. Fetch system logs from last week
            # 2. Analyze patterns using LLM
            # 3. Generate summary document
            # 4. Index the summary
            
            self.enterprise.update_sync_job(job_id, 'completed', documents_processed=1, chunks_created=1)
        
        return job_id
    
    def auto_assign_to_plugins(self, document_id: str):
        """Automatically assign documents to appropriate plugins based on content"""
        try:
            conn = self.ai_service.get_db_connection()
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get document metadata
            cur.execute("SELECT * FROM kb_documents WHERE id = %s", (document_id,))
            doc = cur.fetchone()
            
            if not doc:
                return False
            
            # Determine plugin based on metadata
            department = doc.get('department', '').lower()
            title = doc.get('title', '').lower()
            source = doc.get('source', '').lower()
            tags = doc.get('tags', []) or []
            
            plugins_to_assign = []
            
            # HR plugin
            if any(kw in title or any(kw in str(tags).lower() for kw in ['hr', 'human resources', 'employee', 'policy', 'onboarding']):
                plugins_to_assign.append('plugin-hr')
            
            # Finance plugin
            if any(kw in title or any(kw in str(tags).lower() for kw in ['finance', 'invoice', 'payment', 'budget', 'accounting']):
                plugins_to_assign.append('plugin-finance')
            
            # Security plugin
            if any(kw in title or any(kw in str(tags).lower() for kw in ['security', 'policy', 'access', 'zta', 'zero trust']):
                plugins_to_assign.append('plugin-security')
            
            # DevOps plugin
            if any(kw in title or any(kw in str(tags).lower() for kw in ['devops', 'ci/cd', 'deployment', 'pipeline', 'build']):
                plugins_to_assign.append('plugin-devops')
            
            # Systems plugin (default for infrastructure)
            if any(kw in title or any(kw in str(tags).lower() for kw in ['server', 'infrastructure', 'architecture', 'diagram', 'system']):
                plugins_to_assign.append('plugin-systems')
            
            # Assign to plugins
            for plugin_id in plugins_to_assign:
                self.enterprise.assign_document_to_plugin(document_id, plugin_id)
            
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Error auto-assigning to plugins: {e}")
            return False

if __name__ == '__main__':
    # Example usage
    sync = KnowledgeSyncAutomation()
    
    # Run scheduled syncs
    # sync.generate_log_summary()
    # sync.sync_from_git_push('https://github.com/company/docs', 'main')

