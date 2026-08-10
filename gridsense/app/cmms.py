import abc
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from .schema import WorkItem

class CMMSProvider(abc.ABC):
    """Abstract base class for a Computerized Maintenance Management System."""
    
    @abc.abstractmethod
    def dispatch_workorder(self, item: WorkItem) -> bool:
        """
        Send a work order to the CMMS.
        Returns True if successful, False otherwise.
        """
        pass

class FileCMMSProvider(CMMSProvider):
    """Logs work orders to a local JSONL file (Prototype behavior)."""
    
    def __init__(self, log_path: str = "gridsense_workorders.jsonl"):
        self.log_path = log_path

    def dispatch_workorder(self, item: WorkItem) -> bool:
        rec = item.to_dict()
        rec["_logged_at"] = datetime.now(timezone.utc).isoformat()
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return True
        except Exception as e:
            logging.error(f"Failed to write to FileCMMS: {e}")
            return False

class MockMaximoCMMS(CMMSProvider):
    """Mocks an enterprise REST API integration to a real CMMS like Maximo."""
    
    def __init__(self, api_url: str = "https://api.example.com/maximo/v1/workorders"):
        self.api_url = api_url

    def dispatch_workorder(self, item: WorkItem) -> bool:
        # In a real integration, this would use the `requests` library
        # response = requests.post(self.api_url, json=item.to_dict(), headers=self.auth_headers)
        # return response.status_code == 201
        
        logging.info(f"[MockMaximo] Successfully dispatched WO {item.work_id} to {self.api_url}")
        return True
