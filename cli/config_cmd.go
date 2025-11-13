package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"

	"github.com/spf13/cobra"
)

var configCmd = &cobra.Command{
	Use:   "config",
	Short: "Manage Jarvis CLI configuration",
	Long: `Manage configuration settings for Jarvis CLI including API keys and email settings.
	
The configuration is stored in ~/.jarvis.env file.`,
	Example: `  # Show current configuration
  jarvis config show
  
  # Set a new OpenAI API key
  jarvis config set openai-key
  
  # Set email settings
  jarvis config set email`,
}

var configShowCmd = &cobra.Command{
	Use:   "show",
	Short: "Show current configuration",
	Long:  `Display the current configuration settings (API keys will be masked).`,
	RunE:  showConfig,
}

var configSetCmd = &cobra.Command{
	Use:   "set [key]",
	Short: "Set configuration values",
	Long: `Set configuration values interactively.
	
Available keys:
  openai-key  - Set OpenAI API Key
  email       - Set email configuration (address and password)`,
	Example: `  # Set OpenAI API key
  jarvis config set openai-key
  
  # Set email configuration
  jarvis config set email`,
	Args: cobra.ExactArgs(1),
	RunE: setConfig,
}

var configResetCmd = &cobra.Command{
	Use:   "reset",
	Short: "Reset configuration",
	Long:  `Reset all configuration settings. This will delete the ~/.jarvis.env file.`,
	RunE:  resetConfig,
}

func init() {
	configCmd.AddCommand(configShowCmd)
	configCmd.AddCommand(configSetCmd)
	configCmd.AddCommand(configResetCmd)
}

func showConfig(cmd *cobra.Command, args []string) error {
	config, err := loadConfig()
	if err != nil {
		return fmt.Errorf("failed to load configuration: %w", err)
	}

	fmt.Println("Current Jarvis CLI Configuration:")
	fmt.Println("=================================")
	
	printCurrentConfig(config)

	configPath, _ := getConfigPath()
	fmt.Printf("Config file: %s\n", configPath)

	return nil
}

func setConfig(cmd *cobra.Command, args []string) error {
	key := args[0]
	reader := bufio.NewReader(os.Stdin)

	config, err := loadConfig()
	if err != nil {
		return fmt.Errorf("failed to load configuration: %w", err)
	}

	switch strings.ToLower(key) {
	case "openai-key", "openai":
		fmt.Print("Enter your OpenAI API Key: ")
		apiKey, err := readPassword()
		if err != nil {
			return fmt.Errorf("failed to read API key: %w", err)
		}
		if apiKey == "" {
			return fmt.Errorf("API key cannot be empty")
		}
		config.OpenAIAPIKey = apiKey
		fmt.Println("\nOpenAI API Key updated")

	case "email":
		fmt.Print("Enter your email address: ")
		email, err := reader.ReadString('\n')
		if err != nil {
			return fmt.Errorf("failed to read email: %w", err)
		}
		config.UserEmail = strings.TrimSpace(email)

		if config.UserEmail != "" {
			fmt.Print("Enter your email app password (leave empty to skip): ")
			password, err := readPassword()
			if err != nil {
				return fmt.Errorf("failed to read email password: %w", err)
			}
			config.EmailPassword = password
		}
		fmt.Println("\nEmail configuration updated")

	default:
		return fmt.Errorf("unknown configuration key: %s\nAvailable keys: openai-key, email", key)
	}

	if err := saveConfig(config); err != nil {
		return fmt.Errorf("failed to save configuration: %w", err)
	}

	return nil
}

func resetConfig(cmd *cobra.Command, args []string) error {
	reader := bufio.NewReader(os.Stdin)
	fmt.Print("Are you sure you want to reset all configuration? (y/N): ")
	response, err := reader.ReadString('\n')
	if err != nil {
		return fmt.Errorf("failed to read response: %w", err)
	}

	response = strings.ToLower(strings.TrimSpace(response))
	if response != "y" && response != "yes" {
		fmt.Println("Reset cancelled")
		return nil
	}

	configPath, err := getConfigPath()
	if err != nil {
		return err
	}

	if err := os.Remove(configPath); err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("failed to remove config file: %w", err)
	}

	fmt.Println("Configuration reset successfully")
	return nil
}

