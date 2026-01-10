package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"
)

// VisionService handles vision model interactions
type VisionService struct {
	ollamaHost  string
	visionModel string
	client      *http.Client
}

// NewVisionService creates a new vision service
func NewVisionService() *VisionService {
	ollamaHost := os.Getenv("OLLAMA_HOST")
	if ollamaHost == "" {
		ollamaHost = "http://127.0.0.1:11434"
	}

	visionModel := os.Getenv("VISION_MODEL")
	if visionModel == "" {
		visionModel = "llama3.2-vision" // Default vision model
	}

	return &VisionService{
		ollamaHost:  ollamaHost,
		visionModel: visionModel,
		client: &http.Client{
			Timeout: 120 * time.Second, // Vision models need more time
		},
	}
}

// AnalyzeImage sends image to vision model with prompt
func (vs *VisionService) AnalyzeImage(imageBase64 string, prompt string) (string, error) {
	log.Printf("Analyzing image with prompt: %s", prompt)

	// Create request
	req := VisionModelRequest{
		Model: vs.visionModel,
		Messages: []Message{
			{
				Role:    "user",
				Content: prompt,
				Images:  []string{imageBase64},
			},
		},
		Stream: false,
	}

	// Marshal request
	reqBody, err := json.Marshal(req)
	if err != nil {
		return "", fmt.Errorf("failed to marshal request: %v", err)
	}

	// Send request to Ollama
	httpReq, err := http.NewRequest("POST", vs.ollamaHost+"/api/chat", bytes.NewBuffer(reqBody))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %v", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")

	// Execute request
	resp, err := vs.client.Do(httpReq)
	if err != nil {
		return "", fmt.Errorf("failed to send request: %v", err)
	}
	defer resp.Body.Close()

	// Read response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read response: %v", err)
	}

	// Parse response
	var visionResp VisionModelResponse
	if err := json.Unmarshal(body, &visionResp); err != nil {
		return "", fmt.Errorf("failed to parse response: %v", err)
	}

	log.Printf("Vision model response: %s", visionResp.Message.Content)
	return visionResp.Message.Content, nil
}

// FindElement finds a specific UI element in the screenshot
func (vs *VisionService) FindElement(imageBase64 string, elementQuery string) ([]DetectedElement, error) {
	prompt := fmt.Sprintf(`You are a GUI element detector. Analyze this screenshot and find: "%s"

IMPORTANT: Respond ONLY with valid JSON in this exact format:
{
  "elements": [
    {
      "name": "element name",
      "coordinates": {"x": 100, "y": 200},
      "confidence": 0.95,
      "description": "brief description"
    }
  ]
}

Rules:
- Coordinates should be the CENTER of the element
- Estimate pixel coordinates based on screen position
- If element not found, return empty elements array
- No markdown, no explanations, only JSON`, elementQuery)

	response, err := vs.AnalyzeImage(imageBase64, prompt)
	if err != nil {
		return nil, err
	}

	// Parse JSON response
	var result struct {
		Elements []DetectedElement `json:"elements"`
	}

	if err := json.Unmarshal([]byte(response), &result); err != nil {
		log.Printf("Failed to parse JSON response: %v", err)
		// Try to extract coordinates from text response as fallback
		return vs.extractCoordinatesFromText(response, elementQuery), nil
	}

	return result.Elements, nil
}

// DescribeScreen provides a full description of the screen
func (vs *VisionService) DescribeScreen(imageBase64 string) (string, error) {
	prompt := `Analyze this screenshot and provide a detailed description:

1. What application or website is visible?
2. What are the main UI elements (buttons, fields, menus)?
3. What actions can the user perform?
4. Describe the layout and organization

Be specific and mention positions (top, bottom, left, right, center).`

	return vs.AnalyzeImage(imageBase64, prompt)
}

// DetectText extracts text from the screenshot using vision model
func (vs *VisionService) DetectText(imageBase64 string) ([]string, error) {
	prompt := `Extract ALL visible text from this screenshot.

IMPORTANT: Respond ONLY with valid JSON in this exact format:
{
  "text": ["line 1", "line 2", "line 3"]
}

Rules:
- List each text element separately
- Maintain reading order (top to bottom, left to right)
- Include button labels, field labels, menu items, etc.
- No markdown, no explanations, only JSON`

	response, err := vs.AnalyzeImage(imageBase64, prompt)
	if err != nil {
		return nil, err
	}

	// Parse JSON response
	var result struct {
		Text []string `json:"text"`
	}

	if err := json.Unmarshal([]byte(response), &result); err != nil {
		log.Printf("Failed to parse JSON response: %v", err)
		return []string{response}, nil
	}

	return result.Text, nil
}

// extractCoordinatesFromText tries to extract coordinates from text response (fallback)
func (vs *VisionService) extractCoordinatesFromText(text string, elementName string) []DetectedElement {
	// This is a fallback - try to find coordinate patterns in text
	// For now, return a single element with low confidence
	log.Printf("Attempting to extract coordinates from text response")

	return []DetectedElement{
		{
			Name:        elementName,
			Coordinates: Coordinates{X: 0, Y: 0},
			Confidence:  0.1,
			Description: "Could not parse exact coordinates from vision model response",
		},
	}
}

// GetModelInfo returns information about the vision model
func (vs *VisionService) GetModelInfo() (string, error) {
	resp, err := vs.client.Get(vs.ollamaHost + "/api/tags")
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	return string(body), nil
}
