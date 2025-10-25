package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
	"jarvis/agent"
)

var infoCmd = &cobra.Command{
	Use:   "info",
	Short: "Show information about Jarvis agent",
	Long: `Display information about the Jarvis AI agent including capabilities,
available tools, and configuration details.`,
	Example: `  # Show all capabilities
  jarvis info capabilities
  
  # Show available tools
  jarvis info tools
  
  # Show version information
  jarvis info version`,
}

var capabilitiesCmd = &cobra.Command{
	Use:   "capabilities",
	Short: "Show agent capabilities",
	Long:  `Display all capabilities that the Jarvis AI agent can perform.`,
	RunE:  showCapabilities,
}

var toolsCmd = &cobra.Command{
	Use:   "tools",
	Short: "Show available tools",
	Long:  `Display all tools available to the Jarvis AI agent.`,
	RunE:  showTools,
}

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Show version information",
	Long:  `Display version and build information for the Jarvis CLI.`,
	RunE:  showVersion,
}

func init() {
	infoCmd.AddCommand(capabilitiesCmd)
	infoCmd.AddCommand(toolsCmd)
	infoCmd.AddCommand(versionCmd)
}

func showCapabilities(cmd *cobra.Command, args []string) error {
	config, err := getAgentConfig()
	if err != nil {
		return fmt.Errorf("configuration error: %v", err)
	}

	jarvisAgent, err := agent.NewJarvisAgent(agent.AgentConfig{
		UserID:      config["user_id"],
		OpenAIModel: config["openai_model"],
		OpenAIKey:   config["openai_key"],
	})
	if err != nil {
		return fmt.Errorf("failed to initialize agent: %v", err)
	}

	capabilities := jarvisAgent.GetCapabilities()

	fmt.Println("Jarvis AI Agent Capabilities")
	fmt.Println("============================")
	fmt.Println()

	for category, items := range capabilities {
		fmt.Printf("🔧 %s:\n", category)
		for _, item := range items {
			fmt.Printf("   • %s\n", item)
		}
		fmt.Println()
	}

	return nil
}

func showTools(cmd *cobra.Command, args []string) error {
	config, err := getAgentConfig()
	if err != nil {
		return fmt.Errorf("configuration error: %v", err)
	}

	jarvisAgent, err := agent.NewJarvisAgent(agent.AgentConfig{
		UserID:      config["user_id"],
		OpenAIModel: config["openai_model"],
		OpenAIKey:   config["openai_key"],
	})
	if err != nil {
		return fmt.Errorf("failed to initialize agent: %v", err)
	}

	tools := jarvisAgent.GetAvailableTools()

	fmt.Println("Available Tools")
	fmt.Println("===============")
	fmt.Println()

	for i, tool := range tools {
		fmt.Printf("%2d. %s\n", i+1, tool)
	}
	fmt.Println()
	fmt.Printf("Total: %d tools available\n", len(tools))

	return nil
}

func showVersion(cmd *cobra.Command, args []string) error {
	fmt.Println("Jarvis AI Agent CLI")
	fmt.Println("===================")
	fmt.Println()
	fmt.Println("Version:     1.0.0")
	fmt.Println("Build:       development")
	fmt.Println("Go Version:  1.24.4")
	fmt.Println("Framework:   LangChain Go")
	fmt.Println("Platform:    Cross-platform")
	fmt.Println()
	fmt.Println("For more information, visit: https://github.com/user/jarvis")

	return nil
}
