"""Memory management for UI components"""
import gc
import weakref
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class MemoryManager:
    def __init__(self):
        self._widget_refs: Dict[str, List[weakref.ref]] = {}
        self._cleanup_callbacks: List = []
    
    def register_widget(self, widget, category: str = "default"):
        """Register widget for memory tracking"""
        if category not in self._widget_refs:
            self._widget_refs[category] = []
        
        def cleanup_callback(ref):
            self._widget_refs[category].remove(ref)
        
        widget_ref = weakref.ref(widget, cleanup_callback)
        self._widget_refs[category].append(widget_ref)
    
    def cleanup_category(self, category: str):
        """Force cleanup of widget category"""
        if category in self._widget_refs:
            for widget_ref in self._widget_refs[category][:]:
                widget = widget_ref()
                if widget:
                    try:
                        widget.destroy()
                    except:
                        pass
            self._widget_refs[category].clear()
    
    def force_gc(self):
        """Force garbage collection"""
        gc.collect()
        logger.debug(f"Memory cleanup: {len(gc.get_objects())} objects")
    
    def get_memory_stats(self):
        """Get memory usage statistics"""
        stats = {}
        for category, refs in self._widget_refs.items():
            alive_count = sum(1 for ref in refs if ref() is not None)
            stats[category] = {
                "total": len(refs),
                "alive": alive_count,
                "dead": len(refs) - alive_count
            }
        return stats

# Global memory manager
memory_manager = MemoryManager()

def cleanup_ui_memory():
    """Cleanup UI memory"""
    memory_manager.cleanup_category("temp")
    memory_manager.force_gc()

def register_temp_widget(widget):
    """Register temporary widget"""
    memory_manager.register_widget(widget, "temp")