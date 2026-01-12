"""
Mem0 Self-Hosted Assistant Application
A personal/business assistant with persistent memory using fully self-hosted infrastructure
"""

from mem0 import Memory
from config import get_mem0_config, get_config
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from typing import List, Dict, Optional
import sys


class Mem0Assistant:
    """Self-hosted AI Assistant with Mem0 memory"""
    
    def __init__(self, user_id: Optional[str] = None, use_graph_store: bool = True):
        """
        Initialize the assistant with Mem0 memory
        
        Args:
            user_id: Unique identifier for the user
            use_graph_store: Whether to use Neo4j graph store
        """
        self.console = Console()
        self.config = get_config()
        self.user_id = user_id or self.config.default_user_id
        self.use_graph_store = use_graph_store
        
        # Initialize Mem0
        self.console.print("\n[cyan]Initializing Mem0 memory layer...[/cyan]")
        try:
            mem0_config = get_mem0_config(use_graph_store=use_graph_store)
            self.memory = Memory.from_config(mem0_config)
            self.console.print("[green]✓ Mem0 initialized successfully![/green]\n")
        except Exception as e:
            self.console.print(f"[red]✗ Failed to initialize Mem0: {e}[/red]")
            self.console.print("\n[yellow]Make sure all services are running:[/yellow]")
            self.console.print("  docker-compose up -d")
            sys.exit(1)
    
    def add_memory(self, text: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Add a new memory
        
        Args:
            text: The text content to remember
            metadata: Optional metadata dictionary
        
        Returns:
            Result dictionary from Mem0
        """
        try:
            result = self.memory.add(text, user_id=self.user_id, metadata=metadata)
            return result
        except Exception as e:
            self.console.print(f"[red]Error adding memory: {e}[/red]")
            return {"error": str(e)}
    
    def search_memories(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search for relevant memories
        
        Args:
            query: Search query
            limit: Maximum number of results
        
        Returns:
            List of relevant memories
        """
        try:
            results = self.memory.search(query, user_id=self.user_id, limit=limit)
            return results
        except Exception as e:
            self.console.print(f"[red]Error searching memories: {e}[/red]")
            return []
    
    def get_all_memories(self) -> List[Dict]:
        """
        Get all memories for the current user
        
        Returns:
            List of all memories
        """
        try:
            memories = self.memory.get_all(user_id=self.user_id)
            return memories
        except Exception as e:
            self.console.print(f"[red]Error retrieving memories: {e}[/red]")
            return []
    
    def update_memory(self, memory_id: str, text: str) -> Dict:
        """
        Update an existing memory
        
        Args:
            memory_id: ID of the memory to update
            text: New text content
        
        Returns:
            Result dictionary
        """
        try:
            result = self.memory.update(memory_id=memory_id, data=text)
            return result
        except Exception as e:
            self.console.print(f"[red]Error updating memory: {e}[/red]")
            return {"error": str(e)}
    
    def delete_memory(self, memory_id: str) -> Dict:
        """
        Delete a memory
        
        Args:
            memory_id: ID of the memory to delete
        
        Returns:
            Result dictionary
        """
        try:
            result = self.memory.delete(memory_id=memory_id)
            return result
        except Exception as e:
            self.console.print(f"[red]Error deleting memory: {e}[/red]")
            return {"error": str(e)}
    
    def delete_all_memories(self) -> Dict:
        """
        Delete all memories for the current user
        
        Returns:
            Result dictionary
        """
        try:
            result = self.memory.delete_all(user_id=self.user_id)
            return result
        except Exception as e:
            self.console.print(f"[red]Error deleting all memories: {e}[/red]")
            return {"error": str(e)}
    
    def display_memories(self, memories: List[Dict]):
        """Display memories in a nice format"""
        if not memories:
            self.console.print("[yellow]No memories found.[/yellow]")
            return
        
        self.console.print(f"\n[cyan]Found {len(memories)} memories:[/cyan]\n")
        for idx, mem in enumerate(memories, 1):
            memory_text = mem.get('memory', mem.get('text', 'N/A'))
            memory_id = mem.get('id', 'N/A')
            score = mem.get('score', mem.get('relevance', 'N/A'))
            
            panel_content = f"**Memory:** {memory_text}\n\n"
            panel_content += f"**ID:** `{memory_id}`"
            
            if score != 'N/A':
                panel_content += f" | **Score:** {score:.3f}"
            
            self.console.print(Panel(
                panel_content,
                title=f"Memory {idx}",
                border_style="cyan"
            ))
    
    def interactive_mode(self):
        """Run the assistant in interactive mode"""
        self.console.print(Panel.fit(
            "[bold cyan]Mem0 Self-Hosted Assistant[/bold cyan]\n"
            f"User: {self.user_id}\n"
            f"Graph Memory: {'Enabled' if self.use_graph_store else 'Disabled'}",
            border_style="cyan"
        ))
        
        self.show_help()
        
        while True:
            try:
                command = Prompt.ask("\n[bold green]Command[/bold green]", default="help")
                
                if command in ["exit", "quit", "q"]:
                    self.console.print("[cyan]Goodbye![/cyan]")
                    break
                
                elif command == "help" or command == "h":
                    self.show_help()
                
                elif command == "add" or command == "a":
                    text = Prompt.ask("[yellow]Enter memory text[/yellow]")
                    result = self.add_memory(text)
                    if "error" not in result:
                        self.console.print("[green]✓ Memory added successfully![/green]")
                    
                elif command == "search" or command == "s":
                    query = Prompt.ask("[yellow]Enter search query[/yellow]")
                    results = self.search_memories(query)
                    self.display_memories(results)
                
                elif command == "list" or command == "l":
                    memories = self.get_all_memories()
                    self.display_memories(memories)
                
                elif command == "delete" or command == "d":
                    memory_id = Prompt.ask("[yellow]Enter memory ID to delete[/yellow]")
                    if Confirm.ask(f"Delete memory {memory_id}?"):
                        result = self.delete_memory(memory_id)
                        if "error" not in result:
                            self.console.print("[green]✓ Memory deleted![/green]")
                
                elif command == "clear" or command == "c":
                    if Confirm.ask("[red]Delete ALL memories? This cannot be undone![/red]"):
                        result = self.delete_all_memories()
                        if "error" not in result:
                            self.console.print("[green]✓ All memories cleared![/green]")
                
                elif command == "user" or command == "u":
                    new_user = Prompt.ask("[yellow]Enter user ID[/yellow]", default=self.user_id)
                    self.user_id = new_user
                    self.console.print(f"[green]✓ Switched to user: {self.user_id}[/green]")
                
                elif command == "info" or command == "i":
                    self.show_info()
                
                else:
                    self.console.print(f"[red]Unknown command: {command}[/red]")
                    self.console.print("Type 'help' for available commands")
            
            except KeyboardInterrupt:
                self.console.print("\n[cyan]Use 'exit' to quit[/cyan]")
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
    
    def show_help(self):
        """Display help information"""
        help_text = """
**Available Commands:**

- `add` (a)     - Add a new memory
- `search` (s)  - Search memories by query
- `list` (l)    - List all memories
- `delete` (d)  - Delete a specific memory
- `clear` (c)   - Delete all memories
- `user` (u)    - Switch user
- `info` (i)    - Show system information
- `help` (h)    - Show this help
- `exit` (q)    - Exit the application
        """
        self.console.print(Panel(help_text, title="Help", border_style="blue"))
    
    def show_info(self):
        """Display system information"""
        memories = self.get_all_memories()
        info_text = f"""
**Current User:** `{self.user_id}`
**Total Memories:** {len(memories)}
**Graph Store:** {'Enabled (Neo4j)' if self.use_graph_store else 'Disabled'}

**Services:**
- Qdrant: {self.config.qdrant_host}:{self.config.qdrant_port}
- Ollama: {self.config.ollama_base_url}
- Neo4j: {self.config.neo4j_url if self.use_graph_store else 'N/A'}

**Models:**
- LLM: {self.config.ollama_llm_model}
- Embeddings: {self.config.ollama_embedding_model}
        """
        self.console.print(Panel(info_text, title="System Info", border_style="cyan"))


def main():
    """Main entry point"""
    console = Console()
    
    # Check if user wants to disable graph store
    use_graph = True
    if len(sys.argv) > 1 and sys.argv[1] == "--no-graph":
        use_graph = False
        console.print("[yellow]Running without graph store (Neo4j disabled)[/yellow]")
    
    # Get user ID from command line or use default
    user_id = None
    if len(sys.argv) > 2:
        user_id = sys.argv[2]
    elif len(sys.argv) > 1 and sys.argv[1] != "--no-graph":
        user_id = sys.argv[1]
    
    try:
        assistant = Mem0Assistant(user_id=user_id, use_graph_store=use_graph)
        assistant.interactive_mode()
    except KeyboardInterrupt:
        console.print("\n[cyan]Goodbye![/cyan]")
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()

