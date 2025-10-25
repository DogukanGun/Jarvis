package cmd

import (
	"context"
	"fmt"
	"jarvis/agent"
	"strings"

	"github.com/spf13/cobra"
)

var askCmd = &cobra.Command{
	Use:   "ask [message]",
	Short: "Ask Jarvis a single question or command",
	Long: `Send a single message to your Jarvis AI agent and get a response.
This is useful for one-shot queries, automation, or CI/CD pipelines.`,
	Example: `  # Ask a simple question
  jarvis ask "What is the current time?"
  
  # Request file operations
  jarvis ask "Read the contents of README.md"
  
  # Execute code
  jarvis ask "Run this Python code: print('Hello World')"
  
  # Use with pipes for automation
  echo "List all .go files in the current directory" | jarvis ask`,
	Args: cobra.MinimumNArgs(1),
	RunE: runAsk,
}

func runAsk(cmd *cobra.Command, args []string) error {
	message := strings.Join(args, " ")
	if message == "" {
		return fmt.Errorf("message cannot be empty")
	}

	config, err := getAgentConfig()
	if err != nil {
		return fmt.Errorf("configuration error: %v", err)
	}

	if verbose {
		fmt.Printf("Sending message to Jarvis agent...\n")
		fmt.Printf("Model: %s\n", config["openai_model"])
		fmt.Printf("User ID: %s\n", config["user_id"])
		fmt.Printf("Message: %s\n\n", message)
	}

	jarvisAgent, err := agent.NewJarvisAgent(agent.AgentConfig{
		UserID:      config["user_id"],
		OpenAIModel: config["openai_model"],
		OpenAIKey:   config["openai_key"],
	})
	if err != nil {
		return fmt.Errorf("failed to initialize agent: %v", err)
	}

	ctx := context.Background()
	response, err := jarvisAgent.ProcessMessage(ctx, message)
	if err != nil {
		return fmt.Errorf("agent processing error: %v", err)
	}

	fmt.Println(response)
	return nil
}
