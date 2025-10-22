package main

import (
	"bufio"
	"context"
	"fmt"
	"github.com/tmc/langchaingo/tools"
	"github.com/tmc/langchaingo/tools/wikipedia"
	jarvisTools "jarvis/tools"
	"log"
	"os"
	"strings"

	"github.com/tmc/langchaingo/agents"
	"github.com/tmc/langchaingo/llms/openai"
)

func main() {
	llm, err := openai.New(openai.WithModel("gpt-4o-mini"))
	if err != nil {
		log.Fatal(err)
	}

	// Initialize Wikipedia tool with proper user agent
	wikipediaTool := wikipedia.New("Jarvis-AI-Agent/1.0 (https://github.com/user/jarvis)")

	// Get web tools (includes wrapped scraper)
	webTools, err := jarvisTools.GetWebTools()
	if err != nil {
		log.Fatal("Failed to create web tools:", err)
	}

	var allTools []tools.Tool

	// Add custom tools
	allTools = append(allTools, jarvisTools.GetFileTools()...)
	allTools = append(allTools, jarvisTools.GetExecutionTools()...)
	allTools = append(allTools, jarvisTools.GetEnvironmentTools()...)
	allTools = append(allTools, jarvisTools.GetCommunicationTools()...)

	// Add web tools
	allTools = append(allTools, webTools...)
	
	// Add external langchain tools
	allTools = append(allTools, wikipediaTool)

	// Create an OpenAI Functions agent which works best with GPT models and tools
	agent := agents.NewOpenAIFunctionsAgent(llm, allTools)
	executor := agents.NewExecutor(agent)

	ctx := context.Background()
	scanner := bufio.NewScanner(os.Stdin)

	fmt.Println("Jarvis AI Agent ready! Type 'exit' or 'quit' to stop.")
	fmt.Println("Available tools: file operations, execution, environment, communication, web scraping, wikipedia")
	fmt.Println()

	for {
		fmt.Print("Jarvis> ")
		if !scanner.Scan() {
			break
		}
		
		input := strings.TrimSpace(scanner.Text())
		
		if input == "exit" || input == "quit" {
			fmt.Println("Goodbye!")
			break
		}

		if input == "" {
			continue
		}

		result, err := executor.Call(ctx, map[string]any{
			"input": input,
		})
		if err != nil {
			fmt.Printf("Error: %v\n", err)
			continue
		}

		if output, ok := result["output"]; ok {
			fmt.Printf("Jarvis: %s\n\n", output)
		} else {
			fmt.Printf("Jarvis: %v\n\n", result)
		}
	}
}
