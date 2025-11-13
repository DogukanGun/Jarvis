package main

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

const envFileName = ".jarvis.env"

type Config struct {
	OpenAIAPIKey  string `env:"OPENAI_API_KEY"`
	EmailPassword string `env:"EMAIL_PASSWORD"`
	UserEmail     string `env:"USER_EMAIL"`
}

// getConfigPath returns the path to the config file in user's home directory
func getConfigPath() (string, error) {
	homeDir, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("failed to get user home directory: %w", err)
	}
	return filepath.Join(homeDir, envFileName), nil
}

// loadConfig loads configuration from .env file
func loadConfig() (*Config, error) {
	configPath, err := getConfigPath()
	if err != nil {
		return nil, err
	}

	config := &Config{}

	// Check if config file exists
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		return config, nil // Return empty config if file doesn't exist
	}

	file, err := os.Open(configPath)
	if err != nil {
		return nil, fmt.Errorf("failed to open config file: %w", err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}

		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}

		key := strings.TrimSpace(parts[0])
		value := strings.TrimSpace(parts[1])

		// Remove quotes if present
		if len(value) >= 2 && ((value[0] == '"' && value[len(value)-1] == '"') ||
			(value[0] == '\'' && value[len(value)-1] == '\'')) {
			value = value[1 : len(value)-1]
		}

		switch key {
		case "OPENAI_API_KEY":
			config.OpenAIAPIKey = value
		case "EMAIL_PASSWORD":
			config.EmailPassword = value
		case "USER_EMAIL":
			config.UserEmail = value
		}
	}

	return config, scanner.Err()
}

// saveConfig saves configuration to .env file
func saveConfig(config *Config) error {
	configPath, err := getConfigPath()
	if err != nil {
		return err
	}

	file, err := os.Create(configPath)
	if err != nil {
		return fmt.Errorf("failed to create config file: %w", err)
	}
	defer file.Close()

	fmt.Fprintln(file, "# Jarvis CLI Configuration")
	fmt.Fprintln(file, "# This file contains your API keys and settings")
	fmt.Fprintln(file, "")

	if config.OpenAIAPIKey != "" {
		fmt.Fprintf(file, "OPENAI_API_KEY=%s\n", config.OpenAIAPIKey)
	}
	if config.EmailPassword != "" {
		fmt.Fprintf(file, "EMAIL_PASSWORD=%s\n", config.EmailPassword)
	}
	if config.UserEmail != "" {
		fmt.Fprintf(file, "USER_EMAIL=%s\n", config.UserEmail)
	}

	return nil
}

// setupInitialConfig prompts user for initial configuration
func setupInitialConfig() (*Config, error) {
	fmt.Println("Welcome to Jarvis CLI! Let's set up your configuration.")
	fmt.Println()

	config := &Config{}
	reader := bufio.NewReader(os.Stdin)

	// OpenAI API Key
	fmt.Print("Enter your OpenAI API Key (required): ")
	apiKey, err := readPasswordWithFallback(reader)
	if err != nil {
		return nil, fmt.Errorf("failed to read API key: %w", err)
	}
	if apiKey == "" {
		return nil, fmt.Errorf("OpenAI API key is required")
	}
	config.OpenAIAPIKey = apiKey

	// Email settings (optional)
	fmt.Print("\nEnter your email address for notifications (optional): ")
	email, err := reader.ReadString('\n')
	if err != nil {
		return nil, fmt.Errorf("failed to read email: %w", err)
	}
	config.UserEmail = strings.TrimSpace(email)

	if config.UserEmail != "" {
		fmt.Print("Enter your email app password (optional): ")
		emailPassword, err := readPasswordWithFallback(reader)
		if err != nil {
			return nil, fmt.Errorf("failed to read email password: %w", err)
		}
		config.EmailPassword = emailPassword
	}

	fmt.Println("\nConfiguration complete!")

	// Save configuration
	if err := saveConfig(config); err != nil {
		return nil, fmt.Errorf("failed to save configuration: %w", err)
	}

	configPath, _ := getConfigPath()
	fmt.Printf("Configuration saved to: %s\n", configPath)
	fmt.Println()

	return config, nil
}

// ensureConfig ensures configuration exists, prompting user if needed
func ensureConfig() (*Config, error) {
	config, err := loadConfig()
	if err != nil {
		return nil, err
	}

	// Check if we need initial setup
	if config.OpenAIAPIKey == "" {
		return setupInitialConfig()
	}

	return config, nil
}

// applyConfigToEnvironment sets environment variables from config
func applyConfigToEnvironment(config *Config) {
	if config.OpenAIAPIKey != "" {
		os.Setenv("OPENAI_API_KEY", config.OpenAIAPIKey)
	}
	if config.EmailPassword != "" {
		os.Setenv("EMAIL_PASSWORD", config.EmailPassword)
	}
	if config.UserEmail != "" {
		os.Setenv("USER_EMAIL", config.UserEmail)
	}
}

// updateConfigValue updates a specific configuration value
func updateConfigValue(key, value string) error {
	config, err := loadConfig()
	if err != nil {
		return err
	}

	switch strings.ToUpper(key) {
	case "OPENAI_API_KEY":
		config.OpenAIAPIKey = value
	case "EMAIL_PASSWORD":
		config.EmailPassword = value
	case "USER_EMAIL":
		config.UserEmail = value
	default:
		return fmt.Errorf("unknown configuration key: %s", key)
	}

	return saveConfig(config)
}

