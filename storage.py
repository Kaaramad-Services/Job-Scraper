"""
Storage module for tracking seen jobs
"""

import json
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class JobStorage:
    def __init__(self, storage_file="seen_jobs.json"):
        self.storage_file = storage_file
        self.seen_jobs = self.load_seen_jobs()
    
    def load_seen_jobs(self):
        """Load seen jobs from file"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                    # Convert old format if needed
                    if isinstance(data, list):
                        return {job_id: datetime.now().isoformat() for job_id in data}
                    return data
            except Exception as e:
                logger.error(f"Error loading storage file: {e}")
                return {}
        return {}
    
    def save_seen_jobs(self):
        """Save seen jobs to file"""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self.seen_jobs, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving storage file: {e}")
    
    def job_exists(self, job_id):
        """Check if job has been seen before"""
        return job_id in self.seen_jobs
    
    def save_job(self, job_id):
        """Mark job as seen"""
        self.seen_jobs[job_id] = datetime.now().isoformat()
        self.save_seen_jobs()
    
    def cleanup_old_entries(self, hours=24):
        """Remove entries older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Convert cutoff to string for comparison
        cutoff_str = cutoff_time.isoformat()
        
        # Filter out old entries
        initial_count = len(self.seen_jobs)
        self.seen_jobs = {
            job_id: timestamp 
            for job_id, timestamp in self.seen_jobs.items() 
            if timestamp > cutoff_str
        }
        
        removed = initial_count - len(self.seen_jobs)
        if removed > 0:
            logger.info(f"Cleaned up {removed} old job entries")
            self.save_seen_jobs()