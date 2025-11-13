package main

import (
	"fmt"
	"jarvis/cli/cmd"
	"os"
)

func main() {
	// Handle special commands that don't need container
	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "config":
			rootCmd := cmd.GetRootCommand()
			rootCmd.AddCommand(configCmd)
			if err := rootCmd.Execute(); err != nil {
				os.Exit(1)
			}
			return
		case "info":
			rootCmd := cmd.GetRootCommand()
			if err := rootCmd.Execute(); err != nil {
				os.Exit(1)
			}
			return
		case "--help", "-h", "help":
			showMainHelp()
			return
		case "--version", "-v", "version":
			showVersion()
			return
		}
	}

	// Load and apply configuration
	config, err := ensureConfig()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to load configuration: %v\n", err)
		os.Exit(1)
	}
	applyConfigToEnvironment(config)

	// Initialize environment with container
	userID := getUserID()
	if err := PrepareEnvironmentForCli(userID); err != nil {
		fmt.Fprintf(os.Stderr, "Failed to prepare environment: %v\n", err)
		os.Exit(1)
	}

	// Ensure cleanup happens on normal exit too
	defer CleanupEnvironment()

	// Start interactive session
	if err := startInteractiveSession(); err != nil {
		fmt.Fprintf(os.Stderr, "Session error: %v\n", err)
		CleanupEnvironment()
		os.Exit(1)
	}
}

