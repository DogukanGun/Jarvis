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

// WebWorkflow handles web fetching and extraction workflows
type WebWorkflow struct {
	webFetcherURL string
	httpClient    *http.Client
}

// NewWebWorkflow creates a new web workflow handler
func NewWebWorkflow(webFetcherURL string) *WebWorkflow {
	if webFetcherURL == "" {
		webFetcherURL = "http://localhost:8082"
	}

	return &WebWorkflow{
		webFetcherURL: webFetcherURL,
		httpClient: &http.Client{
			Timeout: 2 * time.Minute,
		},
	}
}

// FetchRequest represents a request to fetch a URL
type FetchRequest struct {
	URL     string `json:"url"`
	Selectors string `json:"selectors,omitempty"` // CSS selectors for extraction
	Prompt  string `json:"prompt,omitempty"`      // LLM prompt for extraction
}

// FetchResponse represents the response from web fetching
type FetchResponse struct {
	Success bool   `json:"success"`
	Content string `json:"content"`
	Error   string `json:"error,omitempty"`
}

// FetchURL fetches and extracts content from a URL
func (ww *WebWorkflow) FetchURL(ctx context.Context, url string, selectors string, prompt string) (string, error) {
	log.Printf("Fetching content from: %s", url)

	req := FetchRequest{
		URL:       url,
		Selectors: selectors,
		Prompt:    prompt,
	}

	jsonBody, err := json.Marshal(req)
	if err != nil {
		return "", fmt.Errorf("failed to marshal request: %v", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, "POST", fmt.Sprintf("%s/fetch", ww.webFetcherURL), nil)
	if err != nil {
		return "", fmt.Errorf("failed to create request: %v", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Body = io.NopCloser(bytes.NewReader(jsonBody))

	resp, err := ww.httpClient.Do(httpReq)
	if err != nil {
		return "", fmt.Errorf("failed to call web fetcher: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("web fetcher returned %d: %s", resp.StatusCode, string(body))
	}

	var fetchResp FetchResponse
	if err := json.NewDecoder(resp.Body).Decode(&fetchResp); err != nil {
		return "", fmt.Errorf("failed to decode response: %v", err)
	}

	if !fetchResp.Success {
		return "", fmt.Errorf("fetch failed: %s", fetchResp.Error)
	}

	return fetchResp.Content, nil
}

// ExecuteWebExtractionWorkflow executes a web extraction workflow
func (ww *WebWorkflow) ExecuteWebExtractionWorkflow(
	ctx context.Context,
	url string,
	extractionPrompt string,
	onExtractionComplete func(content string) error,
) error {
	log.Printf("Starting web extraction workflow for: %s", url)

	// Fetch and extract content
	content, err := ww.FetchURL(ctx, url, "", extractionPrompt)
	if err != nil {
		return fmt.Errorf("web extraction failed: %v", err)
	}

	log.Printf("Web extraction completed")

	// Callback for completion
	if onExtractionComplete != nil {
		if err := onExtractionComplete(content); err != nil {
			return fmt.Errorf("extraction completion callback failed: %v", err)
		}
	}

	return nil
}

// FetchMultipleURLs fetches from multiple URLs and aggregates results
func (ww *WebWorkflow) FetchMultipleURLs(ctx context.Context, urls []string, aggregationPrompt string) (string, error) {
	log.Printf("Fetching from %d URLs", len(urls))

	aggregatedContent := ""

	for i, url := range urls {
		select {
		case <-ctx.Done():
			return "", ctx.Err()
		default:
		}

		log.Printf("Fetching URL %d/%d: %s", i+1, len(urls), url)

		content, err := ww.FetchURL(ctx, url, "", aggregationPrompt)
		if err != nil {
			log.Printf("Warning: failed to fetch %s: %v", url, err)
			continue
		}

		aggregatedContent += fmt.Sprintf("\n\n=== Content from %s ===\n%s", url, content)
	}

	if aggregatedContent == "" {
		return "", fmt.Errorf("no content fetched from any URL")
	}

	return aggregatedContent, nil
}

// CreateWebExtractionProposal creates a proposal event for web extraction
func CreateWebExtractionProposal(groupID string, threadID string, url string, prompt string) *group.Envelope {
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
			"title":             "Web Content Extraction",
			"description":       fmt.Sprintf("Extract content from: %s", url),
			"action":            "fetch_content",
			"context":           prompt,
			"url":               url,
			"confidence":        0.9,
			"requires_approval": false,
		},
	)
}

// CreatePriceComparisonProposal creates a proposal event for price comparison
func CreatePriceComparisonProposal(groupID string, threadID string, productName string, urls []string) *group.Envelope {
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
			"title":             "Price Comparison",
			"description":       fmt.Sprintf("Compare prices for: %s", productName),
			"action":            "price_comparison",
			"context":           productName,
			"urls":              urls,
			"confidence":        0.85,
			"requires_approval": false,
		},
	)
}
