package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var (
	// Global flags
	openaiKey   string
	openaiModel string
	userID      string
	verbose     bool
)

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use:   "jarvis",
	Short: "Jarvis AI Agent - Your intelligent assistant",
	Long: `Jarvis is an AI agent that can help you with various tasks including:

• File operations (read, write, delete, list)
• Code execution (Python, Go, JavaScript, Bash)
• Environment management (package installation, version checking)
• Communication (Git operations, PR creation)
• Web research (scraping, Wikipedia search)

You can use Jarvis in interactive chat mode or for one-shot queries.`,
	Example: `  # Start interactive chat mode
  jarvis chat

  # Ask a single question
  jarvis ask "What is the weather today?"

  # Show available capabilities
  jarvis info capabilities

  # List available tools
  jarvis info tools`,
}

// Execute adds all child commands to the root command and sets flags appropriately.
// This is called by main.main(). It only needs to happen once to the rootCmd.
func Execute() error {
	return rootCmd.Execute()
}

func init() {
	// Global flags
	rootCmd.PersistentFlags().StringVar(&openaiKey, "openai-key", "", "OpenAI API key (can also use OPENAI_API_KEY env var)")
	rootCmd.PersistentFlags().StringVar(&openaiModel, "model", "gpt-4o-mini", "OpenAI model to use")
	rootCmd.PersistentFlags().StringVar(&userID, "user-id", "cli-user", "User ID for the agent session")
	rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "Enable verbose output")

	// Environment variable bindings
	if rootCmd.PersistentFlags().Lookup("openai-key").Value.String() == "" {
		if key := os.Getenv("OPENAI_API_KEY"); key != "" {
			openaiKey = key
		}
	}

	// Add subcommands
	rootCmd.AddCommand(chatCmd)
	rootCmd.AddCommand(askCmd)
	rootCmd.AddCommand(infoCmd)
}

// getAgentConfig returns agent configuration from flags and environment
func getAgentConfig() (map[string]string, error) {
	// Validate required configuration
	if openaiKey == "" {
		if key := os.Getenv("OPENAI_API_KEY"); key != "" {
			openaiKey = key
		} else {
			return nil, fmt.Errorf("OpenAI API key is required. Set OPENAI_API_KEY environment variable or use --openai-key flag")
		}
	}

	config := map[string]string{
		"openai_key":   openaiKey,
		"openai_model": openaiModel,
		"user_id":      userID,
	}

	if verbose {
		fmt.Printf("Agent Configuration:\n")
		fmt.Printf("  Model: %s\n", openaiModel)
		fmt.Printf("  User ID: %s\n", userID)
		fmt.Printf("  API Key: %s...%s\n", openaiKey[:8], openaiKey[len(openaiKey)-4:])
	}

	return config, nil
}
