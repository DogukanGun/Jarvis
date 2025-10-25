package cmd

import (
	"context"
	"fmt"
	"strings"

	"github.com/chzyer/readline"
	"github.com/spf13/cobra"
	"jarvis/agent"
)

var chatCmd = &cobra.Command{
	Use:   "chat",
	Short: "Start interactive chat mode with Jarvis agent",
	Long: `Start an interactive chat session with your Jarvis AI agent.
You can ask questions, request code execution, file operations, and more.
Type 'exit' or press Ctrl+C to quit.`,
	Example: `  # Start interactive chat
  jarvis chat
  
  # Start chat with specific model
  jarvis chat --model gpt-4o
  
  # Start chat with verbose output
  jarvis chat --verbose`,
	RunE: runChat,
}

func runChat(cmd *cobra.Command, args []string) error {
	config, err := getAgentConfig()
	if err != nil {
		return fmt.Errorf("configuration error: %v", err)
	}

	if verbose {
		fmt.Println("Starting Jarvis AI Agent in interactive mode...")
		fmt.Printf("Model: %s\n", config["openai_model"])
		fmt.Printf("User ID: %s\n", config["user_id"])
		fmt.Println()
	}

	jarvisAgent, err := agent.NewJarvisAgent(agent.AgentConfig{
		UserID:      config["user_id"],
		OpenAIModel: config["openai_model"],
		OpenAIKey:   config["openai_key"],
	})
	if err != nil {
		return fmt.Errorf("failed to initialize agent: %v", err)
	}

	rl, err := readline.NewEx(&readline.Config{
		Prompt:          "jarvis> ",
		HistoryFile:     "/tmp/jarvis_history",
		AutoComplete:    createCompleter(jarvisAgent),
		InterruptPrompt: "^C",
		EOFPrompt:       "exit",
	})
	if err != nil {
		return fmt.Errorf("failed to initialize readline: %v", err)
	}
	defer rl.Close()

	fmt.Println("Welcome to Jarvis AI Agent!")
	fmt.Println("Type your questions or commands. Type 'help' for available commands, 'exit' to quit.")
	fmt.Println()

	ctx := context.Background()

	for {
		line, err := rl.Readline()
		if err != nil {
			if err.Error() == "Interrupt" {
				fmt.Println("\nGoodbye!")
				return nil
			}
			return fmt.Errorf("readline error: %v", err)
		}

		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		if line == "exit" || line == "quit" {
			fmt.Println("Goodbye!")
			return nil
		}

		if line == "help" {
			printChatHelp()
			continue
		}

		if line == "capabilities" {
			printCapabilities(jarvisAgent)
			continue
		}

		if line == "tools" {
			printTools(jarvisAgent)
			continue
		}

		if line == "clear" {
			fmt.Print("\033[2J\033[H")
			continue
		}

		response, err := jarvisAgent.ProcessMessage(ctx, line)
		if err != nil {
			fmt.Printf("Error: %v\n\n", err)
			continue
		}

		fmt.Printf("Jarvis: %s\n\n", response)
	}
}

func createCompleter(agent *agent.JarvisAgent) readline.AutoCompleter {
	return readline.NewPrefixCompleter(
		readline.PcItem("help"),
		readline.PcItem("capabilities"),
		readline.PcItem("tools"),
		readline.PcItem("clear"),
		readline.PcItem("exit"),
		readline.PcItem("quit"),
		readline.PcItem("read file"),
		readline.PcItem("write file"),
		readline.PcItem("list files"),
		readline.PcItem("run code"),
		readline.PcItem("execute"),
		readline.PcItem("install package"),
		readline.PcItem("git commit"),
		readline.PcItem("create pr"),
		readline.PcItem("search wikipedia"),
		readline.PcItem("scrape web"),
	)
}

func printChatHelp() {
	fmt.Println("Available commands:")
	fmt.Println("  help         - Show this help message")
	fmt.Println("  capabilities - Show agent capabilities")
	fmt.Println("  tools        - Show available tools")
	fmt.Println("  clear        - Clear the screen")
	fmt.Println("  exit/quit    - Exit the chat session")
	fmt.Println()
	fmt.Println("You can also ask natural language questions like:")
	fmt.Println("  'Read the contents of main.go'")
	fmt.Println("  'Run this Python code: print(\"Hello World\")'")
	fmt.Println("  'Install the requests package'")
	fmt.Println("  'Search Wikipedia for artificial intelligence'")
	fmt.Println()
}

func printCapabilities(agent *agent.JarvisAgent) {
	capabilities := agent.GetCapabilities()
	fmt.Println("Jarvis Agent Capabilities:")
	fmt.Println()

	for category, items := range capabilities {
		fmt.Printf("%s:\n", category)
		for _, item := range items {
			fmt.Printf("  • %s\n", item)
		}
		fmt.Println()
	}
}

func printTools(agent *agent.JarvisAgent) {
	tools := agent.GetAvailableTools()
	fmt.Println("Available Tools:")
	fmt.Println()

	for _, tool := range tools {
		fmt.Printf("  • %s\n", tool)
	}
	fmt.Println()
}
