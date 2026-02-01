package workflows

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/google/uuid"
	"jarvis/agent/schemas/group"
)

// VisualWorkflow handles image analysis workflows
type VisualWorkflow struct {
	visualURL  string
	httpClient *http.Client
}

// NewVisualWorkflow creates a new visual workflow handler
func NewVisualWorkflow(visualURL string) *VisualWorkflow {
	if visualURL == "" {
		visualURL = "http://localhost:8081"
	}

	return &VisualWorkflow{
		visualURL: visualURL,
		httpClient: &http.Client{
			Timeout: 2 * time.Minute,
		},
	}
}

// AnalyzeImageRequest represents a request to analyze an image
type AnalyzeImageRequest struct {
	ImageURL  string `json:"image_url,omitempty"`
	ImageData string `json:"image_data,omitempty"` // Base64 encoded
	Prompt    string `json:"prompt"`
}

// AnalyzeImageResponse represents the response from image analysis
type AnalyzeImageResponse struct {
	Success    bool   `json:"success"`
	Analysis   string `json:"analysis"`
	Confidence float32 `json:"confidence"`
	Error      string `json:"error,omitempty"`
}

// AnalyzeImage sends an image to the visual analyser for analysis
func (vw *VisualWorkflow) AnalyzeImage(ctx context.Context, imageURL string, imageData string, prompt string) (string, error) {
	log.Printf("Analyzing image with visual analyser")

	req := AnalyzeImageRequest{
		ImageURL:  imageURL,
		ImageData: imageData,
		Prompt:    prompt,
	}

	jsonBody, err := json.Marshal(req)
	if err != nil {
		return "", fmt.Errorf("failed to marshal request: %v", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", fmt.Sprintf("%s/analyze", vw.visualURL), nil)
	if err != nil {
		return "", fmt.Errorf("failed to create request: %v", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Body = io.NopCloser(bytes.NewReader(jsonBody))

	resp, err := vw.httpClient.Do(httpReq)
	if err != nil {
		return "", fmt.Errorf("failed to call visual analyser: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("visual analyser returned %d: %s", resp.StatusCode, string(body))
	}

	var analysisResp AnalyzeImageResponse
	if err := json.NewDecoder(resp.Body).Decode(&analysisResp); err != nil {
		return "", fmt.Errorf("failed to decode response: %v", err)
	}

	if !analysisResp.Success {
		return "", fmt.Errorf("analysis failed: %s", analysisResp.Error)
	}

	return analysisResp.Analysis, nil
}

// ExecuteImageAnalysisWorkflow executes an image analysis workflow
func (vw *VisualWorkflow) ExecuteImageAnalysisWorkflow(
	ctx context.Context,
	imageURL string,
	imageData string,
	prompt string,
	onAnalysisComplete func(analysis string) error,
) error {
	log.Printf("Starting image analysis workflow")

	// Perform analysis
	analysis, err := vw.AnalyzeImage(ctx, imageURL, imageData, prompt)
	if err != nil {
		return fmt.Errorf("image analysis failed: %v", err)
	}

	log.Printf("Image analysis completed: %s", analysis[:min(100, len(analysis))])

	// Callback for completion
	if onAnalysisComplete != nil {
		if err := onAnalysisComplete(analysis); err != nil {
			return fmt.Errorf("analysis completion callback failed: %v", err)
		}
	}

	return nil
}

// CreateImageAnalysisProposal creates a proposal event for image analysis
func CreateImageAnalysisProposal(groupID string, threadID string, imageURL string, prompt string) *group.Envelope {
	proposalID := uuid.New().String()

	return group.NewEnvelope(
		groupID,
		threadID,
		uuid.New().String(),
		group.Sender{
			ID:    "orchestrator",
			Role:  group.RoleAdmin,
			Agent: "orchestrator",
		},
		group.EventProposalCreated,
		map[string]interface{}{
			"proposal_id":       proposalID,
			"title":             "Image Analysis",
			"description":       prompt,
			"action":            "analyze_image",
			"context":           prompt,
			"image_url":         imageURL,
			"confidence":        0.9,
			"requires_approval": false,
		},
	)
}
