package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"
	"syscall"

	"golang.org/x/term"
)

// maskAPIKey masks an API key for display purposes
func maskAPIKey(key string) string {
	if len(key) <= 8 {
		return strings.Repeat("*", len(key))
	}
	return key[:4] + strings.Repeat("*", len(key)-8) + key[len(key)-4:]
}

// readPasswordWithFallback tries to read password securely, falls back to normal input
func readPasswordWithFallback(reader *bufio.Reader) (string, error) {
	// Try secure password reading first
	if term.IsTerminal(int(syscall.Stdin)) {
		bytePassword, err := term.ReadPassword(int(syscall.Stdin))
		if err == nil {
			fmt.Println() // Add newline after password input
			return strings.TrimSpace(string(bytePassword)), nil
		}
		// If secure reading fails, inform user and fall back
		fmt.Println("\nNote: Secure password input not available, input will be visible.")
	}

	// Fallback to normal input
	input, err := reader.ReadString('\n')
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(input), nil
}

// readPassword reads a password from terminal without echoing (for backward compatibility)
func readPassword() (string, error) {
	reader := bufio.NewReader(os.Stdin)
	return readPasswordWithFallback(reader)
}

// getUserID returns the user ID from environment or defaults
func getUserID() string {
	if userID := os.Getenv("JARVIS_USER_ID"); userID != "" {
		return userID
	}
	// Default user ID based on system user
	if user := os.Getenv("USER"); user != "" {
		return user
	}
	return "cli-user"
}

// showMainHelp displays the main help message
func showMainHelp() {
	fmt.Println("Jarvis AI Assistant")
	fmt.Println("===================")
	fmt.Println()
	fmt.Println("Usage:")
	fmt.Println("  jarvis              Start interactive session")
	fmt.Println("  jarvis config       Manage configuration")
	fmt.Println("  jarvis info         Show agent capabilities")
	fmt.Println("  jarvis --help       Show this help")
	fmt.Println("  jarvis --version    Show version")
	fmt.Println()
	fmt.Println("Interactive Mode:")
	fmt.Println("  When you run 'jarvis', it starts an interactive session where you can")
	fmt.Println("  chat with the AI assistant. Use '/stop' to exit the session.")
	fmt.Println()
	fmt.Println("Examples:")
	fmt.Println("  jarvis                          # Start interactive session")
	fmt.Println("  jarvis config show              # Show current configuration")
	fmt.Println("  jarvis config set openai-key    # Set OpenAI API key")
	fmt.Println()
}

// showVersion displays version information
func showVersion() {
	fmt.Println("Jarvis AI Assistant CLI v1.0.0")
	fmt.Println("Built with Go 1.24.4")
	fmt.Println("Container-based agent architecture")
}

// printCapabilities prints the agent capabilities in a formatted way
func printCapabilities() {
	capabilities := map[string][]string{
		"File Operations": {
			"Read file contents",
			"Write to files",
			"List directory contents",
			"Delete files",
			"Copy and move files",
		},
		"Code Execution": {
			"Execute Python scripts",
			"Run Go programs",
			"Execute JavaScript",
			"Run shell commands",
			"Compile and build projects",
		},
		"Environment Management": {
			"Install packages (pip, npm, go get)",
			"Check versions",
			"Manage dependencies",
			"Environment variable handling",
		},
		"Git Operations": {
			"Git status and diff",
			"Commit changes",
			"Create pull requests",
			"Branch management",
		},
		"Web Research": {
			"Wikipedia search",
			"Web scraping",
			"URL content fetching",
		},
		"Communication": {
			"Send email notifications",
			"Kafka messaging",
		},
	}

	for category, items := range capabilities {
		fmt.Printf("%s:\n", category)
		for _, item := range items {
			fmt.Printf("   • %s\n", item)
		}
		fmt.Println()
	}
}

// printCurrentConfig prints the current configuration in a formatted way
func printCurrentConfig(config *Config) {
	fmt.Println()
	fmt.Println("Current Configuration:")
	fmt.Println("=====================")

	if config.OpenAIAPIKey != "" {
		masked := maskAPIKey(config.OpenAIAPIKey)
		fmt.Printf("OpenAI API Key: %s\n", masked)
	} else {
		fmt.Println("OpenAI API Key: (not set)")
	}

	if config.UserEmail != "" {
		fmt.Printf("Email Address:  %s\n", config.UserEmail)
	} else {
		fmt.Println("Email Address:  (not set)")
	}

	if config.EmailPassword != "" {
		fmt.Println("Email Password: (set)")
	} else {
		fmt.Println("Email Password: (not set)")
	}
	fmt.Println()
}