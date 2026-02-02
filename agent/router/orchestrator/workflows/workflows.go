package workflows

import (
	"os"
)

// WorkflowRegistry manages all available workflows
type WorkflowRegistry struct {
	Qwen   *QwenWorkflow
	Visual *VisualWorkflow
	Web    *WebWorkflow
}

// NewWorkflowRegistry creates and initializes all workflows
func NewWorkflowRegistry() *WorkflowRegistry {
	return &WorkflowRegistry{
		Qwen:   NewQwenWorkflow(os.Getenv("QWEN_CODE_URL")),
		Visual: NewVisualWorkflow(os.Getenv("VISUAL_ANALYSER_URL")),
		Web:    NewWebWorkflow(os.Getenv("WEB_FETCHER_URL")),
	}
}
