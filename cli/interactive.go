package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

// startInteractiveSession starts an interactive session like Claude Code
func startInteractiveSession() error {
	fmt.Println("Jarvis AI Assistant")
	fmt.Println("===================")
	fmt.Println()
	fmt.Println("Welcome! I'm your AI assistant. Ask me anything or give me tasks to complete.")
	fmt.Println("Type your message and press Enter. Use '/stop' to exit the session.")
	fmt.Println()

	reader := bufio.NewReader(os.Stdin)

	for {
		// Show prompt
		fmt.Print("You: ")

		// Read user input
		input, err := reader.ReadString('\n')
		if err != nil {
			return fmt.Errorf("error reading input: %w", err)
		}

		// Clean up input
		input = strings.TrimSpace(input)

		// Handle empty input
		if input == "" {
			continue
		}

		// Handle stop command
		if input == "/stop" || input == "/exit" || input == "/quit" {
			fmt.Println("\nGoodbye! Thanks for using Jarvis.")
			return nil
		}

		// Handle help command
		if input == "/help" {
			showInteractiveHelp()
			continue
		}

		// Handle config commands in interactive mode
		if strings.HasPrefix(input, "/config") {
			handleConfigCommand(input)
			continue
		}

		// Handle info commands
		if strings.HasPrefix(input, "/info") {
			handleInfoCommand(input)
			continue
		}

		// Send message to agent
		fmt.Print("Jarvis: ")

		// Check if container manager is available
		if globalContainerManager == nil {
			fmt.Println("Error: Agent container not available. Please restart the session.")
			continue
		}

		// Send message to container
		response, err := globalContainerManager.SendMessage(input)
		if err != nil {
			fmt.Printf("Error: %v\n", err)
			fmt.Println("Try restarting the session if the issue persists.")
			continue
		}

		// Print response
		fmt.Println(response)
		fmt.Println()
	}
}

func showInteractiveHelp() {
	fmt.Println()
	fmt.Println("Available Commands:")
	fmt.Println("==================")
	fmt.Println("/help           - Show this help message")
	fmt.Println("/stop           - Exit the session")
	fmt.Println("/config show    - Show current configuration")
	fmt.Println("/info          - Show agent capabilities")
	fmt.Println()
	fmt.Println("Natural Language:")
	fmt.Println("You can also ask me anything in natural language:")
	fmt.Println("• 'What files are in this directory?'")
	fmt.Println("• 'Create a Python script that prints hello world'")
	fmt.Println("• 'Help me debug this code'")
	fmt.Println("• 'Send an email with the results'")
	fmt.Println()
}

func handleConfigCommand(input string) {
	parts := strings.Fields(input)
	if len(parts) < 2 {
		fmt.Println("Error: Usage: /config show")
		return
	}

	switch parts[1] {
	case "show":
		config, err := loadConfig()
		if err != nil {
			fmt.Printf("Error: Failed to load configuration: %v\n", err)
			return
		}

		printCurrentConfig(config)

	default:
		fmt.Printf("Error: Unknown config command: %s\n", parts[1])
		fmt.Println("Available: /config show")
	}
}

func handleInfoCommand(input string) {
	fmt.Println()
	fmt.Println("Jarvis AI Agent Capabilities:")
	fmt.Println("=============================")
	fmt.Println()

	printCapabilities()
}
