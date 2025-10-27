package main

import (
	"fmt"
	"github.com/tmc/langchaingo/tools/scraper"
	"github.com/tmc/langchaingo/tools/wikipedia"
	jarvisTools2 "jarvis/agent/tools"
	"regexp"
)

func main() {
	fmt.Println("Checking tool names for OpenAI compatibility...")

	// OpenAI pattern: ^[a-zA-Z0-9_-]+$
	validPattern := regexp.MustCompile(`^[a-zA-Z0-9_-]+$`)

	fmt.Println("\n=== Custom Tools ===")

	fmt.Println("\nFile Tools:")
	for _, tool := range jarvisTools2.GetFileTools() {
		name := tool.Name()
		valid := validPattern.MatchString(name)
		fmt.Printf("  - %s: %v\n", name, valid)
	}

	fmt.Println("\nExecution Tools:")
	for _, tool := range jarvisTools2.GetExecutionTools() {
		name := tool.Name()
		valid := validPattern.MatchString(name)
		fmt.Printf("  - %s: %v\n", name, valid)
	}

	fmt.Println("\nEnvironment Tools:")
	for _, tool := range jarvisTools2.GetEnvironmentTools() {
		name := tool.Name()
		valid := validPattern.MatchString(name)
		fmt.Printf("  - %s: %v\n", name, valid)
	}

	fmt.Println("\nCommunication Tools:")
	for _, tool := range jarvisTools2.GetCommunicationTools() {
		name := tool.Name()
		valid := validPattern.MatchString(name)
		fmt.Printf("  - %s: %v\n", name, valid)
	}

	fmt.Println("\n=== External Tools ===")
	scraperTool, _ := scraper.New()
	scraperName := scraperTool.Name()
	scraperValid := validPattern.MatchString(scraperName)
	fmt.Printf("Scraper: %s (%v)\n", scraperName, scraperValid)

	wikipediaTool := wikipedia.New("Jarvis-AI-Agent/1.0")
	wikipediaName := wikipediaTool.Name()
	wikipediaValid := validPattern.MatchString(wikipediaName)
	fmt.Printf("Wikipedia: %s (%v)\n", wikipediaName, wikipediaValid)
}
