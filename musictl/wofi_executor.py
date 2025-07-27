import subprocess
from typing import List, Optional

class WofiExecutor:
    """Handles direct wofi execution with proper space handling."""
    
    def call_wofi(self, items: List[str], prompt: str) -> Optional[str]:
        """Call wofi directly with proper handling of spaces."""
        if not items:
            return None
        
        try:
            # Join items with newlines and pass via stdin
            items_input = '\n'.join(items)
            
            result = subprocess.run(
                ['wofi', '--dmenu', '--prompt', prompt],
                input=items_input,
                text=True,
                capture_output=True
            )
            
            if result.returncode == 0:
                selected = result.stdout.strip()
                return selected if selected in items else None
            else:
                print(f"wofi error: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Error running wofi: {e}")
            return None
