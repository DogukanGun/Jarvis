package coder

import (
	"github.com/tmc/langchaingo/agents"
	"github.com/tmc/langchaingo/llms/ollama"
	"github.com/tmc/langchaingo/tools"
	jarvisTools2 "jarvis/agent/tools"
	"log"
)

func NewCoderAgent() {
	llm, err := ollama.New(ollama.WithModel("llama2"))
	if err != nil {
		log.Fatal(err)
	}
	var allTools []tools.Tool
	allTools = append(allTools, jarvisTools2.GetFileTools()...)
	allTools = append(allTools, jarvisTools2.GetExecutionTools()...)
	allTools = append(allTools, jarvisTools2.GetEnvironmentTools()...)
	allTools = append(allTools, jarvisTools2.GetCommunicationTools()...)
	agents.NewConversationalAgent(llm, allTools)

}
