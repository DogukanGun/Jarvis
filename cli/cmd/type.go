package cmd

import (
	"fmt"
	"strings"

	"github.com/spf13/cobra"
)

// ContainerManagerInterface defines the interface for container manager
type ContainerManagerInterface interface {
	SendMessage(message string) (string, error)
}

var containerManager ContainerManagerInterface

// typeCmd represents the type command
var typeCmd = &cobra.Command{
	Use:   "type [message]",
	Short: "Send a message to the Jarvis agent",
	Long: `Send a message to the Jarvis agent and get a response.
	
The type command allows you to interact with the Jarvis agent by sending
it a message and receiving a response. This is useful for quick queries
or commands that you want the agent to process.`,
	Example: `  # Send a simple message
  jarvis type "What is the weather today?"
  
  # Send a message with quotes
  jarvis type "Create a new Go file with hello world"
  
  # Send a complex request
  jarvis type "List all files in the current directory and summarize them"`,
	Args: cobra.MinimumNArgs(1),
	RunE: runTypeCmd,
}

// SetContainerManager sets the container manager for the CLI commands
func SetContainerManager(cm ContainerManagerInterface) {
	containerManager = cm
}

func runTypeCmd(cmd *cobra.Command, args []string) error {
	// Join all arguments to form the complete message
	message := strings.Join(args, " ")
	
	if verbose {
		fmt.Printf("Sending message to agent: %s\n", message)
	}

	// Check if container manager is initialized
	if containerManager == nil {
		return fmt.Errorf("container manager not initialized")
	}

	// Send message to container
	response, err := containerManager.SendMessage(message)
	if err != nil {
		return fmt.Errorf("failed to send message to agent: %w", err)
	}

	// Print agent response
	fmt.Println(response)

	return nil
}

func init() {
	// Add type command to root
	rootCmd.AddCommand(typeCmd)
}