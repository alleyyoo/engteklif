# services/background_tasks.py
import threading
import queue
import time
from typing import Dict, Any, Callable
import uuid
from datetime import datetime

class BackgroundTaskManager:
    """Arka plan görevlerini yöneten singleton servis"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BackgroundTaskManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.task_queue = queue.Queue()
        self.active_tasks = {}
        self.completed_tasks = {}
        self.failed_tasks = {}
        self.max_workers = 3
        self.workers = []
        self._start_workers()
        
        print("[TASK-MANAGER] ✅ Background Task Manager başlatıldı")
    
    def _start_workers(self):
        """Worker thread'lerini başlat"""
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, daemon=True)
            worker.start()
            self.workers.append(worker)
            print(f"[TASK-MANAGER] 🔧 Worker {i+1} başlatıldı")
    
    def _worker(self):
        """Worker thread - kuyruktan görevleri al ve çalıştır"""
        while True:
            try:
                task = self.task_queue.get(timeout=1)
                if task is None:
                    break
                    
                task_id = task['id']
                print(f"[TASK-WORKER] 🏃 Task başlatılıyor: {task_id} - {task['name']}")
                
                # Task'ı aktif olarak işaretle
                self.active_tasks[task_id] = {
                    'status': 'running',
                    'started_at': datetime.utcnow(),
                    'name': task['name']
                }
                
                try:
                    # Task fonksiyonunu çalıştır
                    result = task['func'](*task['args'], **task['kwargs'])
                    
                    # Başarılı olarak işaretle
                    self.completed_tasks[task_id] = {
                        'status': 'completed',
                        'completed_at': datetime.utcnow(),
                        'result': result,
                        'name': task['name']
                    }
                    
                    # Callback varsa çalıştır
                    if task.get('callback'):
                        task['callback'](result)
                    
                    print(f"[TASK-WORKER] ✅ Task tamamlandı: {task_id}")
                    
                except Exception as e:
                    # Hatalı olarak işaretle
                    self.failed_tasks[task_id] = {
                        'status': 'failed',
                        'failed_at': datetime.utcnow(),
                        'error': str(e),
                        'name': task['name']
                    }
                    print(f"[TASK-WORKER] ❌ Task başarısız: {task_id} - {str(e)}")
                
                finally:
                    # Aktif listesinden kaldır
                    if task_id in self.active_tasks:
                        del self.active_tasks[task_id]
                    
                    self.task_queue.task_done()
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[TASK-WORKER] ❌ Worker hatası: {str(e)}")
    
    def add_task(
        self, 
        func: Callable, 
        args: tuple = (), 
        kwargs: dict = None, 
        name: str = "Unknown",
        callback: Callable = None
    ) -> str:
        """Yeni görev ekle"""
        task_id = str(uuid.uuid4())
        
        task = {
            'id': task_id,
            'func': func,
            'args': args,
            'kwargs': kwargs or {},
            'name': name,
            'callback': callback,
            'created_at': datetime.utcnow()
        }
        
        self.task_queue.put(task)
        print(f"[TASK-MANAGER] 📥 Task kuyruğa eklendi: {task_id} - {name}")
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Görev durumunu getir"""
        if task_id in self.active_tasks:
            return {'status': 'running', **self.active_tasks[task_id]}
        elif task_id in self.completed_tasks:
            return {'status': 'completed', **self.completed_tasks[task_id]}
        elif task_id in self.failed_tasks:
            return {'status': 'failed', **self.failed_tasks[task_id]}
        else:
            return {'status': 'not_found'}
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Kuyruk durumunu getir"""
        return {
            'queue_size': self.task_queue.qsize(),
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'failed_tasks': len(self.failed_tasks),
            'workers': len(self.workers)
        }

# Singleton instance
task_manager = BackgroundTaskManager()