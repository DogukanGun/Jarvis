package cmd

import (
	"fmt"

	"github.com/spf13/cobra"
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
	fmt.Println("Jarvis AI Agent Capabilities")
	fmt.Println("============================")
	fmt.Println()

	capabilities := map[string][]string{
		"File Operations": {
			"Read file contents",
			"Write to files",
			"List directory contents",
			"Delete files",
			"Copy files",
			"Move files",
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
		fmt.Printf("🔧 %s:\n", category)
		for _, item := range items {
			fmt.Printf("   • %s\n", item)
		}
		fmt.Println()
	}

	return nil
}

func showTools(cmd *cobra.Command, args []string) error {
	tools := []string{
		"file_tool - File operations (read, write, list, delete)",
		"bash_tool - Execute shell commands and scripts",
		"python_tool - Execute Python code",
		"go_tool - Execute Go code",
		"javascript_tool - Execute JavaScript code",
		"git_tool - Git operations and version control",
		"web_tool - Web scraping and content fetching",
		"wikipedia_tool - Wikipedia search and content retrieval",
		"package_tool - Package management (pip, npm, go get)",
		"email_tool - Send email notifications",
		"kafka_tool - Kafka messaging operations",
		"environment_tool - Environment variable management",
		"docker_tool - Docker container operations",
	}

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
